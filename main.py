"""
Main application for DGFT Regulatory Updates Monitoring System.
This module orchestrates the various agents and components to:
1. Fetch regulatory updates from DGFT portal
2. Process and analyze documents
3. Send email notifications
4. Run the Streamlit frontend
"""
import os
import sys
import logging
import argparse
import traceback
from datetime import datetime

# Import project modules
from agents.web_agent import WebAgent
from agents.pdf_agent import PDFAgent
from agents.email_agent import EmailAgent
from agents.query_agent import QueryAgent
from utils.data_handler import DataHandler
from utils.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DGFTMonitor:
    def __init__(self):
        """Initialize DGFT Monitor with required components"""
        # Load configuration
        self.config = Config()
        logger.info("Configuration loaded")
        
        # Validate configuration
        errors = self.config.validate()
        if errors:
            logger.warning("Configuration validation errors:")
            for error in errors:
                logger.warning(f"- {error}")
        
        # Initialize data handler
        self.data_handler = DataHandler()
        logger.info("Data handler initialized")
        
        # Load previous state
        self.data_handler.load_state()
        
        # Initialize agents
        self.web_agent = WebAgent(self.config.dgft_url)
        self.pdf_agent = PDFAgent()
        self.email_agent = EmailAgent()
        self.query_agent = QueryAgent()
        logger.info("Agents initialized")
    
    def fetch_updates(self):
        """
        Fetch latest updates from DGFT portal
        Returns a dictionary with section data
        """
        try:
            logger.info("Fetching latest updates from DGFT portal")
            
            # Get updates from web agent
            updates = self.web_agent.get_latest_updates()
            
            # Store updates in data handler
            for section, docs in updates.items():
                self.data_handler.add_documents(section, docs)
            
            # Save state
            self.data_handler.save_state()
            
            logger.info("Successfully fetched updates")
            return updates
        except Exception as e:
            logger.error(f"Error fetching updates: {e}")
            logger.error(traceback.format_exc())
            return {}
    
    def process_latest_documents(self):
        """
        Process the latest document from each section
        Returns a list of processed documents
        """
        try:
            logger.info("Processing latest documents")
            
            processed_docs = []
            sections = ["Notifications", "Public Notices", "Circulars"]
            
            for section in sections:
                # Get latest document from section
                docs = self.data_handler.get_documents(section)
                if not docs:
                    logger.info(f"No documents found for {section}")
                    continue
                
                # Get latest document
                latest_doc = docs[0]  # Assuming docs are sorted by date (newest first)
                
                # Generate document ID
                doc_id = self.data_handler.generate_document_id(
                    section, latest_doc["date"], latest_doc["description"][:50]
                )
                
                # Check if already processed
                existing_doc = self.data_handler.get_processed_document(doc_id)
                if existing_doc:
                    logger.info(f"Document {doc_id} already processed")
                    processed_docs.append(existing_doc)
                    continue
                
                # Download attachment
                if not latest_doc.get("attachment"):
                    logger.warning(f"No attachment URL for {doc_id}")
                    continue
                
                pdf_path = self.web_agent.download_attachment(latest_doc["attachment"])
                if not pdf_path:
                    logger.error(f"Failed to download attachment for {doc_id}")
                    continue
                
                # Process PDF
                result = self.pdf_agent.process_pdf(pdf_path, section, latest_doc["date"])
                
                if not result["success"]:
                    logger.error(f"Failed to process PDF for {doc_id}: {result['error']}")
                    continue
                
                # Create processed document
                processed_doc = {
                    "id": doc_id,
                    "section": section,
                    "date": latest_doc["date"],
                    "description": latest_doc["description"],
                    "attachment_url": latest_doc["attachment"],
                    "pdf_path": pdf_path,
                    "text": result["text"],
                    "analysis": result["analysis"],
                    "processed_at": datetime.now().isoformat()
                }
                
                # Store processed document
                self.data_handler.add_processed_document(doc_id, processed_doc)
                
                processed_docs.append(processed_doc)
                logger.info(f"Successfully processed document {doc_id}")
            
            return processed_docs
        except Exception as e:
            logger.error(f"Error processing latest documents: {e}")
            logger.error(traceback.format_exc())
            return []
    
    def notify_latest_update(self):
        """
        Send email notification for the latest update
        Returns True if successful, False otherwise
        """
        try:
            logger.info("Notifying latest update")
            
            # Get latest document across all sections
            latest_doc = self.data_handler.get_latest_document()
            
            if not latest_doc:
                logger.warning("No documents found for notification")
                return False
            
            # Generate document ID
            doc_id = self.data_handler.generate_document_id(
                latest_doc["section"], latest_doc["date"], latest_doc["description"][:50]
            )
            
            # Get processed document
            processed_doc = self.data_handler.get_processed_document(doc_id)
            
            if not processed_doc:
                logger.warning(f"Document {doc_id} not processed yet")
                
                # Process document first
                if not latest_doc.get("attachment"):
                    logger.error(f"No attachment URL for {doc_id}")
                    return False
                
                pdf_path = self.web_agent.download_attachment(latest_doc["attachment"])
                if not pdf_path:
                    logger.error(f"Failed to download attachment for {doc_id}")
                    return False
                
                # Process PDF
                result = self.pdf_agent.process_pdf(pdf_path, latest_doc["section"], latest_doc["date"])
                
                if not result["success"]:
                    logger.error(f"Failed to process PDF for {doc_id}: {result['error']}")
                    return False
                
                # Create processed document
                processed_doc = {
                    "id": doc_id,
                    "section": latest_doc["section"],
                    "date": latest_doc["date"],
                    "description": latest_doc["description"],
                    "attachment_url": latest_doc["attachment"],
                    "pdf_path": pdf_path,
                    "text": result["text"],
                    "analysis": result["analysis"],
                    "processed_at": datetime.now().isoformat()
                }
                
                # Store processed document
                self.data_handler.add_processed_document(doc_id, processed_doc)
            
            # Send email notification
            success = self.email_agent.notify_update(
                processed_doc["section"],
                processed_doc["date"],
                processed_doc["description"],
                processed_doc["analysis"],
                processed_doc.get("pdf_path")
            )
            
            if success:
                logger.info(f"Successfully sent notification for {doc_id}")
            else:
                logger.error(f"Failed to send notification for {doc_id}")
            
            return success
        except Exception as e:
            logger.error(f"Error notifying latest update: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def process_query(self, query_text):
        """
        Process user query to find relevant documents
        Returns a list of matching documents
        """
        try:
            logger.info(f"Processing query: {query_text}")
            
            # Get all documents
            documents = self.data_handler.get_documents()
            
            # Process query
            results = self.query_agent.process_query(query_text, documents)
            
            logger.info(f"Found {len(results)} matching documents")
            return results
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            logger.error(traceback.format_exc())
            return []
    
    def run_streamlit(self):
        """Run the Streamlit frontend"""
        try:
            logger.info("Starting Streamlit frontend")
            
            # Get the absolute path to the streamlit app
            script_dir = os.path.dirname(os.path.abspath(__file__))
            streamlit_app = os.path.join(script_dir, "frontend", "streamlit_app.py")
            
            # Check if file exists
            if not os.path.exists(streamlit_app):
                logger.error(f"Streamlit app not found: {streamlit_app}")
                return False
            
            # Print the path to help with debugging
            logger.info(f"Streamlit app path: {streamlit_app}")
            
            # Run streamlit with properly quoted path
            import subprocess
            cmd = ["streamlit", "run", streamlit_app]
            logger.info(f"Running command: {' '.join(cmd)}")
            
            # Use subprocess instead of os.system for better handling
            process = subprocess.Popen(cmd)
            
            # Wait for the streamlit process
            process.wait()
            
            return True
        except Exception as e:
            logger.error(f"Error running Streamlit: {e}")
            logger.error(traceback.format_exc())
            return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="DGFT Regulatory Updates Monitoring System")
    
    # Add command line arguments
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Fetch latest updates from DGFT portal"
    )
    
    parser.add_argument(
        "--process",
        action="store_true",
        help="Process the latest document from each section"
    )
    
    parser.add_argument(
        "--notify",
        action="store_true",
        help="Send email notification for the latest update"
    )
    
    parser.add_argument(
        "--query",
        type=str,
        help="Process a user query"
    )
    
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run the Streamlit frontend"
    )
    
    parser.add_argument(
        "--sync-gdrive",
        action="store_true",
        help="Sync existing downloads to Google Drive"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Initialize DGFT Monitor
    monitor = DGFTMonitor()
    
    # Execute command
    if args.fetch:
        monitor.fetch_updates()
    
    if args.process:
        monitor.process_latest_documents()
    
    if args.notify:
        monitor.notify_latest_update()
    
    if args.query:
        results = monitor.process_query(args.query)
        print(f"\nQuery Results ({len(results)}):")
        for doc in results:
            print(f"- {doc.get('section', 'Unknown')}: {doc.get('date', 'No date')} - {doc.get('description', 'No description')}")
    
    if args.sync_gdrive:
        sync_downloads_to_gdrive()
    
    if args.run or not any([args.fetch, args.process, args.notify, args.query, args.sync_gdrive]):
        # Default to running the frontend if no arguments provided
        monitor.run_streamlit()

def sync_downloads_to_gdrive():
    """Utility function to sync existing downloads to Google Drive"""
    try:
        print("Syncing existing downloads to Google Drive...")
        
        # Get Google Drive folder from environment
        gdrive_folder = os.environ.get("GDRIVE_LOCAL_FOLDER")
        if not gdrive_folder:
            print("Error: GDRIVE_LOCAL_FOLDER not set in environment")
            return False
        
        # Normalize path
        gdrive_folder = os.path.normpath(gdrive_folder)
        
        # Create Google Drive folder if it doesn't exist
        if not os.path.exists(gdrive_folder):
            try:
                os.makedirs(gdrive_folder, exist_ok=True)
                print(f"Created Google Drive folder: {gdrive_folder}")
            except Exception as e:
                print(f"Error creating Google Drive folder: {e}")
                return False
        
        # Create DGFT subfolder
        dgft_folder = os.path.join(gdrive_folder, "DGFT_Documents")
        if not os.path.exists(dgft_folder):
            os.makedirs(dgft_folder, exist_ok=True)
            print(f"Created DGFT Documents subfolder: {dgft_folder}")
        
        # Get list of files in downloads folder
        downloads_dir = "downloads"
        if not os.path.exists(downloads_dir):
            print(f"Downloads folder not found: {downloads_dir}")
            return False
        
        files = os.listdir(downloads_dir)
        pdf_files = [f for f in files if f.lower().endswith(".pdf")]
        
        if not pdf_files:
            print("No PDF files found in downloads folder")
            return False
        
        print(f"Found {len(pdf_files)} PDF files to sync")
        
        # Copy files to Google Drive
        import shutil
        for pdf_file in pdf_files:
            src_path = os.path.join(downloads_dir, pdf_file)
            dst_path = os.path.join(dgft_folder, pdf_file)
            
            try:
                # Skip if file already exists in destination
                if os.path.exists(dst_path):
                    print(f"File already exists in Google Drive: {pdf_file}")
                    continue
                
                # Copy file
                shutil.copy2(src_path, dst_path)
                print(f"Copied {pdf_file} to Google Drive")
            except Exception as e:
                print(f"Error copying {pdf_file}: {e}")
        
        print("Google Drive sync completed")
        return True
    except Exception as e:
        print(f"Error syncing to Google Drive: {e}")
        return False

if __name__ == "__main__":
    main()