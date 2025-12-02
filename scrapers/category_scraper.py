"""Category scraper for extracting categories from store pages"""

import re
import requests
import logging
import time
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from config.settings import settings

logger = logging.getLogger(__name__)


class CategoryScraper:
    """Scrapes categories from store /allcategory.html pages"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": settings.USER_AGENT})

    def extract_categories(self, store_data: Dict) -> List[Dict]:
        """
        Extract all categories from store's allcategory page

        Args:
            store_data: Dictionary containing store information

        Returns:
            List of category dictionaries
        """
        store_id = store_data["store_id"]
        store_name = store_data["store_name"]
        base_url = store_data["base_url"].rstrip("/")

        categories = []

        try:
            # Construct allcategory URL
            allcategory_url = f"{base_url}/allcategory.html"

            logger.info(f"Fetching categories for store: {store_name} (ID: {store_id})")

            # Fetch page
            response = self.session.get(
                allcategory_url, timeout=settings.REQUEST_TIMEOUT
            )
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, "lxml")

            # Find all category elements
            category_elements = soup.select("div.cat-area a")

            for element in category_elements:
                try:
                    # Extract category URL
                    category_url = element.get("href", "").strip()

                    # Extract category name from h4 tag
                    h4_tag = element.find("h4", class_="cat-text")
                    if not h4_tag:
                        continue

                    category_name = h4_tag.get_text(strip=True)

                    # Extract category slug from URL
                    # Example: https://watchhouse11.cartpe.in/mens-watch.html -> mens-watch
                    category_slug = self._extract_slug_from_url(category_url)

                    if category_name and category_url and category_slug:
                        categories.append(
                            {
                                "store_id": store_id,
                                "category_name": category_name,
                                "category_slug": category_slug,
                                "category_url": category_url,
                            }
                        )

                        logger.debug(
                            f"Found category: {category_name} ({category_slug})"
                        )

                except Exception as e:
                    logger.warning(f"Error parsing category element: {e}")
                    continue

            logger.info(f"Extracted {len(categories)} categories from {store_name}")

        except requests.RequestException as e:
            logger.error(f"Error fetching categories for {store_name}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error for {store_name}: {str(e)}")
        finally:
            # Add delay to be respectful
            time.sleep(settings.REQUEST_DELAY)

        return categories

    def _extract_slug_from_url(self, url: str) -> Optional[str]:
        """
        Extract slug from category URL

        Args:
            url: Full category URL

        Returns:
            Category slug or None
        """
        try:
            # Extract the last part of URL before .html
            # Example: https://watchhouse11.cartpe.in/mens-watch.html -> mens-watch
            match = re.search(r"/([^/]+)\.html$", url)
            if match:
                return match.group(1)
            return None
        except Exception as e:
            logger.warning(f"Error extracting slug from URL {url}: {e}")
            return None

    def close(self):
        """Close the requests session"""
        self.session.close()
