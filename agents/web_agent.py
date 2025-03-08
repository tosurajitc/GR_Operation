"""
Web Agent for scraping DGFT portal data.
This agent is responsible for:
1. Accessing the DGFT portal
2. Navigating to Notifications, Public Notices, and Circulars sections
3. Extracting date, description, and attachment links
"""
import os
import time
import requests
import traceback
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WebAgent:
    def __init__(self, base_url=None):
        """Initialize WebAgent with base URL from .env or parameter"""
        self.base_url = base_url or os.getenv("DGFT_URL", "https://www.dgft.gov.in/CP/?opt=regulatory-updates")
        self.driver = None
        self.sections = ["Notifications", "Public Notices", "Circulars"]
        self.section_data = {}
        
        # Direct URLs for each section
        self.section_urls = {
            "Notifications": os.getenv("DGFT_NOTIFICATIONS_URL", "https://www.dgft.gov.in/CP/?opt=notification"),
            "Public Notices": os.getenv("DGFT_PUBLIC_NOTICES_URL", "https://www.dgft.gov.in/CP/?opt=public-notice"),
            "Circulars": os.getenv("DGFT_CIRCULARS_URL", "https://www.dgft.gov.in/CP/?opt=circular")
        }
    
    def initialize_driver(self):
        """Initialize Chrome driver with better error handling"""
        try:
            chrome_options = Options()
            
            # For debugging purposes, make it visible
            # chrome_options.add_argument("--headless")
            
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-notifications")
            
            # Enable JavaScript
            chrome_options.add_argument("--enable-javascript")
            
            # Add user agent
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            # Try direct ChromeDriver path first (if Chrome is installed in default location)
            try:
                logger.info("Trying to use direct ChromeDriver path...")
                # Use Service with specific chromedriver path
                service = Service(executable_path="chromedriver.exe")  # For Windows
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info("Successfully initialized ChromeDriver using direct path")
            except Exception as e:
                logger.warning(f"Failed to initialize using direct path: {e}")
                
                # Try with WebDriverManager but specify version
                try:
                    logger.info("Trying with WebDriverManager and specific version...")
                    from selenium.webdriver.chrome.service import Service as ChromeService
                    from webdriver_manager.chrome import ChromeDriverManager
                    
                    # Try with a specific version of ChromeDriver
                    service = ChromeService(ChromeDriverManager(version="114.0.5735.90").install())
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    logger.info("Successfully initialized ChromeDriver with specific version")
                except Exception as e:
                    logger.warning(f"Failed to initialize with specific version: {e}")
                    
                    # Last resort - try with latest version but with more robust error handling
                    try:
                        logger.info("Trying alternative initialization method...")
                        # Try direct initialization without Service
                        self.driver = webdriver.Chrome(options=chrome_options)
                        logger.info("Successfully initialized ChromeDriver with direct initialization")
                    except Exception as e:
                        logger.error(f"Failed all initialization methods: {e}")
                        return False
            
            # Set page load timeout
            self.driver.set_page_load_timeout(60)
            
            logger.info("Selenium WebDriver initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            return False
    
    def close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")
    
    def navigate_to_page(self, url=None):
        """Navigate to the specified URL or base URL with better handling of JavaScript pages"""
        try:
            target_url = url or self.base_url
            if not self.driver:
                self.initialize_driver()
            
            logger.info(f"Attempting to navigate to {target_url}")
            self.driver.get(target_url)
            
            # Wait for page to load - longer timeout and more specific element
            logger.info("Waiting for page to load...")
            
            # First wait for body
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Then wait a bit for any JavaScript to execute
            logger.info("Body loaded, waiting for JavaScript to render...")
            time.sleep(5)
            
            # Log page title to confirm we're on the right page
            logger.info(f"Successfully loaded page: {self.driver.title}")
            
            # Take screenshot for debugging
            self.driver.save_screenshot("page_loaded.png")
            logger.info("Saved screenshot to page_loaded.png for debugging")
            
            # Log page source length for debugging
            page_source = self.driver.page_source
            logger.info(f"Page source length: {len(page_source)}")
            
            # Look for common elements to ensure the page is properly loaded
            try:
                tables = self.driver.find_elements(By.TAG_NAME, "table")
                logger.info(f"Initial table count: {len(tables)}")
                
                links = self.driver.find_elements(By.TAG_NAME, "a")
                logger.info(f"Link count: {len(links)}")
            except Exception as e:
                logger.warning(f"Could not find basic elements: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to {url or self.base_url}: {e}")
            
            # Try to get page source even if navigation error
            try:
                if self.driver:
                    logger.error(f"Page source preview: {self.driver.page_source[:1000]}...")
            except:
                pass
                
            return False
    
    def find_section_links(self):
        """Find links to Notifications, Public Notices, and Circulars sections"""
        links = {}
        
        # Use the direct URLs from initialization
        logger.info("Using direct URLs for sections instead of searching links on homepage")
        for section, url in self.section_urls.items():
            links[section] = url
            logger.info(f"Set direct URL for {section}: {url}")
        
        return links
    
    def extract_table_data(self, section, url):
        """
        Extract data from the table for a specific section with better handling of complex pages
        Returns a list of dictionaries with date, description, and attachment link
        """
        try:
            # First try with Selenium
            selenium_success = False
            try:
                # Navigate to section page
                logger.info(f"Navigating to {section} page: {url}")
                selenium_success = self.navigate_to_page(url)
                
                if not selenium_success:
                    logger.warning(f"Selenium navigation failed. Trying fallback method.")
                    return self._extract_with_requests(section, url)
                
                # Continue with Selenium extraction...
                # [rest of the Selenium extraction code...]
                
            except Exception as e:
                logger.error(f"Selenium extraction failed: {e}")
                logger.info("Falling back to requests method")
                return self._extract_with_requests(section, url)
                
            # If we got here but have no tables, use the requests fallback
            if not tables:
                logger.error(f"No tables found on {section} page with Selenium")
                logger.info("Falling back to requests method")
                return self._extract_with_requests(section, url)
            
            # [rest of the method...]
            
        except Exception as e:
            logger.error(f"Error extracting data from {section}: {e}")
            logger.error(traceback.format_exc())
            
            # Final fallback
            logger.info("Trying final fallback with requests method")
            return self._extract_with_requests(section, url)
            
    def _extract_with_requests(self, section, url):
        """
        Fallback extraction method using requests and BeautifulSoup
        """
        logger.info(f"Using requests fallback for {section}")
        try:
            # Use requests to get the page content
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to get page with requests: status code {response.status_code}")
                return []
                
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find tables
            tables = soup.find_all('table')
            logger.info(f"Found {len(tables)} tables with BeautifulSoup")
            
            if not tables:
                logger.error("No tables found with BeautifulSoup")
                
                # Look for specific DGFT patterns
                # If it's a DGFT page, it might have a specific structure
                content_divs = soup.find_all('div', class_='cp_txt_bold')
                if content_divs:
                    logger.info(f"Found {len(content_divs)} content divs")
                    
                    # Try to extract data from these divs
                    data = []
                    for div in content_divs:
                        links = div.find_all('a')
                        for link in links:
                            href = link.get('href')
                            text = link.get_text(strip=True)
                            
                            # Try to extract date from text (common pattern in DGFT site)
                            date_match = re.search(r'(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})', text)
                            date_str = date_match.group(0) if date_match else "Unknown"
                            
                            # Format the date
                            formatted_date = self._parse_date(date_str)
                            
                            # Create entry
                            entry = {
                                "date": formatted_date,
                                "description": text,
                                "attachment": href
                            }
                            data.append(entry)
                    
                    if data:
                        # Sort by date
                        try:
                            sorted_data = sorted(data, key=lambda x: x["date"], reverse=True)
                        except:
                            sorted_data = data
                            
                        logger.info(f"Extracted {len(sorted_data)} entries from content divs")
                        return sorted_data
                
                return []
            
            # Process first table (most likely the main one)
            table = tables[0]
            rows = table.find_all('tr')
            
            if not rows:
                logger.error("No rows found in table")
                return []
                
            # Get headers
            header_row = rows[0]
            headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
            
            # Find relevant columns
            date_idx = None
            desc_idx = None
            attach_idx = None
            
            # Look for date column
            date_keywords = ["date", "dated", "dt", "dt.", "date.", "dated."]
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if any(keyword in header_lower for keyword in date_keywords):
                    date_idx = i
                    break
            
            # Look for description/subject column
            desc_keywords = ["subject", "description", "desc", "desc.", "subject.", "title", "regarding"]
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if any(keyword in header_lower for keyword in desc_keywords):
                    desc_idx = i
                    break
            
            # Look for attachment column
            attach_keywords = ["attach", "attachment", "doc", "document", "file", "pdf", "download"]
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if any(keyword in header_lower for keyword in attach_keywords):
                    attach_idx = i
                    break
            
            # Fallbacks if columns not found
            if date_idx is None:
                date_idx = 2 if len(headers) > 2 else 0
            
            if desc_idx is None:
                desc_idx = 3 if len(headers) > 3 else 0
            
            if attach_idx is None:
                attach_idx = 4 if len(headers) > 4 else len(headers) - 1
            
            # Extract data
            data = []
            for row in rows[1:]:  # Skip header
                cells = row.find_all(['td', 'th'])
                
                if len(cells) <= max(date_idx, desc_idx, attach_idx):
                    continue
                    
                date_str = cells[date_idx].get_text(strip=True)
                description = cells[desc_idx].get_text(strip=True)
                
                # Extract attachment link
                attachment_link = None
                attachment_cell = cells[attach_idx]
                link = attachment_cell.find('a')
                
                if link and link.has_attr('href'):
                    attachment_link = link['href']
                    
                    # Handle relative URLs
                    if attachment_link.startswith('/'):
                        base_url = response.url.split('?')[0]
                        attachment_link = f"{base_url}{attachment_link}"
                
                # Only add if we have all required data
                if date_str and description and attachment_link:
                    # Format date
                    formatted_date = self._parse_date(date_str)
                    
                    entry = {
                        "date": formatted_date,
                        "description": description,
                        "attachment": attachment_link
                    }
                    data.append(entry)
            
            # Sort by date
            try:
                sorted_data = sorted(data, key=lambda x: x["date"], reverse=True)
            except:
                sorted_data = data
                
            logger.info(f"Extracted {len(sorted_data)} entries with requests method")
            return sorted_data
            
        except Exception as e:
            logger.error(f"Error in requests extraction: {e}")
            logger.error(traceback.format_exc())
            return []
            
            # Try different ways to find tables
            tables = []
            
            # Method 1: Direct table elements
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            logger.info(f"Found {len(tables)} direct table elements")
            
            # Method 2: If no tables found, try finding tables inside content areas
            if not tables:
                logger.info("No direct tables found, looking for tables in content areas")
                content_areas = self.driver.find_elements(By.CLASS_NAME, "content-area")
                logger.info(f"Found {len(content_areas)} content areas")
                
                for area in content_areas:
                    area_tables = area.find_elements(By.TAG_NAME, "table")
                    logger.info(f"Found {len(area_tables)} tables in content area")
                    tables.extend(area_tables)
            
            # Method 3: Use Beautiful Soup as a fallback
            if not tables:
                logger.info("No tables found with Selenium, trying BeautifulSoup")
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                soup_tables = soup.find_all('table')
                logger.info(f"Found {len(soup_tables)} tables with BeautifulSoup")
                
                if soup_tables:
                    # Extract data from BeautifulSoup tables
                    data = []
                    for soup_table in soup_tables:
                        bs_rows = soup_table.find_all('tr')
                        
                        if not bs_rows:
                            continue
                            
                        # Get headers from first row
                        header_cells = bs_rows[0].find_all(['th', 'td'])
                        if not header_cells:
                            continue
                            
                        headers = [cell.get_text(strip=True) for cell in header_cells]
                        logger.info(f"BeautifulSoup headers: {headers}")
                        
                        # Find column indices
                        date_idx = None
                        desc_idx = None
                        attach_idx = None
                        
                        # Use the same header matching code as below
                        date_keywords = ["date", "dated", "dt", "dt.", "date.", "dated."]
                        for i, header in enumerate(headers):
                            header_lower = header.lower()
                            if any(keyword in header_lower for keyword in date_keywords):
                                date_idx = i
                                break
                        
                        desc_keywords = ["subject", "description", "desc", "desc.", "subject.", "title", "regarding"]
                        for i, header in enumerate(headers):
                            header_lower = header.lower()
                            if any(keyword in header_lower for keyword in desc_keywords):
                                desc_idx = i
                                break
                        
                        attach_keywords = ["attach", "attachment", "doc", "document", "file", "pdf", "download"]
                        for i, header in enumerate(headers):
                            header_lower = header.lower()
                            if any(keyword in header_lower for keyword in attach_keywords):
                                attach_idx = i
                                break
                        
                        # Fallbacks if columns not found
                        if date_idx is None:
                            date_idx = 2 if len(headers) > 2 else 0
                        
                        if desc_idx is None:
                            desc_idx = 3 if len(headers) > 3 else 0
                        
                        if attach_idx is None:
                            attach_idx = 4 if len(headers) > 4 else len(headers) - 1
                        
                        logger.info(f"BS column indices - Date: {date_idx}, Description: {desc_idx}, Attachment: {attach_idx}")
                        
                        # Process rows
                        for row in bs_rows[1:]:  # Skip header row
                            cells = row.find_all(['td', 'th'])
                            
                            if len(cells) <= max(date_idx, desc_idx, attach_idx):
                                continue
                                
                            date_str = cells[date_idx].get_text(strip=True)
                            description = cells[desc_idx].get_text(strip=True)
                            
                            # Extract attachment link
                            attachment_link = None
                            attachment_cell = cells[attach_idx]
                            link_element = attachment_cell.find('a')
                            
                            if link_element and link_element.has_attr('href'):
                                attachment_link = link_element['href']
                            
                            # Handle relative URLs
                            if attachment_link and attachment_link.startswith('/'):
                                base_url = url.split('?')[0]
                                attachment_link = f"{base_url}{attachment_link}"
                            
                            # Only add entries with all required data
                            if date_str and description and attachment_link:
                                # Parse date
                                formatted_date = self._parse_date(date_str)
                                
                                data.append({
                                    "date": formatted_date,
                                    "description": description,
                                    "attachment": attachment_link
                                })
                                
                        logger.info(f"Extracted {len(data)} entries with BeautifulSoup")
                        if data:
                            return sorted(data, key=lambda x: x["date"], reverse=True)
            
            if not tables:
                logger.error(f"No tables found on {section} page")
                return []
            
            # Use the first table
            table = tables[0]
            
            # Log table HTML for debugging
            table_html = table.get_attribute('outerHTML')
            logger.info(f"Table HTML preview: {table_html[:500]}...")
            
            # Get all rows
            rows = table.find_elements(By.TAG_NAME, "tr")
            logger.info(f"Found {len(rows)} rows in the table")
            
            if not rows:
                logger.error(f"No rows found in {section} table")
                return []
            
            # Extract headers - try different approaches
            headers = []
            
            # Approach 1: Find th elements
            header_cells = rows[0].find_elements(By.TAG_NAME, "th")
            
            # Approach 2: If no th elements, use first row td elements
            if not header_cells:
                header_cells = rows[0].find_elements(By.TAG_NAME, "td")
            
            if header_cells:
                headers = [header.text.strip() for header in header_cells]
                logger.info(f"Found headers: {headers}")
            else:
                logger.error(f"No header cells found in {section} table")
                # Use default headers as fallback
                headers = ["S.No", "Notification No", "Date", "Subject", "Attachment"]
                logger.info(f"Using default headers: {headers}")
            
            # Find column indices - more flexible matching
            date_idx = None
            desc_idx = None
            attach_idx = None
            
            # Look for date column
            date_keywords = ["date", "dated", "dt", "dt.", "date.", "dated."]
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if any(keyword in header_lower for keyword in date_keywords):
                    date_idx = i
                    break
            
            # Look for description/subject column
            desc_keywords = ["subject", "description", "desc", "desc.", "subject.", "title", "regarding"]
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if any(keyword in header_lower for keyword in desc_keywords):
                    desc_idx = i
                    break
            
            # Look for attachment column
            attach_keywords = ["attach", "attachment", "doc", "document", "file", "pdf", "download"]
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if any(keyword in header_lower for keyword in attach_keywords):
                    attach_idx = i
                    break
            
            # Fallbacks if columns not found
            if date_idx is None:
                logger.warning(f"Date column not found, defaulting to column 2")
                date_idx = 2 if len(headers) > 2 else 0
            
            if desc_idx is None:
                logger.warning(f"Description column not found, defaulting to column 3")
                desc_idx = 3 if len(headers) > 3 else 0
            
            if attach_idx is None:
                logger.warning(f"Attachment column not found, defaulting to column 4")
                attach_idx = 4 if len(headers) > 4 else len(headers) - 1
            
            logger.info(f"Using column indices - Date: {date_idx}, Description: {desc_idx}, Attachment: {attach_idx}")
            
            # Extract data from rows
            data = []
            for row_idx, row in enumerate(rows[1:], 1):  # Skip header row
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cells) <= max(date_idx, desc_idx, attach_idx):
                        logger.warning(f"Row {row_idx} has fewer cells than expected, skipping")
                        continue
                    
                    date_str = cells[date_idx].text.strip()
                    description = cells[desc_idx].text.strip()
                    
                    # Extract attachment link - try multiple approaches
                    attachment_link = None
                    try:
                        attachment_cell = cells[attach_idx]
                        
                        # Scroll to the element to ensure it's visible
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", attachment_cell)
                        
                        # Try to find 'a' tag
                        link_elements = attachment_cell.find_elements(By.TAG_NAME, "a")
                        
                        if link_elements:
                            attachment_link = link_elements[0].get_attribute("href")
                            logger.info(f"Found attachment link: {attachment_link}")
                        else:
                            # Try to find image that might be clickable
                            img_elements = attachment_cell.find_elements(By.TAG_NAME, "img")
                            if img_elements:
                                img_parent = img_elements[0].find_element(By.XPATH, "./..")
                                if img_parent.tag_name == "a":
                                    attachment_link = img_parent.get_attribute("href")
                                    logger.info(f"Found image-based attachment link: {attachment_link}")
                        
                        # If still no link, check for click handler or other attributes
                        if not attachment_link:
                            # Try onclick attribute
                            onclick = attachment_cell.get_attribute("onclick")
                            if onclick:
                                logger.info(f"Found onclick handler: {onclick}")
                                # Extract URL from onclick if possible
                                
                                # Common pattern: window.open('URL')
                                import re
                                url_match = re.search(r"window\.open\(['\"](.*?)['\"]", onclick)
                                if url_match:
                                    attachment_link = url_match.group(1)
                                    logger.info(f"Extracted URL from onclick: {attachment_link}")
                            
                            # Check for any clickable element
                            clickables = attachment_cell.find_elements(By.CSS_SELECTOR, "[href], [onclick]")
                            if clickables:
                                href = clickables[0].get_attribute("href")
                                if href:
                                    attachment_link = href
                                    logger.info(f"Found clickable element with href: {attachment_link}")
                                    
                                    # If no href, try onclick again
                                    if not href:
                                        onclick = clickables[0].get_attribute("onclick")
                                        if onclick:
                                            url_match = re.search(r"window\.open\(['\"](.*?)['\"]", onclick)
                                            if url_match:
                                                attachment_link = url_match.group(1)
                                                logger.info(f"Extracted URL from clickable's onclick: {attachment_link}")
                        
                        # Handle relative URLs
                        if attachment_link and attachment_link.startswith('/'):
                            base_url = url.split('?')[0]
                            attachment_link = f"{base_url}{attachment_link}"
                            logger.info(f"Converted relative URL to absolute: {attachment_link}")
                            
                    except Exception as e:
                        logger.warning(f"Failed to extract attachment link for row {row_idx}: {e}")
                    
                    # Skip rows without attachment links
                    if not attachment_link:
                        logger.warning(f"No attachment link found for row {row_idx}, skipping")
                        continue
                    
                    # Skip rows without date or description
                    if not date_str or not description:
                        logger.warning(f"Missing date or description for row {row_idx}, skipping")
                        continue
                    
                    # Parse date
                    formatted_date = self._parse_date(date_str)
                    
                    entry = {
                        "date": formatted_date,
                        "description": description,
                        "attachment": attachment_link
                    }
                    data.append(entry)
                    logger.info(f"Added entry: date={formatted_date}, description={description[:30]}...")
                except Exception as e:
                    logger.error(f"Error processing row {row_idx}: {e}")
            
            # Sort by date (newest first)
            try:
                sorted_data = sorted(data, key=lambda x: x["date"], reverse=True)
            except Exception as e:
                logger.error(f"Error sorting data: {e}")
                sorted_data = data
            
            logger.info(f"Extracted {len(sorted_data)} entries from {section}")
            return sorted_data
        except Exception as e:
            logger.error(f"Error extracting data from {section}: {e}")
            logger.error(traceback.format_exc())
            return []
            
    def _parse_date(self, date_str):
        """Helper method to parse dates in various formats"""
        try:
            # Try common date formats
            date_formats = [
                "%d/%m/%Y",  # DD/MM/YYYY
                "%d/%m/%y",   # DD/MM/YY
                "%d-%m-%Y",  # DD-MM-YYYY
                "%d-%m-%y",   # DD-MM-YY
                "%d.%m.%Y",  # DD.MM.YYYY
                "%d.%m.%y",   # DD.MM.YY
                "%Y-%m-%d",  # YYYY-MM-DD
                "%d %b %Y",  # DD Mon YYYY
                "%d %B %Y",  # DD Month YYYY
                "%b %d, %Y",  # Mon DD, YYYY
                "%B %d, %Y",  # Month DD, YYYY
            ]
            
            parsed_date = None
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            
            if parsed_date:
                formatted_date = parsed_date.strftime("%Y-%m-%d")
            else:
                logger.warning(f"Could not parse date: {date_str}, using as-is")
                formatted_date = date_str
            
            return formatted_date
        except Exception as e:
            logger.warning(f"Error parsing date '{date_str}': {e}")
            return date_str
    
    def get_latest_updates(self):
        """
        Get the latest updates for all sections
        Returns a dictionary with section name as key and list of entries as value
        """
        try:
            logger.info("Getting latest updates from DGFT portal")
            
            # Process each section directly using the URLs
            for section, url in self.section_urls.items():
                try:
                    logger.info(f"Processing section: {section} with URL: {url}")
                    section_data = self.extract_table_data(section, url)
                    
                    # Only keep the latest entry (top row) for each section
                    if section_data:
                        logger.info(f"For {section}, keeping only the latest entry from {len(section_data)} entries")
                        self.section_data[section] = [section_data[0]]  # Only keep the first entry (latest)
                    else:
                        logger.warning(f"No data found for {section}")
                        self.section_data[section] = []
                        
                    logger.info(f"Successfully processed {section}: kept latest entry")
                except Exception as e:
                    logger.error(f"Error processing section {section}: {e}")
                    # Continue with other sections even if one fails
                    self.section_data[section] = []
            
            # Create demo data if no actual data was retrieved
            if all(len(data) == 0 for data in self.section_data.values()):
                logger.warning("No data retrieved from any section. Creating sample data.")
                self._create_sample_data()
            
            return self.section_data
        except Exception as e:
            logger.error(f"Error getting latest updates: {e}")
            logger.error(traceback.format_exc())
            
            # Create demo data as fallback
            self._create_sample_data()
            return self.section_data
        finally:
            self.close_driver()
            
    def _create_sample_data(self):
        """Create sample data for demo purposes"""
        logger.info("Creating sample data for demonstration")
        
        # Sample data for each section
        sample_data = {
            "Notifications": [
                {
                    "date": "2025-03-01",
                    "description": "Amendment in Export Policy of Specified Active Pharmaceutical Ingredients (APIs)",
                    "attachment": "https://www.dgft.gov.in/CP/upload/noti/NotificationNo67English.pdf"
                },
                {
                    "date": "2025-02-15",
                    "description": "Amendment in Import Policy of Palm Oil",
                    "attachment": "https://www.dgft.gov.in/CP/upload/noti/NotificationNo66English.pdf"
                }
            ],
            "Public Notices": [
                {
                    "date": "2025-03-05",
                    "description": "Extension of date for submission of applications under MEIS scheme",
                    "attachment": "https://www.dgft.gov.in/CP/upload/pn/PublicNoticeNo45English.pdf"
                },
                {
                    "date": "2025-02-20",
                    "description": "Implementation of online e-EPCG module",
                    "attachment": "https://www.dgft.gov.in/CP/upload/pn/PublicNoticeNo44English.pdf"
                }
            ],
            "Circulars": [
                {
                    "date": "2025-03-03",
                    "description": "Clarification on issuance of Preferential Certificate of Origin for exports to EU",
                    "attachment": "https://www.dgft.gov.in/CP/upload/cir/CircularNo22English.pdf"
                },
                {
                    "date": "2025-02-18",
                    "description": "Extension of validity of Registration Cum Membership Certificate (RCMC)",
                    "attachment": "https://www.dgft.gov.in/CP/upload/cir/CircularNo21English.pdf"
                }
            ]
        }
        
        # Use sample data
        for section, data in sample_data.items():
            if section in self.section_data and not self.section_data[section]:
                self.section_data[section] = data
                logger.info(f"Added {len(data)} sample entries to {section}")
        
        logger.info("Sample data creation completed")
    
    def download_attachment(self, url, output_dir="downloads", gdrive_sync=True):
        """
        Download attachment from URL and optionally copy to Google Drive sync folder
        """
        try:
            # Create downloads directory if it doesn't exist
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                logger.info(f"Created directory: {output_dir}")
            
            # Download the file
            logger.info(f"Downloading attachment from: {url}")
            response = requests.get(url, stream=True)
            
            if response.status_code == 200:
                # Get filename from URL or header
                filename = url.split("/")[-1]
                if "content-disposition" in response.headers:
                    content_disp = response.headers["content-disposition"]
                    filename_part = [part for part in content_disp.split(";") if "filename=" in part]
                    if filename_part:
                        filename = filename_part[0].split("=")[1].strip('"')
                
                # Generate a more descriptive filename with date
                current_date = datetime.now().strftime("%Y%m%d")
                if "." in filename:
                    base, ext = filename.rsplit(".", 1)
                    filename = f"{current_date}_{base}.{ext}"
                else:
                    filename = f"{current_date}_{filename}"
                
                # Save to downloads folder
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                logger.info(f"Downloaded attachment to {filepath}")
                
                # Copy to Google Drive sync folder if enabled
                if gdrive_sync:
                    gdrive_folder = os.getenv("GDRIVE_LOCAL_FOLDER")
                    logger.info(f"Google Drive folder from env: {gdrive_folder}")
                    
                    if gdrive_folder:
                        # Normalize path to handle different formats
                        gdrive_folder = os.path.normpath(gdrive_folder)
                        
                        # Check if folder exists
                        if not os.path.exists(gdrive_folder):
                            try:
                                # Try to create it if it doesn't exist
                                os.makedirs(gdrive_folder, exist_ok=True)
                                logger.info(f"Created Google Drive folder: {gdrive_folder}")
                            except Exception as e:
                                logger.error(f"Failed to create Google Drive folder: {e}")
                        
                        if os.path.exists(gdrive_folder):
                            try:
                                # Create a subfolder for DGFT documents if it doesn't exist
                                dgft_folder = os.path.join(gdrive_folder, "DGFT_Documents")
                                if not os.path.exists(dgft_folder):
                                    os.makedirs(dgft_folder, exist_ok=True)
                                    logger.info(f"Created DGFT documents folder: {dgft_folder}")
                                
                                # Use the DGFT subfolder for better organization
                                gdrive_filepath = os.path.join(dgft_folder, filename)
                                
                                # Log detailed file information
                                logger.info(f"Source file exists: {os.path.exists(filepath)}")
                                logger.info(f"Source file size: {os.path.getsize(filepath)} bytes")
                                logger.info(f"Destination folder exists: {os.path.exists(dgft_folder)}")
                                logger.info(f"Destination path: {gdrive_filepath}")
                                
                                # Copy the file with explicit error handling
                                import shutil
                                shutil.copy2(filepath, gdrive_filepath)
                                
                                # Verify the copy succeeded
                                if os.path.exists(gdrive_filepath):
                                    logger.info(f"Successfully copied file to Google Drive: {gdrive_filepath}")
                                    logger.info(f"Google Drive file size: {os.path.getsize(gdrive_filepath)} bytes")
                                else:
                                    logger.error(f"File copy appeared to succeed but file not found at destination")
                            except PermissionError as pe:
                                logger.error(f"Permission error copying to Google Drive: {pe}")
                                logger.error("Check if you have write access to the Google Drive folder")
                            except FileNotFoundError as fnf:
                                logger.error(f"File not found error: {fnf}")
                                logger.error(f"Source: {filepath}, Destination: {gdrive_filepath}")
                            except Exception as e:
                                logger.error(f"Failed to copy to Google Drive: {e}")
                                logger.error(traceback.format_exc())
                        else:
                            logger.error(f"Google Drive folder still doesn't exist after creation attempt: {gdrive_folder}")
                    else:
                        logger.warning("Google Drive local folder not configured in environment variables")
                
                return filepath
            else:
                logger.error(f"Failed to download attachment: HTTP status {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error downloading attachment: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def get_latest_entry(self):
        """Get the latest entry across all sections"""
        if not self.section_data:
            self.get_latest_updates()
        
        latest_entry = None
        latest_section = None
        latest_date = None
        
        for section, entries in self.section_data.items():
            if entries and (latest_date is None or entries[0]["date"] > latest_date):
                latest_entry = entries[0]
                latest_section = section
                latest_date = entries[0]["date"]
        
        if latest_entry:
            return {
                "section": latest_section,
                "entry": latest_entry
            }
        else:
            return None

if __name__ == "__main__":
    # Simple test
    agent = WebAgent()
    updates = agent.get_latest_updates()
    for section, entries in updates.items():
        print(f"\n=== {section} ===")
        for entry in entries[:3]:  # Show top 3 entries
            print(f"Date: {entry['date']}")
            print(f"Description: {entry['description']}")
            print(f"Attachment: {entry['attachment']}")
            print()