"""Main entry point for product scraping"""

import logging
from utils.logger import setup_logger
from concurrent.futures import ThreadPoolExecutor, as_completed
from scrapers.product_scraper import ProductScraper, TokenExpiredException
from scrapers.token_scraper import TokenScraper
from services.database_service import StoreService, CategoryService, ProductService
from config.settings import settings

setup_logger()
logger = logging.getLogger(__name__)


def scrape_store_products(store_data: dict) -> tuple:
    """
    Scrape all products for a single store

    Args:
        store_data: Store information dictionary

    Returns:
        Tuple of (store_id, store_name, product_count, success_status)
    """
    store_id = store_data["store_id"]
    store_name = store_data["store_name"]

    scraper = ProductScraper()
    total_products = 0

    try:
        # Get all categories for this store
        categories = CategoryService.get_categories_by_store(store_id)

        if not categories:
            logger.warning(f"No categories found for {store_name}")
            return (store_id, store_name, 0, False)

        logger.info(f"Processing {len(categories)} categories for {store_name}")

        # Process each category
        for category in categories:
            try:
                # Extract products
                products = scraper.extract_products(store_data, category)

                if products:
                    # Batch insert/update in database
                    ProductService.bulk_upsert_products(products)
                    total_products += len(products)
                    logger.info(
                        f"Saved {len(products)} products for {category['category_name']}"
                    )

            except TokenExpiredException:
                logger.warning(f"Token expired for {store_name}. Re-fetching token...")

                # Re-fetch token
                token_scraper = TokenScraper()
                new_token = token_scraper.extract_token(store_data)
                token_scraper.close()

                if new_token:
                    StoreService.update_store_token(store_id, new_token)
                    store_data["web_token"] = new_token
                    logger.info(f"Token refreshed for {store_name}. Retrying...")

                    # Retry this category
                    products = scraper.extract_products(store_data, category)
                    if products:
                        ProductService.bulk_upsert_products(products)
                        total_products += len(products)
                else:
                    logger.error(f"Failed to refresh token for {store_name}")
                    break

            except Exception as e:
                logger.error(
                    f"Error processing category {category['category_name']}: {e}"
                )
                continue

        scraper.close()
        return (store_id, store_name, total_products, True)

    except Exception as e:
        logger.error(f"Error processing store {store_name}: {e}")
        scraper.close()
        return (store_id, store_name, 0, False)


def run_product_scraping():
    """Main function to scrape products for all stores"""
    logger.info("=" * 80)
    logger.info("Starting Product Scraping Process")
    logger.info("=" * 80)

    # Get all stores
    stores = StoreService.get_all_stores()

    if not stores:
        logger.info("No stores found in database. Exiting.")
        return

    logger.info(f"Processing {len(stores)} stores with {settings.MAX_WORKERS} workers")

    # Statistics
    successful = 0
    failed = 0
    total_products = 0

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=settings.MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_store = {
            executor.submit(scrape_store_products, store): store for store in stores
        }

        # Process completed tasks
        for future in as_completed(future_to_store):
            store_id, store_name, product_count, success = future.result()

            if success:
                successful += 1
                total_products += product_count
                logger.info(
                    f"✓ Successfully processed: {store_name} ({product_count} products)"
                )
            else:
                failed += 1
                logger.error(f"✗ Failed to process: {store_name}")

    # Summary
    logger.info("=" * 80)
    logger.info("Product Scraping Complete")
    logger.info(f"Total Stores: {len(stores)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total Products Scraped: {total_products}")
    logger.info("=" * 80)


if __name__ == "__main__":
    try:
        run_product_scraping()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
