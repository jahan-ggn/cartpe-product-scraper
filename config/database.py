"""Database connection management with connection pooling"""

import time
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
                    f"Database pool initialized with {settings.POOL_SIZE} connections"
                )
            except Error as e:
                logger.error(f"Error creating connection pool: {e}")
                raise

    @classmethod
    @contextmanager
    def get_connection(cls, max_retries=3, retry_delay=1):
        """Context manager for database connections with retry logic"""
        if cls._pool is None:
            cls.initialize_pool()

        connection = None
        last_error = None

        for attempt in range(max_retries):
            try:
                connection = cls._pool.get_connection()
                yield connection
                connection.commit()
                return
            except Error as e:
                last_error = e
                if connection:
                    try:
                        connection.rollback()
                    except:
                        pass

                error_code = getattr(e, "errno", None)
                error_msg = str(e).lower()

                # Retry on pool exhausted or deadlock
                is_pool_exhausted = "pool exhausted" in error_msg
                is_deadlock = error_code == 1213 or "deadlock" in error_msg

                if (is_pool_exhausted or is_deadlock) and attempt < max_retries - 1:
                    wait_time = retry_delay * (2**attempt)
                    logger.warning(
                        f"DB error (attempt {attempt + 1}), retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                    continue

                logger.error(f"Database error: {e}")
                raise
            finally:
                if connection and connection.is_connected():
                    connection.close()

        if last_error:
            raise last_error

    @classmethod
    def execute_query(cls, query, params=None, fetch=False):
        """Execute a single query with optional parameters"""
        with cls.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(query, params or ())
                return cursor.fetchall() if fetch else cursor.rowcount
            finally:
                cursor.close()

    @classmethod
    def execute_many(cls, query, data):
        """Execute batch insert/update operations"""
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.executemany(query, data)
                return cursor.rowcount
            finally:
                cursor.close()
