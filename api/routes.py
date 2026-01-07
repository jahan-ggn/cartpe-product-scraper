"""API routes for stores and products"""

from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from typing import List, Dict
import logging
from services.database_service import StoreService, CategoryService
from services.subscription_service import SubscriptionService
from pydantic import BaseModel, EmailStr, field_validator
from typing import List
from config.settings import settings
from scrapers.category_scraper import CategoryScraper
from services.database_service import CategoryService


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["stores"])


# Pydantic models
class StoreCreateRequest(BaseModel):
    store_name: str
    store_slug: str
    base_url: str
    api_endpoint: str


class SubscriptionCreateRequest(BaseModel):
    buyer_email: EmailStr
    buyer_domain: str
    plan_name: str  # "starter", "pro"
    plan_duration: str  # "monthly", "yearly"
    whatsapp_number: str

    @field_validator("whatsapp_number")
    @classmethod
    def validate_whatsapp(cls, v: str) -> str:
        # Remove any spaces or special chars
        cleaned = "".join(filter(str.isdigit, v))

        if len(cleaned) != 10:
            raise ValueError("WhatsApp number must be exactly 10 digits")

        # Format with prefix
        return f"whatsapp:+91{cleaned}"


class PermissionAddRequest(BaseModel):
    token: str
    buyer_domain: str
    store_ids: List[int]


class WooCommerceCredentialsRequest(BaseModel):
    token: str
    buyer_domain: str
    consumer_key: str
    consumer_secret: str


class SubscriptionStatusRequest(BaseModel):
    token: str
    buyer_domain: str


def fetch_and_store_categories(store_data: dict):
    """Background task to fetch categories for a newly created store"""
    try:
        scraper = CategoryScraper()
        categories = scraper.extract_categories(store_data)
        if categories:
            CategoryService.bulk_insert_categories(categories)
        scraper.close()
    except Exception as e:
        logger.error(f"Error fetching categories in background: {e}")


@router.get("/stores", response_model=List[Dict])
def get_stores_with_categories():
    """
    Get all stores with their categories

    Returns:
        List of stores with nested categories
    """
    try:
        # Get all stores
        stores = StoreService.get_all_stores()

        if not stores:
            return []

        # Build response with nested categories
        result = []
        for store in stores:
            # Get categories for this store
            categories = CategoryService.get_categories_by_store(store["store_id"])

            # Format categories
            formatted_categories = [
                {
                    "category_id": cat["category_id"],
                    "category_name": cat["category_name"],
                    "category_slug": cat["category_slug"],
                    "category_url": cat["category_url"],
                }
                for cat in categories
            ]

            # Build store object
            store_data = {
                "store_id": store["store_id"],
                "store_name": store["store_name"],
                "store_slug": store["store_slug"],
                "base_url": store["base_url"],
                "categories": formatted_categories,
            }

            result.append(store_data)

        return result

    except Exception as e:
        logger.error(f"Error fetching stores with categories: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/stores")
async def create_store(request: StoreCreateRequest, background_tasks: BackgroundTasks):
    """Create a new store"""
    try:
        result = StoreService.create_store(
            {
                "store_name": request.store_name,
                "store_slug": request.store_slug,
                "base_url": request.base_url,
                "api_endpoint": request.api_endpoint,
            }
        )

        # Add background task
        background_tasks.add_task(
            fetch_and_store_categories,
            {
                "store_id": result["store_id"],
                "store_name": request.store_name,
                "base_url": request.base_url,
            },
        )

        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Error creating store: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscriptions/register")
async def register_subscription(
    request: SubscriptionCreateRequest, api_key: str = Header(None)
):
    """Register a new subscription and generate API token"""
    if not api_key:
        raise HTTPException(status_code=401, detail="API key is required")

    if api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

    try:
        # Validate plan_name
        if request.plan_name not in ["starter", "pro"]:
            raise ValueError("Invalid plan_name")

        # Validate plan_duration
        if request.plan_duration not in ["monthly", "yearly"]:
            raise ValueError("Invalid plan_duration")

        # Normalize domain - strip trailing slash
        buyer_domain = request.buyer_domain.rstrip("/")

        subscription = SubscriptionService.create_subscription(
            buyer_email=request.buyer_email,
            whatsapp_number=request.whatsapp_number,
            buyer_domain=buyer_domain,
            plan_name=request.plan_name,
            plan_duration=request.plan_duration,
        )

        return {"success": True, "data": subscription}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in register_subscription: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscriptions/permissions")
async def add_permissions(request: PermissionAddRequest):
    """
    Add store permissions - requires token + matching domain

    Request body:
    {
        "token": "abc-123-xyz",
        "buyer_domain": "buyersite.com",
        "store_ids": [3, 4, 5]
    }
    """
    try:
        result = SubscriptionService.add_subscription_permissions(
            token=request.token,
            buyer_domain=request.buyer_domain,
            store_ids=request.store_ids,
        )

        return {"success": True, "data": result}

    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error in add_permissions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscriptions/woocommerce")
async def store_woocommerce_credentials(request: WooCommerceCredentialsRequest):
    """Store WooCommerce API credentials for a subscription"""
    try:
        result = SubscriptionService.store_woocommerce_credentials(
            token=request.token,
            buyer_domain=request.buyer_domain,
            consumer_key=request.consumer_key,
            consumer_secret=request.consumer_secret,
        )

        return {"success": True, "data": result}

    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error storing WooCommerce credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscriptions/status")
async def get_subscription_status(request: SubscriptionStatusRequest):
    """
    Get subscription status and details

    Request body:
    {
        "token": "abc-123-xyz",
        "buyer_domain": "buyersite.com"
    }
    """
    try:
        result = SubscriptionService.get_subscription_status(
            token=request.token, buyer_domain=request.buyer_domain
        )

        return {"success": True, "data": result}

    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error in get_subscription_status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
