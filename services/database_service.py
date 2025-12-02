"""Database service layer for CRUD operations"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
from config.database import DatabaseManager

logger = logging.getLogger(__name__)


class StoreService:
    """Service class for store-related database operations"""

    @staticmethod
    def get_stores_without_token() -> List[Dict]:
        """
        Fetch all stores that don't have a web token

        Returns:
            List of store dictionaries
        """
        query = """
            SELECT store_id, store_name, store_slug, base_url, api_endpoint
            FROM stores
            WHERE web_token IS NULL OR web_token = ''
        """

        try:
            stores = DatabaseManager.execute_query(query, fetch=True)
            logger.info(f"Found {len(stores)} stores without tokens")
            return stores
        except Exception as e:
            logger.error(f"Error fetching stores: {e}")
            return []

    @staticmethod
    def get_all_stores() -> List[Dict]:
        """
        Fetch all stores from database

        Returns:
            List of store dictionaries
        """
        query = "SELECT * FROM stores"

        try:
            stores = DatabaseManager.execute_query(query, fetch=True)
            logger.info(f"Found {len(stores)} stores in database")
            return stores
        except Exception as e:
            logger.error(f"Error fetching stores: {e}")
            return []

    @staticmethod
    def update_store_token(store_id: int, token: str) -> bool:
        """
        Update store with extracted web token

        Args:
            store_id: Store ID
            token: Extracted web token

        Returns:
            True if update successful, False otherwise
        """
        query = """
            UPDATE stores
            SET web_token = %s,
                token_last_fetched_at = %s,
                updated_at = %s
            WHERE store_id = %s
        """

        try:
            now = datetime.now()
            params = (token, now, now, store_id)
            rows_affected = DatabaseManager.execute_query(query, params)

            if rows_affected > 0:
                logger.info(f"Token updated successfully for store ID: {store_id}")
                return True
            else:
                logger.warning(f"No rows updated for store ID: {store_id}")
                return False

        except Exception as e:
            logger.error(f"Error updating token for store {store_id}: {e}")
            return False


class CategoryService:
    """Service class for category-related database operations"""

    @staticmethod
    def bulk_insert_categories(categories: List[Dict]) -> int:
        """
        Bulk insert categories into database
        Uses INSERT IGNORE to skip duplicates

        Args:
            categories: List of category dictionaries

        Returns:
            Number of categories inserted
        """
        if not categories:
            return 0

        query = """
            INSERT IGNORE INTO categories 
            (store_id, category_name, category_slug, category_url, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """

        try:
            now = datetime.now()
            data = [
                (
                    cat["store_id"],
                    cat["category_name"],
                    cat["category_slug"],
                    cat["category_url"],
                    now,
                )
                for cat in categories
            ]

            rows_affected = DatabaseManager.execute_many(query, data)
            logger.info(f"Inserted {rows_affected} categories into database")
            return rows_affected

        except Exception as e:
            logger.error(f"Error bulk inserting categories: {e}")
            return 0

    @staticmethod
    def get_categories_by_store(store_id: int) -> List[Dict]:
        """
        Get all categories for a specific store

        Args:
            store_id: Store ID

        Returns:
            List of category dictionaries
        """
        query = """
            SELECT * FROM categories
            WHERE store_id = %s
        """

        try:
            categories = DatabaseManager.execute_query(query, (store_id,), fetch=True)
            logger.info(f"Found {len(categories)} categories for store ID: {store_id}")
            return categories
        except Exception as e:
            logger.error(f"Error fetching categories for store {store_id}: {e}")
            return []


class ProductService:
    """Service class for product-related database operations"""

    @staticmethod
    def bulk_upsert_products(products: List[Dict]) -> int:
        """
        Bulk insert or update products using INSERT ... ON DUPLICATE KEY UPDATE

        Args:
            products: List of product dictionaries

        Returns:
            Number of rows affected
        """
        if not products:
            return 0

        query = """
            INSERT INTO products 
            (store_id, category_id, product_id, product_name, product_url, 
             image_url, current_price, original_price, size, stock_status, 
             is_active, last_synced_at, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                category_id = VALUES(category_id),
                product_name = VALUES(product_name),
                product_url = VALUES(product_url),
                image_url = VALUES(image_url),
                current_price = VALUES(current_price),
                original_price = VALUES(original_price),
                size = VALUES(size),
                stock_status = VALUES(stock_status),
                is_active = TRUE,
                last_synced_at = VALUES(last_synced_at),
                updated_at = VALUES(updated_at)
        """

        try:
            now = datetime.now()
            data = [
                (
                    prod["store_id"],
                    prod["category_id"],
                    prod["product_id"],
                    prod["product_name"],
                    prod["product_url"],
                    prod["image_url"],
                    prod["current_price"],
                    prod["original_price"],
                    prod["size"],
                    prod["stock_status"],
                    True,  # is_active
                    now,  # last_synced_at
                    now,  # created_at
                    now,  # updated_at
                )
                for prod in products
            ]

            rows_affected = DatabaseManager.execute_many(query, data)
            logger.info(f"Upserted {rows_affected} products into database")
            return rows_affected

        except Exception as e:
            logger.error(f"Error bulk upserting products: {e}")
            return 0

    @staticmethod
    def get_product_count_by_store(store_id: int) -> int:
        """
        Get total product count for a store

        Args:
            store_id: Store ID

        Returns:
            Product count
        """
        query = "SELECT COUNT(*) as count FROM products WHERE store_id = %s"

        try:
            result = DatabaseManager.execute_query(query, (store_id,), fetch=True)
            return result[0]["count"] if result else 0
        except Exception as e:
            logger.error(f"Error getting product count: {e}")
            return 0
