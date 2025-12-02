"""Database connection management with connection pooling"""

import mysql.connector
from mysql.connector import pooling, Error
from contextlib import contextmanager
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages MySQL database connections with connection pooling"""

    _pool = None

    @classmethod
    def initialize_pool(cls):
        """Initialize the connection pool"""
        if cls._pool is None:
            try:
                cls._pool = pooling.MySQLConnectionPool(
                    pool_name=settings.POOL_NAME,
                    pool_size=settings.POOL_SIZE,
                    pool_reset_session=True,
                    host=settings.DB_HOST,
                    port=settings.DB_PORT,
                    database=settings.DB_NAME,
                    user=settings.DB_USER,
                    password=settings.DB_PASSWORD,
                    charset="utf8mb4",
                    autocommit=False,
                )
                logger.info(
                    f"Database connection pool initialized with {settings.POOL_SIZE} connections"
                )
            except Error as e:
                logger.error(f"Error creating connection pool: {e}")
                raise

    @classmethod
    @contextmanager
    def get_connection(cls):
        """
        Context manager for database connections
        Automatically handles commit/rollback and connection release
        """
        if cls._pool is None:
            cls.initialize_pool()

        connection = None
        try:
            connection = cls._pool.get_connection()
            yield connection
            connection.commit()
        except Error as e:
            if connection:
                connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()

    @classmethod
    def execute_query(cls, query, params=None, fetch=False):
        """
        Execute a single query with optional parameters

        Args:
            query: SQL query string
            params: Query parameters (tuple or dict)
            fetch: If True, return fetched results

        Returns:
            For SELECT: List of rows
            For INSERT/UPDATE: Number of affected rows
        """
        with cls.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(query, params or ())

                if fetch:
                    result = cursor.fetchall()
                    return result
                else:
                    return cursor.rowcount
            finally:
                cursor.close()

    @classmethod
    def execute_many(cls, query, data):
        """
        Execute batch insert/update operations

        Args:
            query: SQL query string
            data: List of tuples containing parameter values

        Returns:
            Number of affected rows
        """
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.executemany(query, data)
                return cursor.rowcount
            finally:
                cursor.close()


# Initialize pool on import
DatabaseManager.initialize_pool()
