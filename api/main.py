"""FastAPI application for CartPE scraper"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from contextlib import asynccontextmanager
from services.reminder_scheduler import ReminderScheduler
from utils.logger import setup_logger


setup_logger()
logger = logging.getLogger(__name__)

# Create scheduler instance
reminder_scheduler = ReminderScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the scheduler
    reminder_scheduler.start()
    yield
    # Shutdown: Stop the scheduler
    reminder_scheduler.stop()


app = FastAPI(
    title="CartPE Product Scraper API",
    description="API for accessing scraped product data",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)


@app.get("/")
def read_root():
    return {
        "message": "CartPE Product Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "stores": "/api/stores",
            "register_subscription": "/api/subscriptions/register",
            "add_permissions": "/api/subscriptions/permissions",
            "store_woocommerce": "/api/subscriptions/woocommerce",
            "subscription_status": "/api/subscriptions/status",
        },
    }
