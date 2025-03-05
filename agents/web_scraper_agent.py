"""
Web Scraper Agent

This agent is responsible for:
1. Accessing the DGFT website
2. Identifying and navigating to Notifications, Public Notices, and Circulars
3. Extracting tables of content with dates and attachment links
"""

import os
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from crewai import Agent

from utils.date_utils import parse_date, is_recent_date

logger = logging.getLogger(__name__)

class WebScraperAgent(Agent):
    """Agent for web scraping regulatory updates from DGFT website."""
    
    def __init__(self, url: Optional[str] = None):
        """Initialize the web scraper agent.
        
        Args:
            url: The URL to scrape. If None, will use the URL from environment variables.
        """
        # Initialize the agent first
        super().__init__(
            role="Web Scraper Specialist",
            goal="Extract latest regulatory updates from DGFT website",
            backstory="""You are an expert web scraper who specializes in navigating 
            government websites and extracting regulatory information accurately.""",
            verbose=True
        )
        
        # Set the URL as an attribute (not a field)
        self._url = url or os.getenv("DGFT_URL")
        if not self._url:
            raise ValueError("DGFT URL not provided and not found in environment variables")
    
    def setup_webdriver(self) -> webdriver.Chrome:
        """Set up and return a Chrome webdriver."""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # Try to use the Chrome driver manager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            return driver
        except Exception as e:
            logger.error(f"Failed to set up Chrome webdriver: {str(e)}")
            logger.info("Attempting to use Firefox webdriver instead")
            
            try:
                from selenium.webdriver.firefox.service import Service as FirefoxService
                from selenium.webdriver.firefox.options import Options as FirefoxOptions
                from webdriver_manager.firefox import GeckoDriverManager
                
                firefox_options = FirefoxOptions()
                firefox_options.add_argument("--headless")
                
                service = FirefoxService(GeckoDriverManager().install())
                driver = webdriver.Firefox(service=service, options=firefox_options)
                return driver
            except Exception as e2:
                logger.error(f"Failed to set up Firefox webdriver as well: {str(e2)}")
                
                # If both Chrome and Firefox fail, fall back to a requests-based approach
                logger.info("Falling back to a non-Selenium approach using requests")
                raise RuntimeError(
                    "Chrome and Firefox WebDriver setup failed. Please install Chrome or Firefox and try again. "
                    f"Original error: {str(e)}"
                )
    
    def get_latest_documents(self) -> Dict[str, List[Dict]]:
        """Scrape the website for the latest regulatory documents.
        
        Returns:
            Dictionary with document types as keys and lists of document info as values.
            Each document info includes date, title, and attachment URL.
        """
        try:
            driver = self.setup_webdriver()
            return self._get_documents_with_selenium(driver)
        except Exception as e:
            logger.error(f"Selenium approach failed: {str(e)}")
            logger.info("Falling back to requests-based approach")
            return self._get_documents_with_requests()
            
    def _get_documents_with_selenium(self, driver: webdriver.Chrome) -> Dict[str, List[Dict]]:
        """Get documents using Selenium.
        
        Args:
            driver: The webdriver instance.
            
        Returns:
            Dictionary with document types as keys and lists of document info as values.
        """
        results = {}
        
        try:
            # Navigate to the main page
            logger.info(f"Accessing URL: {self._url}")
            driver.get(self._url)
            time.sleep(3)  # Allow page to load
            
            # Identify the sections: Notifications, Public Notices, and Circulars
            sections = ["Notification", "Public Notice", "Circular"]
            
            for section in sections:
                logger.info(f"Processing section: {section}")
                try:
                    # Click on the section link
                    section_link = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, f"//a[contains(text(), '{section}')]"))
                    )
                    section_link.click()
                    time.sleep(3)  # Allow page to load
                    
                    # Extract the table content
                    table_data = self._extract_table_data(driver)
                    
                    # Store the results
                    results[section] = table_data
                    
                    # Go back to the main page for the next section
                    driver.back()
                    time.sleep(2)
                    
                except (TimeoutException, NoSuchElementException) as e:
                    logger.error(f"Error processing section {section}: {str(e)}")
            
        finally:
            driver.quit()
        
        return results
        
    def _get_documents_with_requests(self) -> Dict[str, List[Dict]]:
        """Get documents using requests and BeautifulSoup instead of Selenium.
        
        Returns:
            Dictionary with document types as keys and lists of document info as values.
        """
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin, urlparse
        
        results = {}
        
        try:
            # Use a proper URL with scheme
            url = self._url
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url.lstrip('/')
            
            base_url_parts = urlparse(url)
            base_url = f"{base_url_parts.scheme}://{base_url_parts.netloc}"
            
            logger.info(f"Accessing URL with requests: {url}")
            session = requests.Session()
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = session.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Direct URLs for each section based on the base domain
            section_urls = {
                "Notification": urljoin(base_url, "CP/?opt=notification"),
                "Public Notice": urljoin(base_url, "CP/?opt=public-notice"),
                "Circular": urljoin(base_url, "CP/?opt=circular")
            }
            
            # Process each section
            for section, section_url in section_urls.items():
                logger.info(f"Processing section with requests: {section} at URL: {section_url}")
                try:
                    # Visit the section page
                    section_response = session.get(section_url, headers=headers)
                    section_response.raise_for_status()
                    section_soup = BeautifulSoup(section_response.text, 'html.parser')
                    
                    # Extract table data
                    table_data = self._extract_table_data_with_bs4(section_soup, base_url)
                    
                    # Store the results
                    results[section] = table_data
                    
                except Exception as e:
                    logger.error(f"Error processing section {section} with requests: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error in requests-based approach: {str(e)}")
        
        return results
    
    def _extract_table_data_with_bs4(self, soup: 'BeautifulSoup', base_url: str) -> List[Dict]:
        """Extract data from the table of content using BeautifulSoup.
        
        Args:
            soup: The BeautifulSoup object.
            base_url: The base URL for constructing absolute URLs.
            
        Returns:
            List of dictionaries containing document information.
        """
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin
        
        documents = []
        
        try:
            # Find the table
            table = soup.find('table')
            
            if not table:
                logger.warning("Could not find table in the page")
                return documents
            
            # Get table headers
            headers = table.find_all('th')
            header_texts = [h.text.strip().lower() for h in headers]
            
            # Find indices for date and attachment columns
            date_idx = next((i for i, h in enumerate(header_texts) if "date" in h), None)
            attachment_idx = next((i for i, h in enumerate(header_texts) if "attachment" in h), None)
            title_idx = next((i for i, h in enumerate(header_texts) if "title" in h or "subject" in h), None)
            
            if date_idx is None or attachment_idx is None:
                logger.error("Could not find Date or Attachment columns in the table")
                return documents
            
            # Process table rows
            rows = table.find_all('tr')[1:]  # Skip header row
            
            for row in rows:
                cells = row.find_all('td')
                
                if len(cells) <= max(date_idx, attachment_idx):
                    continue
                
                # Extract date
                date_text = cells[date_idx].text.strip()
                date_obj = parse_date(date_text)
                
                # Extract title if available
                title = cells[title_idx].text.strip() if title_idx is not None and title_idx < len(cells) else "N/A"
                
                # Extract attachment link
                attachment_cell = cells[attachment_idx]
                attachment_link = attachment_cell.find('a')
                
                if attachment_link and 'href' in attachment_link.attrs:
                    attachment_url = attachment_link['href']
                    
                    # Convert relative URL to absolute if needed
                    if not attachment_url.startswith(('http://', 'https://')):
                        attachment_url = urljoin(base_url, attachment_url)
                    
                    documents.append({
                        "date": date_obj,
                        "date_text": date_text,
                        "title": title,
                        "attachment_url": attachment_url
                    })
            
            # Sort by date (newest first)
            documents.sort(key=lambda x: x["date"] if x["date"] else datetime.min, reverse=True)
            
        except Exception as e:
            logger.error(f"Error extracting table data with BeautifulSoup: {str(e)}")
        
        return documents
    
    def _extract_table_data(self, driver: webdriver.Chrome) -> List[Dict]:
        """Extract data from the table of content.
        
        Args:
            driver: The webdriver instance.
            
        Returns:
            List of dictionaries containing document information.
        """
        documents = []
        
        try:
            # Locate the table
            table = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//table"))
            )
            
            # Get table headers to identify column indices
            headers = table.find_elements(By.XPATH, ".//th")
            header_texts = [h.text.strip().lower() for h in headers]
            
            # Find indices for date and attachment columns
            date_idx = next((i for i, h in enumerate(header_texts) if "date" in h), None)
            attachment_idx = next((i for i, h in enumerate(header_texts) if "attachment" in h), None)
            title_idx = next((i for i, h in enumerate(header_texts) if "title" in h or "subject" in h), None)
            
            if date_idx is None or attachment_idx is None:
                logger.error("Could not find Date or Attachment columns in the table")
                return documents
            
            # Process table rows
            rows = table.find_elements(By.XPATH, ".//tr[position() > 1]")  # Skip header row
            
            for row in rows:
                cells = row.find_elements(By.XPATH, ".//td")
                
                if len(cells) <= max(date_idx, attachment_idx):
                    continue
                
                # Extract date
                date_text = cells[date_idx].text.strip()
                date_obj = parse_date(date_text)
                
                # Extract title if available
                title = cells[title_idx].text.strip() if title_idx is not None and title_idx < len(cells) else "N/A"
                
                # Extract attachment link
                try:
                    attachment_link = cells[attachment_idx].find_element(By.XPATH, ".//a")
                    attachment_url = attachment_link.get_attribute("href")
                    
                    documents.append({
                        "date": date_obj,
                        "date_text": date_text,
                        "title": title,
                        "attachment_url": attachment_url
                    })
                except NoSuchElementException:
                    # Skip entries without attachment links
                    pass
            
            # Sort by date (newest first)
            documents.sort(key=lambda x: x["date"], reverse=True)
            
        except Exception as e:
            logger.error(f"Error extracting table data: {str(e)}")
        
        return documents
    
    def get_latest_update_by_type(self, doc_type: str) -> Dict:
        """Get the latest update for a specific document type.
        
        Args:
            doc_type: The type of document ("Notification", "Public Notice", or "Circular")
            
        Returns:
            Dictionary with information about the latest document.
        """
        all_docs = self.get_latest_documents()
        
        if doc_type not in all_docs or not all_docs[doc_type]:
            return None
        
        # Return the most recent document
        return all_docs[doc_type][0]