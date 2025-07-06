import time
import json
import logging
import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import requests


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class OutletData:
    name: str
    address: str
    operating_hours: Dict[str, str]
    waze_link: Optional[str]
    phone: Optional[str]
    fax: Optional[str]
    services: List[str]
    longitude: Optional[float] = None
    latitude: Optional[float] = None


class McDonaldsScraperMalaysia:
    def __init__(self, headless: bool = True):
        self.base_url = "https://www.mcdonalds.com.my/locate-us"
        self.headless = headless
        self.driver = None
        self.wait = None

    def _setup_driver(self):
        """Setup Chrome WebDriver with optimized options"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)

    def _filter_by_kuala_lumpur(self):
        """Select 'Kuala Lumpur' from dropdown and click 'Search Now'"""
        try:
            state_dropdown = self.wait.until(
                EC.presence_of_element_located((By.ID, "states"))
            )
            from selenium.webdriver.support.ui import Select

            Select(state_dropdown).select_by_visible_text("Kuala Lumpur")
            logger.info("Selected 'Kuala Lumpur' in dropdown")

            search_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "search-now"))
            )
            search_button.click()
            logger.info("Clicked 'Search Now' button")

            time.sleep(3)
            
        except Exception as e:
            logger.error(f"Error applying Kuala Lumpur filter: {e}")

    def _extract_outlet_data(self, outlet_element) -> Optional[OutletData]:
        """Extract data from a single outlet element
            Args:
                outlet_element (WebElement): The element to extract data from

            Returns:
                Optional[OutletData]: The extracted data, or None if extraction failed
        """
        try:
            # Extract outlet name
            name_selectors = [
                "[class*='addressTitle']",
            ]
            name = self._find_text_by_selectors(outlet_element, name_selectors)

            # Extract address
            address_selectors = [
                "[class*='addressText']",
                "p:contains('Jalan')",
                "p:contains('Kuala Lumpur')",
            ]
            address = self._find_text_by_selectors(outlet_element, address_selectors)

            # Extract phone and fax
            phone = self._extract_contact_info(outlet_element, "Tel:")
            fax = self._extract_contact_info(outlet_element, "Fax:")

            # Extract operating hours
            operating_hours = self._extract_operating_hours(outlet_element)

            # Extract Waze link
            waze_link = self._extract_waze_link(outlet_element)
            latitude, longitude = self._extract_waze_coordinates(waze_link)
            
            # Extract services (from icons)
            services = self._extract_services(outlet_element)

            if not name or not address:
                logger.warning("Missing required data (name or address)")
                return None

            return OutletData(
                name=name,
                address=address,
                operating_hours=operating_hours,
                waze_link=waze_link,
                phone=phone,
                fax=fax,
                services=services,
                latitude=latitude,
                longitude=longitude,
            )

        except Exception as e:
            logger.error(f"Error extracting outlet data: {e}")
            return None

    def _find_text_by_selectors(self, element, selectors: List[str]) -> Optional[str]:
        """Try multiple selectors to find text content
            Args:
                element (WebElement): The element to search in
                selectors (List[str]): The CSS selectors to search for

            Returns:
                Optional[str]: The text content, or None if not found
        """
        for selector in selectors:
            try:
                found_element = element.find_element(By.CSS_SELECTOR, selector)
                text = found_element.text.strip()
                if text:
                    return text
            except NoSuchElementException:
                continue
        return None

    def _extract_contact_info(self, element, contact_type: str) -> Optional[str]:
        """Extract phone or fax number
            Args:
                element (WebElement): The element to search in
                contact_type (str): The type of contact to extract (e.g., "Tel:")

            Returns:
                Optional[str]: The extracted phone number or fax number, or None if not found
        """
        try:
            text_content = element.text
            pattern = rf"{contact_type}\s*([0-9\-\s]+)"
            match = re.search(pattern, text_content)
            if match:
                return match.group(1).strip()
        except Exception:
            pass
        return None

    def _extract_operating_hours(self, element) -> Dict[str, str]:
        """Extract operating hours information
            Args:
                element (WebElement): The element to search in

            Returns:
                Dict[str, str]: The extracted operating hours information, or an empty dict if not found
        """
        hours = {}
        try:
            # Look for operating hours text
            text_content = element.text.lower()

            # Check for 24 hours
            if "24 hours" in text_content or "24hrs" in text_content:
                hours["type"] = "24_hours"
                return hours

            # Look for specific hour patterns
            hour_patterns = [
                r"(\d{1,2}):?(\d{2})?\s*([ap]m)\s*-\s*(\d{1,2}):?(\d{2})?\s*([ap]m)",
                r"(\d{1,2})\s*([ap]m)\s*-\s*(\d{1,2})\s*([ap]m)",
            ]

            for pattern in hour_patterns:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                if matches:
                    hours["pattern"] = "standard"
                    hours["times"] = matches
                    break

        except Exception as e:
            logger.warning(f"Error extracting operating hours: {e}")

        return hours

    def _extract_waze_link(self, element) -> Optional[str]:
        """Click Waze link button, wait for redirect, extract Waze URL with lat/lon
            Args:
                element (WebElement): The element to search in

            Returns:
                Optional[str]: The extracted Waze URL, or None if not found
        """
        try:
            original_window = self.driver.current_window_handle

            # Find Waze button and click it in a new tab
            waze_element = element.find_element(
                By.XPATH, ".//a[contains(text(), 'Waze')]"
            )

            # Open in new tab
            ActionChains(self.driver).key_down(Keys.CONTROL).click(waze_element).key_up(
                Keys.CONTROL
            ).perform()

            # Wait for the new tab to open
            WebDriverWait(self.driver, 5).until(lambda d: len(d.window_handles) > 1)

            # Switch to the new window
            new_window = [handle for handle in self.driver.window_handles if handle != original_window][0]
            self.driver.switch_to.window(new_window)

            # Wait for Waze to redirect and resolve
            for _ in range(15):  # max 7.5s
                current_url = self.driver.current_url
                if "to=ll." in current_url:
                    break
                time.sleep(0.5)

            waze_url = self.driver.current_url

            self.driver.close()
            self.driver.switch_to.window(original_window)

            # Final check
            if "to=ll." in waze_url:
                return waze_url
            else:
                logger.warning("Waze URL loaded but no coordinates found")
                return None

        except Exception as e:
            logger.warning(f"Failed to extract Waze URL: {e}")
            return None


    def _extract_waze_coordinates(self, waze_url: Optional[str]) -> (Optional[float], Optional[float]): # type: ignore
        """Extract latitude and longitude from Waze URL
            Args:
                waze_url (Optional[str]): The Waze URL to extract coordinates from

            Returns:
                Tuple[Optional[float], Optional[float]]: The extracted latitude and longitude, or None if not found
        """
        if not waze_url:
            return None, None
        match = re.search(r"to=ll\.([0-9\.-]+)%2C([0-9\.-]+)", waze_url)
        if match:
            lat, lon = match.groups()
            return float(lat), float(lon)
        return None, None

    def _extract_services(self, element) -> List[str]:
        """Extract available services from icons
            Args:
                element (WebElement): The element to search in

            Returns:
                List[str]: The extracted services, or an empty list if not found
        """
        services = []
        try:
            # Common service indicators
            service_mapping = {
                "drive": "Drive-Thru",
                "mccafe": "McCafe",
                "wifi": "WiFi",
                "parking": "Parking",
                "party": "Birthday Party",
                "delivery": "Delivery",
                "24": "24 Hours",
            }

            element_html = element.get_attribute("outerHTML").lower()
            element_text = element.text.lower()

            for key, service in service_mapping.items():
                if key in element_html or key in element_text:
                    services.append(service)

        except Exception:
            pass
        return services

    def _get_outlet_elements(self) -> List:
        """Find all outlet elements on the page"""
        outlet_selectors = [
            ".outlet-card",
            ".store-card",
            ".location-item",
            "[class*='outlet']",
            "[class*='store']",
            ".card",
        ]

        for selector in outlet_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.info(
                        f"Found {len(elements)} outlets using selector: {selector}"
                    )
                    return elements
            except Exception:
                continue

        # Fallback: try to find elements with McDonald's name
        try:
            elements = self.driver.find_elements(
                By.XPATH, "//*[contains(text(), 'McDonald')]/.."
            )
            if elements:
                logger.info(f"Found {len(elements)} outlets using fallback method")
                return elements
        except Exception:
            pass

        return []
    
    def _geocode_with_nominatim(self, address: str) -> Optional[Dict[str, float]]:
        """Geocode an address using Nominatim
            Args:
                address (str): The address to geocode

            Returns:
                Optional[Dict[str, float]]: The geocoded coordinates, or None if not found            
        """
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": address,
                "format": "jsonv2",
                "polygon_geojson": 0,
            }
            headers = {
                "User-Agent": "mindhive-mcdonalds-scraper"
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            results = response.json()

            if results:
                return {
                    "latitude": float(results[0]["lat"]),
                    "longitude": float(results[0]["lon"]),
                }

        except Exception as e:
            logger.warning(f"Nominatim geocoding failed for '{address}': {e}")
        return None

    def _handle_pagination(self) -> bool:
        """Handle pagination to get all pages"""
        try:
            # Look for next page button
            next_buttons = [
                "button:contains('Next')",
                ".next-page",
                "[aria-label*='Next']",
                ".pagination-next",
            ]

            for selector in next_buttons:
                try:
                    next_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if next_btn.is_enabled():
                        next_btn.click()
                        time.sleep(3)
                        return True
                except NoSuchElementException:
                    continue

        except Exception as e:
            logger.debug(f"Pagination handling: {e}")

        return False

    def scrape_outlets(self) -> List[OutletData]:
        """Main scraping method"""
        all_outlets = []

        try:
            self._setup_driver()
            logger.info(f"Navigating to {self.base_url}")

            self.driver.get(self.base_url)
            time.sleep(5)

            # Apply KL filter
            self._filter_by_kuala_lumpur()

            page_num = 1
            while True:
                logger.info(f"Scraping page {page_num}")

                # Get outlet elements
                outlet_elements = self._get_outlet_elements()

                if not outlet_elements:
                    logger.warning("No outlet elements found on this page")
                    break

                # Extract data from each outlet
                page_outlets = []
                for element in outlet_elements:
                    outlet_data = self._extract_outlet_data(element)
                    if outlet_data:
                        page_outlets.append(outlet_data)

                logger.info(
                    f"Extracted {len(page_outlets)} outlets from page {page_num}"
                )
                all_outlets.extend(page_outlets)

                # Try to go to next page
                if not self._handle_pagination():
                    logger.info("No more pages found")
                    break

                page_num += 1

                # Safety limit
                if page_num > 10:
                    logger.warning("Reached page limit (10)")
                    break

        except Exception as e:
            logger.error(f"Scraping error: {e}")

        finally:
            if self.driver:
                self.driver.quit()

        logger.info(f"Total outlets scraped: {len(all_outlets)}")
        return all_outlets
    

    def save_to_json(
        self, outlets: List[OutletData], filename: str = "./mcdonalds_outlets.json"
    ):
        """Save scraped data to JSON file
            Args:
                outlets (List[OutletData]): The scraped outlet data
                filename (str): The filename to save the data to
        """
        data = []
        for outlet in outlets:
            data.append(
                {
                    "name": outlet.name,
                    "address": outlet.address,
                    "operating_hours": outlet.operating_hours,
                    "waze_link": outlet.waze_link,
                    "phone": outlet.phone,
                    "fax": outlet.fax,
                    "services": outlet.services,
                    "latitude": outlet.latitude,
                    "longitude": outlet.longitude,
                }
            )

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Data saved to {filename}")


if __name__ == "__main__":
    """Main function to run the scraper
        Command to run: python -m scripts.mcdonalds_scraper.py
    """
    scraper = McDonaldsScraperMalaysia(headless=True)  # Set to True for production
    outlets = scraper.scrape_outlets()

    if outlets:
        scraper.save_to_json(outlets)
        logger.info(f"Successfully scraped {len(outlets)} outlets")
    else:
        logger.info("No outlets found")
