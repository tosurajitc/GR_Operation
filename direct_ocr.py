"""
Direct OCR processor for image PDFs.
This script extracts text from PDFs that contain images instead of searchable text.
It uses Python's built-in libraries where possible to avoid dependencies on Poppler.
"""
import os
import sys
import io
import tempfile
import logging
from PIL import Image
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("Tesseract not available. Install with: pip install pytesseract")

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    print("PyMuPDF not available. Install with: pip install pymupdf")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("direct-ocr")

class DirectOCR:
    def __init__(self):
        """Initialize with Tesseract settings"""
        # Try to find Tesseract executable
        tesseract_path = None
        common_tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract"
        ]
        
        for path in common_tesseract_paths:
            if os.path.exists(path):
                tesseract_path = path
                break
        
        if tesseract_path:
            logger.info(f"Found Tesseract at: {tesseract_path}")
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        else:
            logger.warning("Tesseract executable not found in common locations")
    
    def extract_images_from_pdf(self, pdf_path):
        """Extract images directly from PDF using PyMuPDF (no poppler dependency)"""
        if not PYMUPDF_AVAILABLE:
            logger.error("PyMuPDF not installed. Cannot extract images.")
            return []
        
        try:
            logger.info(f"Extracting images from PDF: {pdf_path}")
            doc = fitz.open(pdf_path)
            
            images = []
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                logger.info(f"Processing page {page_num+1}/{len(doc)}")
                
                # Try using get_pixmap which gives us a direct image representation
                pixmap = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))  # 300 DPI
                img_data = pixmap.tobytes("png")
                pil_image = Image.open(io.BytesIO(img_data))
                
                # Add page number for tracking
                images.append({
                    "page_num": page_num + 1,
                    "image": pil_image,
                    "width": pil_image.width,
                    "height": pil_image.height
                })
                logger.info(f"Extracted image from page {page_num+1}: {pil_image.width}x{pil_image.height}")
            
            doc.close()
            logger.info(f"Successfully extracted {len(images)} images from PDF")
            return images
        except Exception as e:
            logger.error(f"Error extracting images from PDF: {e}")
            return []
    
    def ocr_image(self, image, language="eng"):
        """Process a single image with OCR"""
        if not TESSERACT_AVAILABLE:
            logger.error("Tesseract not installed. Cannot perform OCR.")
            return ""
        
        try:
            # Try different OCR configurations for best results
            configs = [
                "--oem 1 --psm 6",  # Default - Assume a single uniform block of text
                "--oem 1 --psm 3",  # Fully automatic page segmentation
                "--oem 1 --psm 1",  # Automatic page segmentation with OSD
            ]
            
            # Try each configuration
            results = []
            for config in configs:
                logger.info(f"Trying OCR with config: {config}")
                text = pytesseract.image_to_string(image, lang=language, config=config)
                results.append({
                    "config": config,
                    "text": text,
                    "length": len(text.strip())
                })
            
            # Use the result with the most text
            best_result = max(results, key=lambda x: x["length"])
            logger.info(f"Best OCR result with config {best_result['config']}: {best_result['length']} chars")
            
            return best_result["text"]
        except Exception as e:
            logger.error(f"Error performing OCR: {e}")
            return ""
    
    def process_pdf(self, pdf_path, language="eng"):
        """
        Extract text from PDF by extracting images and performing OCR
        Does not depend on Poppler
        """
        logger.info(f"Processing PDF with direct OCR: {pdf_path}")
        
        # Extract images from PDF
        images = self.extract_images_from_pdf(pdf_path)
        if not images:
            logger.error("Failed to extract images from PDF")
            return "Failed to extract images from PDF for OCR processing."
        
        # Process each image with OCR
        full_text = ""
        for img_data in images:
            page_num = img_data["page_num"]
            image = img_data["image"]
            
            logger.info(f"Performing OCR on page {page_num}")
            page_text = self.ocr_image(image, language)
            
            if page_text.strip():
                full_text += f"--- Page {page_num} ---\n\n"
                full_text += page_text + "\n\n"
                logger.info(f"Extracted {len(page_text.strip())} chars from page {page_num}")
            else:
                logger.warning(f"No text extracted from page {page_num}")
        
        if full_text.strip():
            logger.info(f"Successfully extracted {len(full_text.strip())} chars total from PDF")
            return full_text
        else:
            logger.error("No text extracted from any page")
            return "OCR processing failed to extract any text from the PDF."

if __name__ == "__main__":
    # Run as a standalone script
    if len(sys.argv) < 2:
        print("Usage: python direct_ocr.py path/to/your/pdf_file.pdf [language]")
        sys.exit(1)
    
    pdf_path = os.path.normpath(sys.argv[1])
    language = sys.argv[2] if len(sys.argv) > 2 else "eng"
    
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    processor = DirectOCR()
    text = processor.process_pdf(pdf_path, language)
    
    print("\n--- EXTRACTED TEXT ---\n")
    print(text)
    print(f"\nTotal characters: {len(text)}")
    
    # Save to file
    output_file = os.path.splitext(pdf_path)[0] + "_ocr.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)
    
    print(f"\nSaved text to: {output_file}")