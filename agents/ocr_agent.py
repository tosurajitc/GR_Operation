"""
OCR Agent

This agent is responsible for:
1. Converting PDF files to images
2. Performing OCR on the images to extract text
3. Handling image-based PDFs specifically
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import Optional, Dict, List
import pytesseract
from pdf2image import convert_from_path
import fitz  # PyMuPDF
from crewai import Agent

logger = logging.getLogger(__name__)

class OCRAgent(Agent):
    """Agent for OCR processing of PDF documents."""
    
    def __init__(self):
        """Initialize the OCR agent."""
        super().__init__(
            role="OCR Specialist",
            goal="Extract text from image-based PDFs using OCR technology",
            backstory="""You are an expert in optical character recognition,
            specializing in extracting text from scanned government documents
            and handling complex layouts and formats.""",
            verbose=True
        )
        
        # Set the OCR engine from environment variable
        self._ocr_engine = os.getenv("OCR_ENGINE", "tesseract")
        
        # If using tesseract, ensure it's installed and configured
        if self._ocr_engine == "tesseract":
            # This can be expanded to include path setup for different platforms
            # For now, we assume tesseract is properly installed
            self._tesseract_cmd = os.getenv("TESSERACT_CMD", "tesseract")
            try:
                pytesseract.get_tesseract_version()
                logger.info("Tesseract is properly configured")
            except Exception as e:
                logger.warning(f"Tesseract configuration issue: {str(e)}")
        
        # Create temporary directory for image files
        self._temp_dir = Path(tempfile.mkdtemp(prefix="dgft_ocr_"))
        logger.info(f"Created temporary directory for OCR processing: {self._temp_dir}")
    
    def _convert_pdf_to_images(self, pdf_path: Path) -> List[Path]:
        """Convert PDF pages to images.
        
        Args:
            pdf_path: Path to the PDF file.
            
        Returns:
            List of paths to the generated image files.
        """
        try:
            logger.info(f"Converting PDF to images: {pdf_path}")
            
            # Create a subdirectory for this PDF's images
            pdf_name = pdf_path.stem
            img_dir = self._temp_dir / pdf_name
            img_dir.mkdir(exist_ok=True)
            
            # Convert PDF to images
            images = convert_from_path(
                pdf_path,
                dpi=300,  # Higher DPI for better OCR accuracy
                thread_count=os.cpu_count() or 1
            )
            
            image_paths = []
            for i, image in enumerate(images):
                img_path = img_dir / f"page_{i+1}.png"
                image.save(img_path, "PNG")
                image_paths.append(img_path)
            
            logger.info(f"Converted PDF to {len(image_paths)} images")
            return image_paths
            
        except Exception as e:
            logger.error(f"Error converting PDF to images: {str(e)}")
            return []
    
    def _perform_ocr(self, image_path: Path) -> str:
        """Perform OCR on an image.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            Extracted text from the image.
        """
        try:
            logger.info(f"Performing OCR on image: {image_path}")
            
            # If using tesseract for OCR
            text = pytesseract.image_to_string(str(image_path), lang='eng')
            
            return text
            
        except Exception as e:
            logger.error(f"Error performing OCR: {str(e)}")
            return ""
    
    def _check_if_pdf_needs_ocr(self, pdf_path: Path) -> bool:
        """Check if a PDF needs OCR (is image-based).
        
        Args:
            pdf_path: Path to the PDF file.
            
        Returns:
            True if the PDF needs OCR, False otherwise.
        """
        try:
            logger.info(f"Checking if PDF needs OCR: {pdf_path}")
            
            # Open the PDF
            doc = fitz.open(pdf_path)
            
            # Check the first few pages (up to 5)
            for page_num in range(min(5, doc.page_count)):
                page = doc[page_num]
                text = page.get_text()
                
                # If the page has a reasonable amount of text, assume it's not image-based
                if len(text) > 100:
                    doc.close()
                    logger.info(f"PDF appears to be text-based, OCR not needed")
                    return False
            
            doc.close()
            logger.info(f"PDF appears to be image-based, OCR needed")
            return True
            
        except Exception as e:
            logger.error(f"Error checking if PDF needs OCR: {str(e)}")
            # If there's an error, assume OCR is needed to be safe
            return True
    
    def _extract_text_directly(self, pdf_path: Path) -> str:
        """Extract text directly from a text-based PDF.
        
        Args:
            pdf_path: Path to the PDF file.
            
        Returns:
            Extracted text from the PDF.
        """
        try:
            logger.info(f"Extracting text directly from PDF: {pdf_path}")
            
            # Open the PDF
            doc = fitz.open(pdf_path)
            
            # Extract text from all pages
            text = ""
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text += page.get_text()
                text += "\n\n"  # Add spacing between pages
            
            doc.close()
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text directly from PDF: {str(e)}")
            return ""
    
    def process_pdf(self, pdf_path: Path) -> str:
        """Process a PDF file to extract text.
        
        Args:
            pdf_path: Path to the PDF file.
            
        Returns:
            Extracted text from the PDF.
        """
        if not pdf_path.exists():
            logger.error(f"PDF file does not exist: {pdf_path}")
            return ""
        
        # First, check if the PDF needs OCR
        needs_ocr = self._check_if_pdf_needs_ocr(pdf_path)
        
        if not needs_ocr:
            # If the PDF is text-based, extract text directly
            return self._extract_text_directly(pdf_path)
        
        # If we get here, the PDF is image-based and needs OCR
        tesseract_available = self._check_tesseract_available()
        
        if not tesseract_available:
            logger.warning("Tesseract OCR is not available. Falling back to direct extraction.")
            # Even if it's not ideal, try direct extraction as a fallback
            return self._extract_text_directly(pdf_path)
        
        # If the PDF is image-based and Tesseract is available, convert to images and perform OCR
        image_paths = self._convert_pdf_to_images(pdf_path)
        
        # Perform OCR on each image and combine the results
        full_text = ""
        for img_path in image_paths:
            text = self._perform_ocr(img_path)
            full_text += text
            full_text += "\n\n"  # Add spacing between pages
        
        return full_text
        
    def _check_tesseract_available(self) -> bool:
        """Check if Tesseract OCR is available.
        
        Returns:
            True if Tesseract is available, False otherwise.
        """
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False
    
    def process_documents(self, documents: Dict) -> Dict:
        """Process multiple documents.
        
        Args:
            documents: Dictionary with document types as keys and document info as values.
            
        Returns:
            Dictionary with document types as keys and document info with extracted text as values.
        """
        result = {}
        
        for doc_type, doc_info in documents.items():
            logger.info(f"Processing document: {doc_type}")
            
            # Get the PDF path
            pdf_path = doc_info["path"]
            
            # Process the PDF
            extracted_text = self.process_pdf(pdf_path)
            
            # Update the document info with extracted text
            doc_info["text"] = extracted_text
            result[doc_type] = doc_info
        
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