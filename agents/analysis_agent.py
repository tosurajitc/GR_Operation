"""
Analysis Agent

This agent is responsible for:
1. Processing extracted text using GROQ's LLM model
2. Generating insights and summaries from the regulatory documents
3. Extracting key information like effective dates, affected industries, etc.
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from crewai import Agent

logger = logging.getLogger(__name__)

class AnalysisAgent(Agent):
    """Agent for analyzing regulatory documents using LLM."""
    
    def __init__(self):
        """Initialize the analysis agent."""
        super().__init__(
            role="Regulatory Analysis Specialist",
            goal="Analyze regulatory documents and extract key insights",
            backstory="""You are an expert in Indian trade regulations and policies,
            specializing in analyzing government notifications and circulars to
            identify important changes and their implications.""",
            verbose=True
        )
        
        # Initialize the GROQ LLM
        self._api_key = os.getenv("GROQ_API_KEY")
        self._model = os.getenv("GROQ_MODEL", "llama3-70b-8192")
        
        if not self._api_key:
            raise ValueError("GROQ API key not found in environment variables")
        
        self.llm = ChatGroq(
            api_key=self._api_key,
            model_name=self._model,
            temperature=0.2,
            max_tokens=4096
        )
        
        logger.info(f"Initialized Analysis Agent with GROQ model: {self._model}")
    
    def _create_analysis_prompt(self, document_text: str, document_type: str, doc_date: datetime) -> List:
        """Create a prompt for document analysis.
        
        Args:
            document_text: The extracted text from the document.
            document_type: The type of document (Notification, Public Notice, or Circular).
            doc_date: The document date.
            
        Returns:
            A list of messages for the LLM.
        """
        date_str = doc_date.strftime("%d %B, %Y") if doc_date else "unknown date"
        
        system_prompt = f"""
        You are an expert in analyzing Indian trade regulatory documents from the Directorate General of Foreign Trade (DGFT).
        Your task is to analyze the provided {document_type} dated {date_str} and extract key information and insights.
        
        For your analysis, focus on:
        1. The main purpose of this {document_type}
        2. Key policy changes or announcements
        3. Which industries or sectors are affected
        4. Effective dates for implementation
        5. Any compliance requirements or deadlines
        6. Any relaxations or restrictions being introduced
        7. Potential impact on trade and businesses
        8. References to other regulations or notifications
        
        Structure your response in the following format:
        
        ## Summary
        [A concise 2-3 sentence summary of the key points]
        
        ## Main Purpose
        [Describe the main purpose or objective of this regulatory document]
        
        ## Key Changes
        [List bullet points of key policy changes]
        
        ## Affected Sectors
        [List the industries or sectors affected]
        
        ## Important Dates
        [List any implementation dates, deadlines, or effective dates]
        
        ## Compliance Requirements
        [Describe what businesses need to do to comply]
        
        ## Impact Assessment
        [Brief assessment of potential impacts on trade and businesses]
        
        Be precise and focus on factual information rather than speculation.
        If information for a section is not available, state "Not specified in the document."
        """
        
        human_prompt = f"""
        Please analyze the following DGFT {document_type} dated {date_str}:
        
        {document_text}
        """
        
        return [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
    
    def _create_extraction_prompt(self, document_text: str, document_type: str) -> List:
        """Create a prompt for structured data extraction.
        
        Args:
            document_text: The extracted text from the document.
            document_type: The type of document.
            
        Returns:
            A list of messages for the LLM.
        """
        system_prompt = f"""
        You are an expert in extracting structured information from Indian trade regulatory documents.
        Your task is to extract specific fields from the provided {document_type} in JSON format.
        
        Extract the following information and return it in valid JSON format:
        
        {{
            "document_number": "The document number/reference number",
            "issued_by": "The issuing authority or department",
            "effective_date": "When the regulation takes effect (format: DD-MM-YYYY)",
            "expiry_date": "End date if applicable (format: DD-MM-YYYY), or null if not specified",
            "subject": "The subject line of the document",
            "affected_hs_codes": ["list", "of", "HS", "codes", "mentioned", "if any"],
            "affected_products": ["list", "of", "products", "or", "services", "affected"],
            "key_requirements": ["list", "of", "main", "requirements", "or", "changes"],
            "penalties": "Any penalties for non-compliance, or null if not specified"
        }}
        
        Ensure all fields are present in your response. If information for a field is not available in the document, use null.
        """
        
        human_prompt = f"""
        Please extract structured information from the following DGFT {document_type}:
        
        {document_text}
        
        Return only the JSON with no additional text.
        """
        
        return [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
    
    def analyze_document(self, document_type: str, document_text: str, metadata: Dict) -> Dict:
        """Analyze a document using the GROQ LLM.
        
        Args:
            document_type: The type of document.
            document_text: The extracted text from the document.
            metadata: Additional information about the document.
            
        Returns:
            Dictionary with analysis results.
        """
        if not document_text or len(document_text.strip()) < 100:
            logger.warning(f"Document text is too short for analysis: {len(document_text) if document_text else 0} chars")
            return {
                "type": document_type,
                "analysis": "The document text was too short or empty for analysis.",
                "structured_data": {},
                "metadata": metadata
            }
        
        try:
            logger.info(f"Analyzing {document_type} document")
            
            # First, perform qualitative analysis
            analysis_messages = self._create_analysis_prompt(
                document_text, 
                document_type, 
                metadata.get("date")
            )
            
            analysis_response = self.llm.invoke(analysis_messages)
            analysis = analysis_response.content if hasattr(analysis_response, 'content') else str(analysis_response)
            
            # Then, extract structured information
            extraction_messages = self._create_extraction_prompt(document_text, document_type)
            extraction_response = self.llm.invoke(extraction_messages)
            structured_text = extraction_response.content if hasattr(extraction_response, 'content') else str(extraction_response)
            
            # Try to parse the structured data
            import json
            try:
                structured_data = json.loads(structured_text)
            except json.JSONDecodeError:
                logger.warning("Failed to parse structured data as JSON")
                structured_data = {"error": "Failed to parse as JSON", "raw": structured_text}
            
            return {
                "type": document_type,
                "analysis": analysis,
                "structured_data": structured_data,
                "metadata": metadata,
                "raw_text": document_text[:500] + "..." if len(document_text) > 500 else document_text  # Store sample of raw text
            }
            
        except Exception as e:
            logger.error(f"Error analyzing document: {str(e)}")
            return {
                "type": document_type,
                "analysis": f"Error during analysis: {str(e)}",
                "structured_data": {},
                "metadata": metadata
            }
    
    def analyze_documents(self, documents: Dict) -> List[Dict]:
        """Analyze multiple documents.
        
        Args:
            documents: Dictionary with document types as keys and document info with text as values.
            
        Returns:
            List of dictionaries with analysis results.
        """
        results = []
        
        for doc_type, doc_info in documents.items():
            # Extract text and metadata
            text = doc_info.get("text", "")
            metadata = {
                "date": doc_info.get("date"),
                "title": doc_info.get("title", "N/A"),
                "url": doc_info.get("url", ""),
                "file_path": str(doc_info.get("path", ""))
            }
            
            # Analyze the document
            analysis_result = self.analyze_document(doc_type, text, metadata)
            results.append(analysis_result)
        
        return results
    
    def get_summary_report(self, analysis_results: List[Dict]) -> str:
        """Generate a summary report of all analyzed documents.
        
        Args:
            analysis_results: List of document analysis results.
            
        Returns:
            A formatted summary report.
        """
        if not analysis_results:
            return "No documents analyzed."
        
        # Create prompt for summary report
        docs_summary = []
        for result in analysis_results:
            doc_type = result.get("type", "Unknown")
            title = result.get("metadata", {}).get("title", "Untitled")
            date = result.get("metadata", {}).get("date")
            date_str = date.strftime("%d %B, %Y") if date else "unknown date"
            
            # Extract first few lines of analysis for summary
            analysis = result.get("analysis", "No analysis available.")
            analysis_preview = "\n".join(analysis.split("\n")[:5]) + "..."
            
            docs_summary.append(f"- {doc_type} ({date_str}): {title}\n  Preview: {analysis_preview}")
        
        system_prompt = """
        You are an expert in summarizing regulatory updates. Create a concise executive summary
        of recent DGFT regulatory updates based on the analyzed documents. Focus on the most
        significant changes and their potential impacts on trade and businesses.
        
        Your summary should include:
        1. Overview of recent regulatory activity
        2. Key themes or trends across documents
        3. Most significant changes and their implications
        4. Recommended actions for businesses
        
        Keep your summary clear, concise, and business-focused.
        """
        
        human_prompt = f"""
        Please create an executive summary based on the following document analyses:
        
        {os.linesep.join(docs_summary)}
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"Error generating summary report: {str(e)}")
            return f"Error generating summary report: {str(e)}"
    
    def extract_key_changes(self, analysis_results: List[Dict]) -> Dict:
        """Extract key changes from analysis results.
        
        Args:
            analysis_results: List of document analysis results.
            
        Returns:
            Dictionary with categories of changes.
        """
        changes = {
            "policy_changes": [],
            "compliance_requirements": [],
            "important_dates": [],
            "affected_sectors": []
        }
        
        for result in analysis_results:
            structured_data = result.get("structured_data", {})
            doc_type = result.get("type", "Unknown")
            
            # Extract policy changes
            key_requirements = structured_data.get("key_requirements", [])
            if key_requirements and isinstance(key_requirements, list):
                for req in key_requirements:
                    changes["policy_changes"].append({
                        "document": doc_type,
                        "change": req
                    })
            
            # Extract compliance info
            penalties = structured_data.get("penalties")
            if penalties and penalties != "null":
                changes["compliance_requirements"].append({
                    "document": doc_type,
                    "requirement": penalties
                })
            
            # Extract dates
            effective_date = structured_data.get("effective_date")
            if effective_date and effective_date != "null":
                changes["important_dates"].append({
                    "document": doc_type,
                    "date_type": "Effective Date",
                    "date": effective_date
                })
            
            expiry_date = structured_data.get("expiry_date")
            if expiry_date and expiry_date != "null":
                changes["important_dates"].append({
                    "document": doc_type,
                    "date_type": "Expiry Date",
                    "date": expiry_date
                })
            
            # Extract affected sectors
            affected_products = structured_data.get("affected_products", [])
            if affected_products and isinstance(affected_products, list):
                for product in affected_products:
                    changes["affected_sectors"].append({
                        "document": doc_type,
                        "sector": product
                    })
        
        return changes