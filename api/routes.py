"""API routes for stores and products"""

from fastapi import APIRouter, HTTPException, Header
from typing import List, Dict
import logging
from services.database_service import StoreService, CategoryService
from services.subscription_service import SubscriptionService
from pydantic import BaseModel, EmailStr
from typing import List
from config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["stores"])


# Pydantic models
class SubscriptionCreateRequest(BaseModel):
    buyer_email: EmailStr
    buyer_domain: str
    plan_name: str  # "basic", "premium", "enterprise"
    plan_duration: str  # "monthly", "yearly"


class PermissionAddRequest(BaseModel):
    token: str
    buyer_domain: str
    store_ids: List[int]


class WooCommerceCredentialsRequest(BaseModel):
    subscription_id: int
    consumer_key: str
    consumer_secret: str


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
        if request.plan_name not in ["basic", "premium", "enterprise"]:
            raise HTTPException(status_code=400, detail="Invalid plan_name")

        if request.plan_duration not in ["monthly", "yearly"]:
            raise HTTPException(status_code=400, detail="Invalid plan_duration")

        subscription = SubscriptionService.create_subscription(
            buyer_email=request.buyer_email,
            buyer_domain=request.buyer_domain,
            plan_name=request.plan_name,
            plan_duration=request.plan_duration,
        )

        return {"success": True, "data": subscription}

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
            subscription_id=request.subscription_id,
            consumer_key=request.consumer_key,
            consumer_secret=request.consumer_secret,
        )

        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Error storing WooCommerce credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
