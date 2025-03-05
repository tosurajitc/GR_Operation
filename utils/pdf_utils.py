"""
PDF Utilities

Helper functions for PDF handling, text extraction, and metadata extraction.
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import pytesseract
import shutil

logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path: Union[str, Path]) -> str:
    """Extract text from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file.
        
    Returns:
        Extracted text from the PDF.
    """
    try:
        logger.info(f"Extracting text from PDF: {pdf_path}")
        
        pdf_path = Path(pdf_path) if isinstance(pdf_path, str) else pdf_path
        
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
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return ""

def extract_metadata_from_pdf(pdf_path: Union[str, Path]) -> Dict:
    """Extract metadata from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file.
        
    Returns:
        Dictionary with metadata information.
    """
    try:
        logger.info(f"Extracting metadata from PDF: {pdf_path}")
        
        pdf_path = Path(pdf_path) if isinstance(pdf_path, str) else pdf_path
        
        # Open the PDF
        doc = fitz.open(pdf_path)
        
        # Extract metadata
        metadata = {
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "subject": doc.metadata.get("subject", ""),
            "keywords": doc.metadata.get("keywords", ""),
            "creator": doc.metadata.get("creator", ""),
            "producer": doc.metadata.get("producer", ""),
            "creation_date": doc.metadata.get("creationDate", ""),
            "modification_date": doc.metadata.get("modDate", ""),
            "page_count": doc.page_count
        }
        
        doc.close()
        return metadata
        
    except Exception as e:
        logger.error(f"Error extracting metadata from PDF: {str(e)}")
        return {}

def is_image_based_pdf(pdf_path: Union[str, Path]) -> bool:
    """Check if a PDF is primarily image-based.
    
    Args:
        pdf_path: Path to the PDF file.
        
    Returns:
        True if the PDF is primarily image-based, False otherwise.
    """
    try:
        logger.info(f"Checking if PDF is image-based: {pdf_path}")
        
        pdf_path = Path(pdf_path) if isinstance(pdf_path, str) else pdf_path
        
        # Open the PDF
        doc = fitz.open(pdf_path)
        
        # Check a sample of pages (up to 5)
        text_length = 0
        image_count = 0
        pages_to_check = min(5, doc.page_count)
        
        for page_num in range(pages_to_check):
            page = doc[page_num]
            
            # Check text content
            text = page.get_text()
            text_length += len(text)
            
            # Check images
            image_list = page.get_images(full=True)
            image_count += len(image_list)
        
        doc.close()
        
        # If there's very little text and there are images, consider it image-based
        avg_text_per_page = text_length / pages_to_check
        avg_images_per_page = image_count / pages_to_check
        
        is_image_based = (avg_text_per_page < 200 and avg_images_per_page > 0)
        logger.info(f"PDF image-based assessment: {is_image_based} (text/page: {avg_text_per_page:.1f}, images/page: {avg_images_per_page:.1f})")
        
        return is_image_based
        
    except Exception as e:
        logger.error(f"Error checking if PDF is image-based: {str(e)}")
        # If there's an error, assume it might be image-based to be safe
        return True

def convert_pdf_to_images(pdf_path: Union[str, Path], output_dir: Optional[Union[str, Path]] = None, dpi: int = 300) -> List[Path]:
    """Convert a PDF to a set of images.
    
    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory to save images to. If None, creates a temporary directory.
        dpi: DPI for the output images.
        
    Returns:
        List of paths to the generated images.
    """
    try:
        logger.info(f"Converting PDF to images: {pdf_path}")
        
        pdf_path = Path(pdf_path) if isinstance(pdf_path, str) else pdf_path
        
        # Create output directory if needed
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp(prefix="pdf_images_"))
        else:
            output_dir = Path(output_dir) if isinstance(output_dir, str) else output_dir
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Convert PDF to images
        images = convert_from_path(
            pdf_path,
            dpi=dpi,
            output_folder=str(output_dir),
            fmt="png",
            thread_count=os.cpu_count() or 1
        )
        
        # Get the paths to the generated images
        image_paths = sorted(output_dir.glob("*.png"))
        
        logger.info(f"Converted PDF to {len(image_paths)} images")
        return image_paths
        
    except Exception as e:
        logger.error(f"Error converting PDF to images: {str(e)}")
        return []

def perform_ocr(image_path: Union[str, Path], lang: str = "eng") -> str:
    """Perform OCR on an image.
    
    Args:
        image_path: Path to the image file.
        lang: Language code for OCR.
        
    Returns:
        Extracted text from the image.
    """
    try:
        logger.info(f"Performing OCR on image: {image_path}")
        
        image_path = Path(image_path) if isinstance(image_path, str) else image_path
        
        # Perform OCR
        text = pytesseract.image_to_string(str(image_path), lang=lang)
        
        return text
        
    except Exception as e:
        logger.error(f"Error performing OCR: {str(e)}")
        return ""

def extract_text_with_ocr(pdf_path: Union[str, Path], lang: str = "eng") -> str:
    """Extract text from a PDF using OCR.
    
    Args:
        pdf_path: Path to the PDF file.
        lang: Language code for OCR.
        
    Returns:
        Extracted text from the PDF.
    """
    try:
        logger.info(f"Extracting text with OCR from PDF: {pdf_path}")
        
        # Create a temporary directory for the images
        temp_dir = Path(tempfile.mkdtemp(prefix="pdf_ocr_"))
        
        try:
            # Convert PDF to images
            image_paths = convert_pdf_to_images(pdf_path, output_dir=temp_dir)
            
            if not image_paths:
                logger.warning(f"No images generated from PDF: {pdf_path}")
                return ""
            
            # Perform OCR on each image and combine the results
            text = ""
            for img_path in image_paths:
                page_text = perform_ocr(img_path, lang=lang)
                text += page_text
                text += "\n\n"  # Add spacing between pages
            
            return text
            
        finally:
            # Clean up temporary directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
        
    except Exception as e:
        logger.error(f"Error extracting text with OCR: {str(e)}")
        return ""

def extract_tables_from_pdf(pdf_path: Union[str, Path]) -> List[Dict]:
    """Extract tables from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file.
        
    Returns:
        List of dictionaries representing tables.
    """
    try:
        logger.info(f"Extracting tables from PDF: {pdf_path}")
        
        pdf_path = Path(pdf_path) if isinstance(pdf_path, str) else pdf_path
        
        # Open the PDF
        doc = fitz.open(pdf_path)
        
        tables = []
        
        # Extract tables from each page
        for page_num in range(doc.page_count):
            page = doc[page_num]
            
            # Use PyMuPDF's table detection capabilities
            # This is a simplified approach; more sophisticated table extraction
            # would require additional libraries or custom implementation
            blocks = page.get_text("blocks")
            
            # Group blocks by their vertical position to identify potential rows
            rows = {}
            for block in blocks:
                y0 = round(block[1])  # Top y-coordinate
                
                if y0 not in rows:
                    rows[y0] = []
                
                rows[y0].append({
                    "text": block[4],
                    "bbox": (block[0], block[1], block[2], block[3])
                })
            
            # If we have at least 3 rows, consider it a potential table
            if len(rows) >= 3:
                sorted_rows = [rows[y] for y in sorted(rows.keys())]
                
                # Extract table data
                table_data = []
                for row in sorted_rows:
                    # Sort cells by x-coordinate (left to right)
                    sorted_cells = sorted(row, key=lambda cell: cell["bbox"][0])
                    table_data.append([cell["text"] for cell in sorted_cells])
                
                tables.append({
                    "page": page_num + 1,
                    "data": table_data
                })
        
        doc.close()
        return tables
        
    except Exception as e:
        logger.error(f"Error extracting tables from PDF: {str(e)}")
        return []

def merge_pdfs(pdf_paths: List[Union[str, Path]], output_path: Union[str, Path]) -> bool:
    """Merge multiple PDFs into a single PDF.
    
    Args:
        pdf_paths: List of paths to the PDF files to merge.
        output_path: Path to save the merged PDF.
        
    Returns:
        True if successful, False otherwise.
    """
    try:
        logger.info(f"Merging {len(pdf_paths)} PDFs")
        
        output_path = Path(output_path) if isinstance(output_path, str) else output_path
        
        # Create a new PDF document
        merged_doc = fitz.open()
        
        # Add pages from each PDF
        for pdf_path in pdf_paths:
            pdf_path = Path(pdf_path) if isinstance(pdf_path, str) else pdf_path
            
            if not pdf_path.exists():
                logger.warning(f"PDF file does not exist: {pdf_path}")
                continue
            
            doc = fitz.open(pdf_path)
            merged_doc.insert_pdf(doc)
            doc.close()
        
        # Save the merged PDF
        merged_doc.save(output_path)
        merged_doc.close()
        
        logger.info(f"Merged PDF saved to: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error merging PDFs: {str(e)}")
        return False

def get_pdf_info(pdf_path: Union[str, Path]) -> Dict:
    """Get detailed information about a PDF file.
    
    Args:
        pdf_path: Path to the PDF file.
        
    Returns:
        Dictionary with PDF information.
    """
    try:
        logger.info(f"Getting PDF info: {pdf_path}")
        
        pdf_path = Path(pdf_path) if isinstance(pdf_path, str) else pdf_path
        
        if not pdf_path.exists():
            logger.warning(f"PDF file does not exist: {pdf_path}")
            return {}
        
        # Get file info
        file_info = {
            "file_name": pdf_path.name,
            "file_size": pdf_path.stat().st_size,
            "file_size_mb": round(pdf_path.stat().st_size / (1024 * 1024), 2),
            "modified_time": pdf_path.stat().st_mtime
        }
        
        # Open the PDF
        doc = fitz.open(pdf_path)
        
        # Get PDF info
        metadata = extract_metadata_from_pdf(pdf_path)
        is_image_based = is_image_based_pdf(pdf_path)
        
        # Analyze structure
        structure_info = {
            "page_count": doc.page_count,
            "is_encrypted": doc.is_encrypted,
            "is_image_based": is_image_based,
            "permissions": doc.permissions
        }
        
        # Get attachments (if any)
        attachments = []
        for name in doc.embfile_names():
            attachments.append({
                "name": name,
                "size": len(doc.extract_embfile(name)[1])
            })
        
        doc.close()
        
        return {
            "file_info": file_info,
            "metadata": metadata,
            "structure": structure_info,
            "attachments": attachments
        }
        
    except Exception as e:
        logger.error(f"Error getting PDF info: {str(e)}")
        return {}

def extract_images_from_pdf(pdf_path: Union[str, Path], output_dir: Optional[Union[str, Path]] = None) -> List[Path]:
    """Extract embedded images from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory to save images to. If None, creates a temporary directory.
        
    Returns:
        List of paths to the extracted images.
    """
    try:
        logger.info(f"Extracting images from PDF: {pdf_path}")
        
        pdf_path = Path(pdf_path) if isinstance(pdf_path, str) else pdf_path
        
        # Create output directory if needed
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp(prefix="pdf_extracted_images_"))
        else:
            output_dir = Path(output_dir) if isinstance(output_dir, str) else output_dir
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Open the PDF
        doc = fitz.open(pdf_path)
        
        extracted_images = []
        image_count = 0
        
        # Extract images from each page
        for page_num in range(doc.page_count):
            page = doc[page_num]
            
            # Get list of image references
            image_list = page.get_images(full=True)
            
            for img_index, img_info in enumerate(image_list):
                xref = img_info[0]  # Image reference number
                
                # Extract image
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Save image
                image_count += 1
                image_path = output_dir / f"page{page_num+1}_img{img_index+1}.{image_ext}"
                
                with open(image_path, "wb") as img_file:
                    img_file.write(image_bytes)
                
                extracted_images.append(image_path)
        
        doc.close()
        
        logger.info(f"Extracted {len(extracted_images)} images from PDF")
        return extracted_images
        
    except Exception as e:
        logger.error(f"Error extracting images from PDF: {str(e)}")
        return []