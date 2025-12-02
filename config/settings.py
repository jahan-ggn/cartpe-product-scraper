"""Application configuration settings"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Centralized configuration for the application"""

    # Database Configuration
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "cartpe_scraper")

    # Connection Pool Settings
    POOL_NAME = "cartpe_pool"
    POOL_SIZE = int(os.getenv("POOL_SIZE", 10))

    # Scraping Configuration
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 30))
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", 10))
    REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", 0.5))
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR = "logs"
    LOG_FILE = "scraper.log"


settings = Settings()
