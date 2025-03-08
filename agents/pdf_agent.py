"""
PDF Agent for processing and analyzing PDF documents.
This agent is responsible for:
1. Extracting text from PDFs using multiple methods
2. Analyzing extracted content using GROQ LLM or rule-based analysis
"""
import os
import tempfile
import logging
import re
import sys
import traceback
from PyPDF2 import PdfReader
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import fitz (PyMuPDF) for better PDF text extraction
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
    logger.info("PyMuPDF (fitz) is available for enhanced PDF text extraction")
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF (fitz) is not available. Install with: pip install pymupdf")

# Set Tesseract path directly if possible
tesseract_paths = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
]

for path in tesseract_paths:
    if os.path.exists(path):
        pytesseract.pytesseract.tesseract_cmd = path
        logger.info(f"Set Tesseract path to: {path}")
        break

class PDFAgent:
    def __init__(self):
        """Initialize PDF Agent with OCR and LLM capabilities"""
        self.ocr_language = os.getenv("OCR_LANGUAGE", "eng")
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_model = os.getenv("GROQ_MODEL", "llama3-70b-8192")
        self.groq_client = None
        
        # Try to initialize GROQ client
        try:
            import groq
            if self.groq_api_key:
                self.groq_client = groq.Client(api_key=self.groq_api_key)
                logger.info("GROQ client initialized successfully")
        except Exception as e:
            logger.warning(f"GROQ client initialization failed: {e}")
    
    def extract_text_from_pdf(self, pdf_path):
        """
        Extract text from PDF file using the exact approach that worked in simple_ocr_test.py
        Returns extracted text as a string
        """
        try:
            logger.info(f"Extracting text from: {pdf_path}")
            
            # First verify the file exists
            if not os.path.exists(pdf_path):
                logger.error(f"PDF file not found: {pdf_path}")
                return f"Error: PDF file not found: {pdf_path}"
            
            file_size = os.path.getsize(pdf_path)
            logger.info(f"PDF file exists. Size: {file_size} bytes")
            
            # Verify PyMuPDF is available
            if not PYMUPDF_AVAILABLE:
                logger.error("PyMuPDF not installed. Cannot extract text.")
                return "Error: PyMuPDF not installed. Install with: pip install pymupdf"
            
            # Set Tesseract path explicitly
            for path in tesseract_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    logger.info(f"Using Tesseract at: {path}")
                    break
            else:
                logger.warning("Tesseract not found in common paths. OCR may fail.")
            
            # Open the PDF using the exact approach from simple_ocr_test.py
            doc = fitz.open(pdf_path)
            logger.info(f"PDF opened successfully with PyMuPDF. Pages: {len(doc)}")
            
            all_text = ""
            
            # Process each page using the exact same approach as the working test script
            for page_num in range(len(doc)):
                logger.info(f"Processing page {page_num+1}/{len(doc)}")
                page = doc.load_page(page_num)
                
                # First try normal text extraction
                text = page.get_text()
                if text and len(text.strip()) > 50:
                    logger.info(f"Text extraction successful: {len(text.strip())} characters")
                    all_text += f"--- Page {page_num+1} (Text) ---\n\n{text}\n\n"
                    continue
                
                logger.info(f"Text extraction yielded only {len(text.strip())} characters")
                logger.info("Trying image extraction and OCR...")
                
                # Render page to image at high resolution - EXACTLY as in the working test script
                zoom = 2.0  # Higher zoom = higher resolution
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # Convert to PIL Image - EXACTLY as in the working test script
                import io
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                logger.info(f"Extracted image: {img.width}x{img.height} pixels")
                
                # Try the exact OCR configuration that worked in the test script
                best_config = "--oem 1 --psm 3"  # This worked best in test
                logger.info(f"Using OCR config: {best_config}")
                
                try:
                    page_text = pytesseract.image_to_string(img, config=best_config)
                    text_len = len(page_text.strip())
                    logger.info(f"OCR extracted {text_len} characters")
                    
                    if text_len > 0:
                        all_text += f"--- Page {page_num+1} (OCR) ---\n\n{page_text}\n\n"
                    else:
                        logger.warning("OCR extracted no text from the page image")
                except Exception as e:
                    logger.error(f"OCR failed: {e}")
                    logger.error(traceback.format_exc())
            
            doc.close()
            
            # Check if we extracted any text
            if all_text and len(all_text.strip()) > 0:
                logger.info(f"Successfully extracted {len(all_text.strip())} characters total")
                
                # Save the extracted text to a file for debugging
                try:
                    output_file = os.path.splitext(pdf_path)[0] + "_extracted.txt"
                    with open(output_file, "w", encoding="utf-8") as f:
                        f.write(all_text)
                    logger.info(f"Saved extracted text to: {output_file}")
                except Exception as e:
                    logger.error(f"Failed to save extracted text: {e}")
                
                return all_text
            else:
                logger.error("Failed to extract any text from the PDF")
                return "No text could be extracted from this document. It may be protected or contain only images that OCR couldn't process."
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            logger.error(traceback.format_exc())
            return f"Error during text extraction: {str(e)}"
    
    def analyze_text(self, text, document_type, document_date):
        """
        Analyze extracted text to provide useful insights
        Returns a structured analysis of the document
        """
        # Handle case where text is error message or empty
        if not text or len(text.strip()) < 20 or text.startswith("Error"):
            logger.warning(f"Insufficient text for analysis: {text[:50]}...")
            return f"""
            # {document_type} Analysis
            
            **Date**: {document_date}
            
            ## Document Processing Note
            
            The system was unable to extract sufficient text for proper analysis.
            
            Please review the extracted text section or the original document for details.
            """
        
        # For OCR text that includes page markers, pre-process it
        if "--- Page" in text:
            # Clean up OCR text for better analysis
            cleaned_text = ""
            
            # Extract actual content from OCR text
            lines = text.split("\n")
            for line in lines:
                # Skip page marker lines
                if line.strip().startswith("--- Page") or not line.strip():
                    continue
                cleaned_text += line + "\n"
            
            # Use the cleaned text for analysis
            text = cleaned_text
        
        # Try GROQ if available
        if self.groq_client:
            try:
                prompt = f"""
                You are a regulatory document analysis expert. Please provide a concise analysis of this {document_type} document dated {document_date}.
                
                The document content is as follows:
                {text[:8000]}
                
                Please provide the following information:
                1. A brief summary (2-3 sentences)
                2. Key points (up to 5 bullet points)
                3. Who this regulation affects
                4. Effective date (if mentioned)
                5. Any action items or compliance requirements
                
                Format your response as a structured markdown document.
                Note that this text was extracted using OCR, so there might be some errors in the text.
                """
                
                response = self.groq_client.chat.completions.create(
                    model=self.groq_model,
                    messages=[
                        {"role": "system", "content": "You are a regulatory document analysis expert."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1024,
                    temperature=0.1,
                )
                
                return response.choices[0].message.content
            
            except Exception as e:
                logger.error(f"GROQ analysis failed: {e}")
                # Fall back to rule-based analysis
        
        # Rule-based analysis for when GROQ is unavailable or fails
        logger.info("Performing rule-based analysis")
        
        # Extract document information
        doc_info = {
            "title": "Unknown Title",
            "number": "Unknown Number",
            "subject": "Unknown Subject",
            "effective_date": "Not specified",
            "affects": []
        }
        
        # Look for document number
        number_match = re.search(r'(?:notification|notice|circular).*?(?:no\.?|number)[\s\.:]*([\w\d\/-]+)', text.lower())
        if number_match:
            doc_info["number"] = number_match.group(1).strip()
        
        # Look for subject
        subject_match = re.search(r'subject[\s:]*([^\n]+)', text, re.IGNORECASE)
        if subject_match:
            doc_info["subject"] = subject_match.group(1).strip()
        
        # Look for effective date
        date_matches = re.findall(r'(?:effective|w\.e\.f\.|with effect).*?((?:\d{1,2}[\/\.\-]\d{1,2}[\/\.\-]\d{2,4})|(?:\d{1,2}(?:st|nd|rd|th)?\s+\w+,?\s+\d{4}))', text, re.IGNORECASE)
        if date_matches:
            doc_info["effective_date"] = date_matches[0]
        
        # Look for affected parties
        for term in ["exporter", "importer", "manufacturer", "producer", "business", "industry", "trader"]:
            if term in text.lower():
                doc_info["affects"].append(term + "s")
        
        # Get most significant paragraph for summary
        paragraphs = text.split('\n\n')
        good_paragraphs = [p for p in paragraphs if len(p.strip()) > 50]
        summary = good_paragraphs[0] if good_paragraphs else text[:200]
        
        # Generate final analysis
        analysis = f"""
        # {document_type} Analysis
        
        **Document Number**: {doc_info["number"]}
        **Date**: {document_date}
        
        ## Subject
        
        {doc_info["subject"]}
        
        ## Summary
        
        {summary}
        
        ## Key Information
        
        - **Effective Date**: {doc_info["effective_date"]}
        - **Impacts**: {", ".join(doc_info["affects"]) if doc_info["affects"] else "Not specifically mentioned"}
        
        ## Note
        
        This analysis is based on OCR-extracted text and may not be complete. 
        Please refer to the original document for definitive information.
        """
        
        return analysis
    
    def process_pdf(self, pdf_path, document_type="Regulatory Document", document_date=None):
        """
        Process PDF file: extract text and analyze content
        Returns a dictionary with extracted text and analysis
        """
        try:
            # Check if PDF exists
            if not os.path.exists(pdf_path):
                logger.error(f"PDF file not found: {pdf_path}")
                return {
                    "success": True,
                    "text": "",
                    "analysis": f"Error: File not found: {pdf_path}",
                    "error": "File not found"
                }
            
            # First log file details
            file_size = os.path.getsize(pdf_path)
            logger.info(f"Processing PDF: {pdf_path} (size: {file_size} bytes)")
            
            # Run a direct extraction test to verify it's working
            test_text = self._test_extraction(pdf_path)
            if test_text and len(test_text.strip()) > 100:
                logger.info(f"Direct extraction test successful: {len(test_text.strip())} characters")
            else:
                logger.warning(f"Direct extraction test yielded limited text: {len(test_text.strip() if test_text else 0)} characters")
            
            # Extract text from PDF using our main method
            extracted_text = self.extract_text_from_pdf(pdf_path)
            
            # Compare results
            extracted_len = len(extracted_text.strip()) if extracted_text else 0
            test_len = len(test_text.strip()) if test_text else 0
            
            logger.info(f"Extraction comparison - Main: {extracted_len} chars, Test: {test_len} chars")
            
            # Use whichever extracted text is better
            if extracted_len < 100 and test_len > 100:
                logger.info("Using text from direct test extraction instead of main extraction")
                extracted_text = test_text
            
            # If text extraction returned minimal text, log warning but still continue
            if len(extracted_text.strip()) < 100:
                logger.warning(f"Minimal text extracted ({len(extracted_text.strip())} chars)")
            else:
                logger.info(f"Good text extraction: {len(extracted_text.strip())} chars")
            
            # Save the extracted text to a file
            try:
                output_file = os.path.splitext(pdf_path)[0] + "_extracted.txt"
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(extracted_text)
                logger.info(f"Saved final extracted text to: {output_file}")
            except Exception as e:
                logger.error(f"Failed to save extracted text file: {e}")
            
            # Analyze the text (our analyze_text handles minimal text gracefully)
            analysis = self.analyze_text(extracted_text, document_type, document_date)
            
            return {
                "success": True,
                "text": extracted_text,
                "analysis": analysis,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            logger.error(traceback.format_exc())
            
            return {
                "success": True,  # We still want to show something
                "text": f"Error processing PDF: {str(e)}",
                "analysis": f"Error processing document: {str(e)}",
                "error": str(e)
            }
    
    def _test_extraction(self, pdf_path):
        """Direct test of extraction using the approach that worked in simple_ocr_test.py"""
        try:
            logger.info(f"Running direct extraction test on: {pdf_path}")
            
            # Check for PyMuPDF
            if not PYMUPDF_AVAILABLE:
                logger.error("PyMuPDF not available for direct test")
                return ""
            
            # Try direct PyMuPDF extraction first
            doc = fitz.open(pdf_path)
            
            # Process only the first page to save time
            all_text = ""
            page = doc.load_page(0)
            
            # First try text extraction
            text = page.get_text()
            if text and len(text.strip()) > this:
                all_text = text
            else:
                # Direct image extraction and OCR
                zoom = 2.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # Convert to PIL Image
                import io
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                # Direct OCR with best config
                best_config = "--oem 1 --psm 3"
                page_text = pytesseract.image_to_string(img, config=best_config)
                all_text = page_text
            
            doc.close()
            logger.info(f"Direct test extracted {len(all_text.strip())} characters")
            return all_text
            
        except Exception as e:
            logger.error(f"Direct extraction test failed: {e}")
            return ""