"""
Query Agent for processing user queries.
This agent is responsible for:
1. Interpreting user queries using GROQ LLM
2. Fetching relevant information based on queries
3. Determining which notifications, public notices, or circulars to download
"""
import os
import logging
from datetime import datetime
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import groq safely
try:
    import groq
    GROQ_AVAILABLE = True
except (ImportError, AttributeError):
    GROQ_AVAILABLE = False
    logger.warning("GROQ package not available or not properly installed. Query interpretation will use rule-based fallback.")

class QueryAgent:
    def __init__(self):
        """Initialize Query Agent with LLM capabilities"""
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_model = os.getenv("GROQ_MODEL", "llama3-70b-8192")
        self.groq_client = None
        
        # Initialize GROQ client if available
        if self.groq_api_key and GROQ_AVAILABLE:
            try:
                self.groq_client = groq.Client(api_key=self.groq_api_key)
                logger.info("GROQ client initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing GROQ client: {e}")
                logger.warning("GROQ client not initialized. Query interpretation will use rule-based fallback.")
    
    def interpret_query(self, query_text):
        """
        Interpret user query to determine search parameters
        Returns a dictionary with search parameters
        """
        try:
            if not self.groq_client:
                logger.warning("GROQ client not initialized. Using rule-based query interpretation.")
                return self._rule_based_interpretation(query_text)
            
            # Create prompt for LLM
            prompt = f"""
            You are a helpful assistant that interprets user queries about regulatory documents.
            
            User query: "{query_text}"
            
            Analyze this query and extract the following information:
            1. Document type (Notifications, Public Notices, Circulars, or any/all)
            2. Date range (specific date, before/after a date, date range, or latest)
            3. Topic or keyword of interest (if any)
            
            Format your response as a JSON object with the following structure:
            {{
                "document_type": "string", (one of: "Notifications", "Public Notices", "Circulars", "any")
                "date_filter": {{
                    "type": "string", (one of: "specific", "before", "after", "range", "latest")
                    "date_start": "YYYY-MM-DD", (or null if not applicable)
                    "date_end": "YYYY-MM-DD" (or null if not applicable)
                }},
                "keywords": ["string", "string"] (list of keywords to search for, or empty list)
            }}
            
            Do not include any explanations or other text, just the JSON object.
            """
            
            # Make API call to GROQ
            response = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that interprets user queries about regulatory documents."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Lower temperature for more factual responses
            )
            
            # Parse the response
            result_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response (in case there's any wrapping text)
            json_match = re.search(r'({.*})', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(1)
            
            # Convert to Python dictionary
            import json
            try:
                result = json.loads(result_text)
                logger.info(f"Query interpretation: {result}")
                return result
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response as JSON: {result_text}")
                return self._rule_based_interpretation(query_text)
                
        except Exception as e:
            logger.error(f"Error interpreting query with GROQ: {e}")
            return self._rule_based_interpretation(query_text)
    
    def _rule_based_interpretation(self, query_text):
        """
        Fallback method to interpret queries using simple rules
        Returns a dictionary with search parameters
        """
        query = query_text.lower()
        result = {
            "document_type": "any",
            "date_filter": {
                "type": "latest",
                "date_start": None,
                "date_end": None
            },
            "keywords": []
        }
        
        # Determine document type
        if "notification" in query:
            result["document_type"] = "Notifications"
        elif "notice" in query:
            result["document_type"] = "Public Notices"
        elif "circular" in query:
            result["document_type"] = "Circulars"
        
        # Look for date patterns
        date_patterns = [
            # YYYY-MM-DD
            r'(\d{4}-\d{2}-\d{2})',
            # DD/MM/YYYY
            r'(\d{2}/\d{2}/\d{4})',
            # Month name DD, YYYY
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}'
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, query_text)
            dates.extend(matches)
        
        # Process dates
        if dates:
            if len(dates) == 1:
                # Check if "before" or "after" is in the query
                if "before" in query or "prior" in query or "earlier" in query:
                    result["date_filter"]["type"] = "before"
                    result["date_filter"]["date_end"] = self._normalize_date(dates[0])
                elif "after" in query or "since" in query or "later" in query:
                    result["date_filter"]["type"] = "after"
                    result["date_filter"]["date_start"] = self._normalize_date(dates[0])
                else:
                    result["date_filter"]["type"] = "specific"
                    result["date_filter"]["date_start"] = self._normalize_date(dates[0])
                    result["date_filter"]["date_end"] = self._normalize_date(dates[0])
            elif len(dates) >= 2:
                result["date_filter"]["type"] = "range"
                result["date_filter"]["date_start"] = self._normalize_date(dates[0])
                result["date_filter"]["date_end"] = self._normalize_date(dates[1])
        
        # Check for latest
        if "latest" in query or "recent" in query or "newest" in query:
            result["date_filter"]["type"] = "latest"
        
        # Extract potential keywords
        # Remove common words and keep potential keywords
        common_words = {"the", "and", "or", "a", "an", "in", "on", "at", "for", "with", "to", "from", 
                       "by", "about", "like", "through", "over", "between", "after", "before", 
                       "during", "above", "below", "under", "please", "find", "get", "show", "me",
                       "notification", "notifications", "notice", "notices", "circular", "circulars",
                       "document", "documents", "latest", "recent", "new", "date", "dated", "regarding"}
        
        words = re.findall(r'\b[a-zA-Z]{3,}\b', query)
        potential_keywords = [word for word in words if word.lower() not in common_words]
        result["keywords"] = potential_keywords[:5]  # Limit to top 5 keywords
        
        logger.info(f"Rule-based query interpretation: {result}")
        return result
    
    def _normalize_date(self, date_str):
        """Convert various date formats to YYYY-MM-DD"""
        try:
            # Handle YYYY-MM-DD
            if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                return date_str
            
            # Handle DD/MM/YYYY
            if re.match(r'\d{2}/\d{2}/\d{4}', date_str):
                day, month, year = date_str.split('/')
                return f"{year}-{month}-{day}"
            
            # Handle Month name DD, YYYY
            month_names = ["January", "February", "March", "April", "May", "June",
                          "July", "August", "September", "October", "November", "December"]
            
            for i, month in enumerate(month_names):
                if month in date_str:
                    pattern = fr'{month}\s+(\d{{1,2}}),\s+(\d{{4}})'
                    match = re.search(pattern, date_str)
                    if match:
                        day = match.group(1).zfill(2)
                        year = match.group(2)
                        month_num = str(i + 1).zfill(2)
                        return f"{year}-{month_num}-{day}"
            
            # Default to today if parsing fails
            return datetime.now().strftime("%Y-%m-%d")
        except Exception as e:
            logger.error(f"Error normalizing date: {e}")
            return datetime.now().strftime("%Y-%m-%d")
    
    def filter_documents(self, documents, query_params):
        """
        Filter documents based on query parameters
        Returns filtered list of documents
        """
        try:
            filtered_docs = []
            
            # Filter by document type
            if query_params["document_type"] != "any":
                documents = {
                    section: docs for section, docs in documents.items() 
                    if section == query_params["document_type"]
                }
            
            # Apply filters to each section
            for section, docs in documents.items():
                section_filtered = []
                
                for doc in docs:
                    # Skip documents without date
                    if "date" not in doc:
                        continue
                    
                    # Apply date filter
                    date_filter = query_params["date_filter"]
                    doc_date = doc["date"]
                    
                    date_match = False
                    if date_filter["type"] == "latest":
                        date_match = True  # We'll sort and take the top later
                    elif date_filter["type"] == "specific" and date_filter["date_start"]:
                        date_match = doc_date == date_filter["date_start"]
                    elif date_filter["type"] == "before" and date_filter["date_end"]:
                        date_match = doc_date <= date_filter["date_end"]
                    elif date_filter["type"] == "after" and date_filter["date_start"]:
                        date_match = doc_date >= date_filter["date_start"]
                    elif date_filter["type"] == "range" and date_filter["date_start"] and date_filter["date_end"]:
                        date_match = date_filter["date_start"] <= doc_date <= date_filter["date_end"]
                    
                    # Skip if date doesn't match
                    if not date_match:
                        continue
                    
                    # Apply keyword filter
                    keyword_match = False
                    if not query_params["keywords"]:
                        keyword_match = True  # No keywords specified
                    else:
                        description = doc.get("description", "").lower()
                        for keyword in query_params["keywords"]:
                            if keyword.lower() in description:
                                keyword_match = True
                                break
                    
                    # Add document if it matches all filters
                    if date_match and keyword_match:
                        section_filtered.append(doc)
                
                # Sort by date (newest first)
                section_filtered.sort(key=lambda x: x["date"], reverse=True)
                
                # Add section and documents to result
                if section_filtered:
                    for doc in section_filtered:
                        # Add section metadata
                        doc_with_section = doc.copy()
                        doc_with_section["section"] = section
                        filtered_docs.append(doc_with_section)
            
            # Sort all documents by date (newest first)
            filtered_docs.sort(key=lambda x: x["date"], reverse=True)
            
            # If "latest" filter and we have results, keep only the most recent
            if query_params["date_filter"]["type"] == "latest" and filtered_docs:
                if query_params["document_type"] != "any":
                    return [filtered_docs[0]]
                else:
                    # Get latest from each section
                    latest_by_section = {}
                    for doc in filtered_docs:
                        section = doc["section"]
                        if section not in latest_by_section or doc["date"] > latest_by_section[section]["date"]:
                            latest_by_section[section] = doc
                    
                    # Return all latest documents (one per section)
                    return list(latest_by_section.values())
            
            logger.info(f"Filtered {len(filtered_docs)} documents")
            return filtered_docs
            
        except Exception as e:
            logger.error(f"Error filtering documents: {e}")
            return []
    
    def process_query(self, query_text, documents):
        """
        Process a user query against the available documents
        Returns list of matching documents
        """
        try:
            # Interpret query
            query_params = self.interpret_query(query_text)
            
            # Filter documents
            filtered_docs = self.filter_documents(documents, query_params)
            
            return filtered_docs
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return []

if __name__ == "__main__":
    # Simple test
    agent = QueryAgent()
    
    # Test queries
    test_queries = [
        "Show me the latest notifications",
        "Find circulars about exports from January 2023",
        "Get me public notices regarding imports after June 15, 2023",
        "What are the most recent documents about licenses?"
    ]
    
    # Test documents
    test_documents = {
        "Notifications": [
            {"date": "2023-07-15", "description": "Notification regarding export procedures", "attachment": "url1"},
            {"date": "2023-06-10", "description": "Notification about import licenses", "attachment": "url2"}
        ],
        "Public Notices": [
            {"date": "2023-07-20", "description": "Public notice on import tariffs", "attachment": "url3"},
            {"date": "2023-05-05", "description": "Public notice regarding export quotas", "attachment": "url4"}
        ],
        "Circulars": [
            {"date": "2023-07-01", "description": "Circular on export incentives", "attachment": "url5"},
            {"date": "2023-06-25", "description": "Circular regarding import duty exemptions", "attachment": "url6"}
        ]
    }
    
    # Test each query
    for query in test_queries:
        print(f"\nQuery: {query}")
        results = agent.process_query(query, test_documents)
        print(f"Found {len(results)} matching document(s):")
        for doc in results:
            print(f"- {doc.get('section', 'Unknown')}: {doc.get('date', 'No date')} - {doc.get('description', 'No description')}")