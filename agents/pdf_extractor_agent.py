"""
PDF Extractor Agent

This agent is responsible for:
1. Downloading PDF files from the links provided by the web scraper agent
2. Handling redirects and authentication if needed
3. Saving the PDFs to a temporary location for processing
"""

import os
import tempfile
import logging
import requests
from typing import Optional, Dict
from pathlib import Path
from crewai import Agent

logger = logging.getLogger(__name__)

class PDFExtractorAgent(Agent):
    """Agent for downloading and extracting PDF documents."""
    
    def __init__(self):
        """Initialize the PDF extractor agent."""
        super().__init__(
            role="PDF Extraction Specialist",
            goal="Download and extract PDF documents from regulatory sources",
            backstory="""You are an expert in document extraction, specializing in 
            retrieving PDFs from government websites and handling various security 
            measures and redirect patterns.""",
            verbose=True
        )
        
        # Create a temporary directory for PDFs
        self._temp_dir = Path(tempfile.mkdtemp(prefix="dgft_pdfs_"))
        logger.info(f"Created temporary directory for PDFs: {self._temp_dir}")
    
    def download_pdf(self, url: str, filename: Optional[str] = None) -> Optional[Path]:
        """Download a PDF from a URL.
        
        Args:
            url: The URL of the PDF to download.
            filename: Optional filename to use. If None, will generate one.
            
        Returns:
            Path to the downloaded PDF file or None if download failed.
        """
        if not url:
            logger.error("No URL provided for PDF download")
            return None
        
        try:
            logger.info(f"Downloading PDF from URL: {url}")
            
            # Use a session to handle redirects
            session = requests.Session()
            response = session.get(url, stream=True, timeout=30)
            
            # Check if the request was successful
            if response.status_code != 200:
                logger.error(f"Failed to download PDF: HTTP status {response.status_code}")
                return None
            
            # Generate a filename if not provided
            if not filename:
                # Try to get filename from Content-Disposition header
                if 'Content-Disposition' in response.headers:
                    content_disp = response.headers['Content-Disposition']
                    if 'filename=' in content_disp:
                        filename = content_disp.split('filename=')[1].strip('"\'')
                
                # If still no filename, use the last part of the URL
                if not filename:
                    filename = url.split('/')[-1]
                    
                    # If filename doesn't end with .pdf, add the extension
                    if not filename.lower().endswith('.pdf'):
                        filename += '.pdf'
            
            # Ensure the filename is safe
            filename = ''.join(c for c in filename if c.isalnum() or c in '._- ')
            
            # Save the PDF to the temporary directory
            file_path = self._temp_dir / filename
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"PDF downloaded successfully to: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error downloading PDF: {str(e)}")
            return None
    
    def download_latest_pdfs(self, documents_by_type: Dict) -> Dict:
        """Download the latest PDFs for each document type.
        
        Args:
            documents_by_type: Dictionary with document types as keys and 
                              lists of document info as values.
        
        Returns:
            Dictionary with document types as keys and paths to downloaded PDFs as values.
        """
        result = {}
        
        for doc_type, docs in documents_by_type.items():
            if not docs:
                continue
                
            # Get the most recent document
            latest_doc = docs[0]
            
            # Generate a meaningful filename
            date_str = latest_doc["date"].strftime("%Y%m%d")
            doc_type_clean = doc_type.replace(" ", "_")
            filename = f"{date_str}_{doc_type_clean}.pdf"
            
            # Download the PDF
            pdf_path = self.download_pdf(latest_doc["attachment_url"], filename)
            
            if pdf_path:
                result[doc_type] = {
                    "path": pdf_path,
                    "date": latest_doc["date"],
                    "title": latest_doc.get("title", "N/A"),
                    "url": latest_doc["attachment_url"]
                }
        
        return result
    
    def cleanup(self):
        """Clean up temporary files."""
        import shutil
        try:
            if self._temp_dir.exists():
                shutil.rmtree(self._temp_dir)
                logger.info(f"Cleaned up temporary directory: {self._temp_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {str(e)}")