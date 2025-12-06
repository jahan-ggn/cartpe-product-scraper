"""Subscription service for managing API subscriptions"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from config.database import DatabaseManager

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for managing subscriptions"""

    @staticmethod
    def create_subscription(
        buyer_email: str, buyer_domain: str, plan_name: str, plan_duration: str
    ) -> Dict:
        """
        Create a new subscription and generate token

        Args:
            buyer_email: Buyer's email
            buyer_domain: Buyer's website domain
            plan_name: Plan type (basic, premium, enterprise)
            plan_duration: Duration (monthly, yearly)

        Returns:
            Dictionary with subscription details including token
        """
        try:
            # Validate inputs
            if plan_name not in ["basic", "premium", "enterprise"]:
                raise ValueError(f"Invalid plan_name: {plan_name}")

            if plan_duration not in ["monthly", "yearly"]:
                raise ValueError(f"Invalid plan_duration: {plan_duration}")

            # Generate unique token
            token = str(uuid.uuid4())

            # Calculate expiry date
            created_at = datetime.now()
            if plan_duration == "monthly":
                expires_at = created_at + timedelta(days=30)
            elif plan_duration == "yearly":
                expires_at = created_at + timedelta(days=365)

            # Insert into database
            with DatabaseManager.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)

                query = """
                    INSERT INTO api_subscriptions 
                    (token, buyer_email, buyer_domain, plan_name, plan_duration, status, created_at, expires_at)
                    VALUES (%s, %s, %s, %s, %s, 'active', %s, %s)
                """

                cursor.execute(
                    query,
                    (
                        token,
                        buyer_email,
                        buyer_domain,
                        plan_name,
                        plan_duration,
                        created_at,
                        expires_at,
                    ),
                )

                subscription_id = cursor.lastrowid
                conn.commit()

                logger.info(f"Created subscription {subscription_id} for {buyer_email}")

                return {
                    "subscription_id": subscription_id,
                    "token": token,
                    "buyer_email": buyer_email,
                    "buyer_domain": buyer_domain,
                    "plan_name": plan_name,
                    "plan_duration": plan_duration,
                    "status": "active",
                    "created_at": created_at.isoformat(),
                    "expires_at": expires_at.isoformat(),
                }

        except Exception as e:
            logger.error(f"Error creating subscription: {str(e)}")
            raise

    @staticmethod
    def add_subscription_permissions(
        token: str, buyer_domain: str, store_ids: List[int]
    ) -> Dict:
        """
        Set store permissions - validates token matches domain

        Args:
            token: Subscription token
            buyer_domain: Buyer's domain
            store_ids: Complete list of store IDs

        Returns:
            Dictionary with success status
        """
        try:
            with DatabaseManager.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)

                # Get subscription by domain and verify token
                cursor.execute(
                    """SELECT id, token, plan_name FROM api_subscriptions 
                    WHERE buyer_domain = %s AND status = 'active' 
                    ORDER BY created_at DESC LIMIT 1""",
                    (buyer_domain,),
                )
                subscription = cursor.fetchone()

                if not subscription:
                    raise ValueError(
                        f"No active subscription found for domain: {buyer_domain}"
                    )

                # Verify token matches
                if subscription["token"] != token:
                    raise ValueError("Invalid token for this domain")

                subscription_id = subscription["id"]
                plan_name = subscription["plan_name"]

                # Validate store count based on plan
                max_stores = {"basic": 3, "premium": 5, "enterprise": float("inf")}

                if len(store_ids) > max_stores.get(plan_name, 0):
                    raise ValueError(
                        f"Plan '{plan_name}' allows maximum {max_stores[plan_name]} stores. "
                        f"You requested {len(store_ids)} stores."
                    )

                # Delete existing permissions
                cursor.execute(
                    "DELETE FROM subscription_permissions WHERE subscription_id = %s",
                    (subscription_id,),
                )

                # Insert new permissions
                query = """
                    INSERT INTO subscription_permissions 
                    (subscription_id, store_id)
                    VALUES (%s, %s)
                """

                for store_id in store_ids:
                    cursor.execute(query, (subscription_id, store_id))

                conn.commit()

                logger.info(
                    f"Set {len(store_ids)} store permissions for subscription {subscription_id}"
                )

                return {
                    "subscription_id": subscription_id,
                    "buyer_domain": buyer_domain,
                    "total_stores": len(store_ids),
                }

        except Exception as e:
            logger.error(f"Error setting permissions: {str(e)}")
            raise

    @staticmethod
    def store_woocommerce_credentials(
        subscription_id: int, consumer_key: str, consumer_secret: str
    ) -> Dict:
        """
        Store WooCommerce API credentials for a subscription

        Args:
            subscription_id: Subscription ID
            consumer_key: WooCommerce consumer key
            consumer_secret: WooCommerce consumer secret

        Returns:
            Dictionary with success status
        """
        try:
            with DatabaseManager.get_connection() as conn:
                cursor = conn.cursor()

                query = """
                    INSERT INTO woocommerce_credentials 
                    (subscription_id, consumer_key, consumer_secret)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                    consumer_key = VALUES(consumer_key),
                    consumer_secret = VALUES(consumer_secret)
                """

                cursor.execute(query, (subscription_id, consumer_key, consumer_secret))
                conn.commit()

                logger.info(
                    f"Stored WooCommerce credentials for subscription {subscription_id}"
                )

                return {
                    "subscription_id": subscription_id,
                    "message": "WooCommerce credentials stored successfully",
                }

        except Exception as e:
            logger.error(f"Error storing WooCommerce credentials: {str(e)}")
            raise
