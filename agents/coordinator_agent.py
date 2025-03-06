"""
Coordinator Agent

This agent is responsible for:
1. Orchestrating the workflow between all other agents
2. Managing the execution sequence and data flow
3. Aggregating and preparing results for the UI
"""

import os
import logging
from typing import Dict, List, Optional, Union
from datetime import datetime
from pathlib import Path
from crewai import Agent, Crew, Task, Process
from .web_scraper_agent import WebScraperAgent
from .pdf_extractor_agent import PDFExtractorAgent
from .ocr_agent import OCRAgent
from .analysis_agent import AnalysisAgent

from utils.email_notifier import EmailNotifier

logger = logging.getLogger(__name__)

class CoordinatorAgent:
    """Coordinator agent to orchestrate the workflow between agents."""
    
    def __init__(self, url: Optional[str] = None, enable_email: bool = True):
        """Initialize the coordinator agent.
        
        Args:
            url: Optional URL to scrape. If None, uses the URL from environment variables.
            enable_email: Whether to enable email notifications.
        """
        self.url = url
        self.enable_email = enable_email
        self.results = {
            "documents": {},
            "analyses": [],
            "summary": "",
            "key_changes": {}
        }
        
        # Initialize agents
        self.web_scraper = WebScraperAgent(url=url)
        self.pdf_extractor = PDFExtractorAgent()
        self.ocr_agent = OCRAgent()
        self.analysis_agent = AnalysisAgent()
        
        # Initialize email notifier if enabled
        self.email_notifier = EmailNotifier() if enable_email else None
        
        logger.info("Coordinator agent initialized")
    
    def run(self, email_recipients: Optional[Union[str, List[str]]] = None, max_stored_pdfs=5) -> Dict:
        """Execute the full workflow.
        
        Args:
            email_recipients: Optional email recipient(s) to send results to.
            max_stored_pdfs: Maximum number of PDFs to keep in storage.
        Returns:
            Dictionary with the results.
        """
        try:
            # Step 1: Get latest regulatory documents
            documents_by_type = self.web_scraper.get_latest_documents()
            logger.info(f"Found {sum(len(docs) for docs in documents_by_type.values())} documents")
            
            # Step 2: Download the PDFs
            downloaded_pdfs = self.pdf_extractor.download_latest_pdfs(documents_by_type)
            logger.info(f"Downloaded {len(downloaded_pdfs)} PDFs")
            
            self.results["documents"] = downloaded_pdfs
            
            
            # If no documents found, return early
            if not downloaded_pdfs:
                logger.warning("No documents found or downloaded")
                return self.results
            
            # Step 3: Process PDFs with OCR if needed
            processed_documents = self.ocr_agent.process_documents(downloaded_pdfs)
            logger.info(f"Processed {len(processed_documents)} documents with OCR")
            
            # Step 4: Analyze documents using LLM
            analysis_results = self.analysis_agent.analyze_documents(processed_documents)
            logger.info(f"Analyzed {len(analysis_results)} documents")
            
            self.results["analyses"] = analysis_results
            
            # Step 5: Generate summary report
            summary = self.analysis_agent.get_summary_report(analysis_results)
            self.results["summary"] = summary
            
            # Step 6: Extract key changes
            key_changes = self.analysis_agent.extract_key_changes(analysis_results)
            self.results["key_changes"] = key_changes
            
            # Step 7: Send email notification if recipients are provided
            if email_recipients and self.enable_email and self.email_notifier:
                self.send_email_notification(email_recipients)

            self._limit_stored_pdfs(max_stored_pdfs)    
            
            return self.results
            
        except Exception as e:
            logger.error(f"Error in coordinator workflow: {str(e)}")
            self.results["error"] = str(e)
            return self.results
        finally:
            # Clean up temporary files
            self._cleanup()
    
    def run_with_crew(self) -> Dict:
        """Execute the workflow using CrewAI for more autonomous operation.
        
        Returns:
            Dictionary with the results.
        """
        try:
            # Define tasks for the crew
            scraping_task = Task(
                description="""
                Access the DGFT regulatory updates website and identify the latest 
                Notifications, Public Notices, and Circulars. Extract the tables of
                content with Description, dates and attachment links for each document type.
                """,
                agent=self.web_scraper,
                expected_output="Dictionary of document types with their content tables"
            )
            
            extraction_task = Task(
                description="""
                Download the PDF files from the links provided by the web scraper.
                Handle any authentication or redirects required. Save the PDFs
                to a temporary location for further processing.
                """,
                agent=self.pdf_extractor,
                expected_output="Dictionary of document types with paths to downloaded PDFs",
                context=[scraping_task]
            )
            
            ocr_task = Task(
                description="""
                Process the downloaded PDF files to extract text content.
                If a PDF is image-based, use OCR to extract the text.
                If a PDF is already text-based, extract the text directly.
                """,
                agent=self.ocr_agent,
                expected_output="Dictionary of document types with extracted text",
                context=[extraction_task]
            )
            
            analysis_task = Task(
                description="""
                Analyze the extracted text from each document using GROQ's LLM model.
                Generate insights and summaries about the regulatory changes.
                Extract key information like effective dates, affected industries, etc.
                """,
                agent=self.analysis_agent,
                expected_output="List of dictionaries with analysis results",
                context=[ocr_task]
            )
            
            # Create the crew
            crew = Crew(
                agents=[
                    self.web_scraper,
                    self.pdf_extractor,
                    self.ocr_agent,
                    self.analysis_agent
                ],
                tasks=[
                    scraping_task,
                    extraction_task,
                    ocr_task,
                    analysis_task
                ],
                verbose=True,
                process=Process.sequential
            )
            
            # Run the crew
            result = crew.kickoff()
            
            # Process the result
            self.results["analyses"] = result
            
            # Generate summary and extract key changes
            self.results["summary"] = self.analysis_agent.get_summary_report(result)
            self.results["key_changes"] = self.analysis_agent.extract_key_changes(result)
            
            return self.results
            
        except Exception as e:
            logger.error(f"Error in coordinator crew workflow: {str(e)}")
            self.results["error"] = str(e)
            return self.results
        finally:
            # Clean up temporary files
            self._cleanup()
    
    def send_email_notification(self, recipients: Union[str, List[str]]) -> bool:
        """Send email notification with analysis results.
        
        Args:
            recipients: Email address(es) to send to.
            
        Returns:
            True if the email was sent successfully, False otherwise.
        """
        if not self.email_notifier:
            logger.warning("Email notifier not initialized. Cannot send email.")
            return False
        
        if not self.results.get("analyses"):
            logger.warning("No analysis results to send via email.")
            return False
        
        try:
            logger.info(f"Sending email notification to {recipients}")
            success = self.email_notifier.send_email(
                recipients=recipients,
                results=self.results,
                attach_pdfs=True,
                attach_json=True
            )
            
            if success:
                logger.info("Email notification sent successfully")
            else:
                logger.warning("Failed to send email notification")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            return False
    
    def _cleanup(self):
        """Clean up temporary files."""
        try:
            # Cleanup agent-specific temp dirs
            self.pdf_extractor.cleanup()
            self.ocr_agent.cleanup()
            
            # Also clean any global temp files
            for path in Path(".").rglob("*.tmp"):
                path.unlink()
            for path in Path(".").rglob("*.log"):
                if path.stat().st_size > 10_000_000:  # 10MB
                    path.unlink()
                    
            logger.info("Cleaned up temporary files")
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {str(e)}")

        
        
    def _limit_stored_pdfs(self, max_count):
        """Limit the number of stored PDFs to save space."""
        storage_dir = Path("stored_pdfs")
        if not storage_dir.exists():
            return
            
        # Get all PDFs sorted by modification time (newest first)
        pdfs = sorted(storage_dir.glob("*.pdf"), 
                    key=lambda p: p.stat().st_mtime, reverse=True)
        
        # Remove older PDFs beyond the max count
        for pdf in pdfs[max_count:]:
            pdf.unlink()
            logger.info(f"Removed old PDF: {pdf}")        