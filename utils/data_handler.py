"""
Data Handler for processing and storing regulatory data.
This utility is responsible for:
1. Managing document data from different sources
2. Saving and loading data to/from disk
3. Providing a clean interface for the main application
"""
import os
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataHandler:
    def __init__(self, data_dir="data"):
        """Initialize Data Handler with data directory"""
        self.data_dir = data_dir
        self.documents = {
            "Notifications": [],
            "Public Notices": [],
            "Circulars": []
        }
        self.processed_documents = {}
        
        # Create data directory if it doesn't exist
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            logger.info(f"Created data directory: {data_dir}")
    
    def add_documents(self, section, documents):
        """
        Add documents to the specified section
        Returns number of documents added
        """
        if section not in self.documents:
            logger.warning(f"Unknown section: {section}")
            return 0
        
        # Add documents
        self.documents[section] = documents
        logger.info(f"Added {len(documents)} documents to {section}")
        
        return len(documents)
    
    def get_documents(self, section=None):
        """
        Get documents from the specified section or all sections
        Returns a dictionary of documents by section or list of documents
        """
        if section:
            if section not in self.documents:
                logger.warning(f"Unknown section: {section}")
                return []
            return self.documents[section]
        else:
            return self.documents
    
    def get_latest_document(self, section=None):
        """
        Get the latest document from the specified section or all sections
        Returns a single document or None if no documents are available
        """
        latest_doc = None
        latest_date = None
        
        if section:
            # Get latest document from specified section
            if section not in self.documents:
                logger.warning(f"Unknown section: {section}")
                return None
            
            docs = self.documents[section]
            for doc in docs:
                if "date" in doc and (latest_date is None or doc["date"] > latest_date):
                    latest_doc = doc
                    latest_date = doc["date"]
                    latest_doc["section"] = section
        else:
            # Get latest document from all sections
            for section_name, docs in self.documents.items():
                for doc in docs:
                    if "date" in doc and (latest_date is None or doc["date"] > latest_date):
                        latest_doc = doc
                        latest_date = doc["date"]
                        latest_doc["section"] = section_name
        
        return latest_doc
    
    def add_processed_document(self, document_id, document_data):
        """
        Add a processed document (with OCR and analysis)
        Returns True if successful, False otherwise
        """
        try:
            self.processed_documents[document_id] = document_data
            
            # Save to file
            self._save_processed_document(document_id, document_data)
            
            logger.info(f"Added processed document: {document_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding processed document: {e}")
            return False
    
    def get_processed_document(self, document_id):
        """
        Get a processed document by ID
        Returns document data or None if not found
        """
        # Check if document is in memory
        if document_id in self.processed_documents:
            return self.processed_documents[document_id]
        
        # Try to load from disk
        doc_path = os.path.join(self.data_dir, f"{document_id}.json")
        if os.path.exists(doc_path):
            try:
                with open(doc_path, "r", encoding="utf-8") as f:
                    document_data = json.load(f)
                
                # Cache in memory
                self.processed_documents[document_id] = document_data
                
                return document_data
            except Exception as e:
                logger.error(f"Error loading processed document: {e}")
        
        return None
    
    def _save_processed_document(self, document_id, document_data):
        """
        Save processed document to disk
        Returns True if successful, False otherwise
        """
        try:
            doc_path = os.path.join(self.data_dir, f"{document_id}.json")
            
            with open(doc_path, "w", encoding="utf-8") as f:
                json.dump(document_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved processed document to: {doc_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving processed document: {e}")
            return False
    
    def save_state(self):
        """
        Save current document state to disk
        Returns True if successful, False otherwise
        """
        try:
            state_path = os.path.join(self.data_dir, "state.json")
            
            # Create a serializable state (without OCR text to reduce size)
            state = {}
            for section, docs in self.documents.items():
                state[section] = []
                for doc in docs:
                    # Create a copy without OCR text
                    doc_copy = doc.copy()
                    if "text" in doc_copy:
                        del doc_copy["text"]
                    state[section].append(doc_copy)
            
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved state to: {state_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving state: {e}")
            return False
    
    def load_state(self):
        """
        Load document state from disk
        Returns True if successful, False otherwise
        """
        try:
            state_path = os.path.join(self.data_dir, "state.json")
            
            if not os.path.exists(state_path):
                logger.info("No state file found. Starting with empty state.")
                return False
            
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            
            # Update documents
            for section, docs in state.items():
                if section in self.documents:
                    self.documents[section] = docs
            
            logger.info(f"Loaded state from: {state_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading state: {e}")
            return False
    
    def generate_document_id(self, section, date, description=None):
        """Generate a unique document ID based on section, date, and description"""
        # Clean up date
        date_str = date.replace("-", "")
        
        # Derive slug from description
        slug = ""
        if description:
            # Take first few words
            words = description.split()[:3]
            slug = "_".join(words).lower()
            
            # Remove non-alphanumeric characters
            slug = "".join(c for c in slug if c.isalnum() or c == "_")
        
        # Generate ID
        section_prefix = "".join(word[0] for word in section.split())
        document_id = f"{section_prefix}_{date_str}"
        if slug:
            document_id += f"_{slug}"
        
        return document_id

if __name__ == "__main__":
    # Simple test
    handler = DataHandler()
    
    # Add test documents
    test_notifications = [
        {"date": "2023-07-15", "description": "Test notification 1", "attachment": "url1"},
        {"date": "2023-06-10", "description": "Test notification 2", "attachment": "url2"}
    ]
    
    handler.add_documents("Notifications", test_notifications)
    
    # Get latest document
    latest = handler.get_latest_document()
    print("Latest document:")
    print(latest)
    
    # Save and load state
    handler.save_state()
    
    # Create a new handler and load state
    new_handler = DataHandler()
    new_handler.load_state()
    
    # Verify loaded state
    loaded_docs = new_handler.get_documents("Notifications")
    print(f"\nLoaded {len(loaded_docs)} notifications:")
    for doc in loaded_docs:
        print(f"- {doc['date']}: {doc['description']}")