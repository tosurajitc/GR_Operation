"""
Test script for PDF text extraction.
This script tests multiple PDF text extraction methods on a single file.

Usage:
    python test_pdf_extraction.py path/to/your/pdf_file.pdf
"""
import sys
import os
import traceback
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("pdf-test")

def test_extraction(pdf_path):
    """Test multiple PDF text extraction methods on a single file"""
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        return
    
    print(f"\nTesting PDF text extraction on: {pdf_path}")
    print(f"File size: {os.path.getsize(pdf_path)} bytes\n")
    
    results = []
    
    # Method 1: Try PyMuPDF (fitz)
    print("--- Testing PyMuPDF (fitz) ---")
    try:
        import fitz
        print("PyMuPDF version:", fitz.version)
        
        # Open the PDF with PyMuPDF
        doc = fitz.open(pdf_path)
        print(f"Document has {len(doc)} pages")
        
        # Extract text from each page
        pymupdf_text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            print(f"  Page {page_num+1}: {len(page_text)} characters")
            pymupdf_text += page_text + "\n\n"
        
        doc.close()
        
        print(f"Total text extracted: {len(pymupdf_text)} characters")
        print(f"Preview: {pymupdf_text[:200]}...")
        
        results.append({
            "method": "PyMuPDF",
            "success": True,
            "text_length": len(pymupdf_text),
            "text_preview": pymupdf_text[:200]
        })
    except ImportError:
        print("PyMuPDF not installed. Install with: pip install pymupdf")
        results.append({
            "method": "PyMuPDF",
            "success": False,
            "error": "Not installed"
        })
    except Exception as e:
        print(f"Error with PyMuPDF: {e}")
        traceback.print_exc()
        results.append({
            "method": "PyMuPDF",
            "success": False,
            "error": str(e)
        })
    
    print("\n--- Testing PyPDF2 ---")
    try:
        from PyPDF2 import PdfReader
        
        # Open the PDF with PyPDF2
        with open(pdf_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            print(f"Document has {len(pdf_reader.pages)} pages")
            
            # Extract text from each page
            pypdf_text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                print(f"  Page {page_num+1}: {len(page_text) if page_text else 0} characters")
                if page_text:
                    pypdf_text += page_text + "\n\n"
            
            print(f"Total text extracted: {len(pypdf_text)} characters")
            print(f"Preview: {pypdf_text[:200]}...")
            
            results.append({
                "method": "PyPDF2",
                "success": True,
                "text_length": len(pypdf_text),
                "text_preview": pypdf_text[:200]
            })
    except ImportError:
        print("PyPDF2 not installed. Install with: pip install PyPDF2")
        results.append({
            "method": "PyPDF2",
            "success": False,
            "error": "Not installed"
        })
    except Exception as e:
        print(f"Error with PyPDF2: {e}")
        traceback.print_exc()
        results.append({
            "method": "PyPDF2",
            "success": False,
            "error": str(e)
        })
    
    print("\n--- Testing Tesseract OCR ---")
    try:
        import pytesseract
        from pdf2image import convert_from_path
        import tempfile
        
        # Check if Tesseract is installed
        try:
            version = pytesseract.get_tesseract_version()
            print(f"Tesseract version: {version}")
        except:
            print("Could not determine Tesseract version")
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Created temp directory: {temp_dir}")
            
            # Convert PDF to images
            try:
                images = convert_from_path(
                    pdf_path, 
                    dpi=300,
                    output_folder=temp_dir
                )
                print(f"Converted PDF to {len(images)} images")
                
                # Process each image with OCR
                ocr_text = ""
                for i, image in enumerate(images):
                    print(f"  Processing image {i+1}...")
                    page_text = pytesseract.image_to_string(image)
                    print(f"  Image {i+1}: {len(page_text)} characters")
                    ocr_text += page_text + "\n\n"
                
                print(f"Total text extracted: {len(ocr_text)} characters")
                print(f"Preview: {ocr_text[:200]}...")
                
                results.append({
                    "method": "Tesseract OCR",
                    "success": True,
                    "text_length": len(ocr_text),
                    "text_preview": ocr_text[:200]
                })
            except Exception as e:
                print(f"Error converting PDF to images: {e}")
                traceback.print_exc()
                results.append({
                    "method": "Tesseract OCR",
                    "success": False,
                    "error": str(e)
                })
    except ImportError as e:
        print(f"Required OCR library not installed: {e}")
        print("Install with: pip install pytesseract pdf2image pillow")
        results.append({
            "method": "Tesseract OCR",
            "success": False,
            "error": "Not installed"
        })
    except Exception as e:
        print(f"Error with Tesseract OCR: {e}")
        traceback.print_exc()
        results.append({
            "method": "Tesseract OCR",
            "success": False,
            "error": str(e)
        })
    
    # Print summary
    print("\n=== SUMMARY ===")
    for result in results:
        status = f"SUCCESS - {result['text_length']} chars" if result.get("success") else f"FAILED - {result.get('error')}"
        print(f"{result['method']}: {status}")
    
    # Find best method
    successful_results = [r for r in results if r.get("success") and r.get("text_length", 0) > 0]
    if successful_results:
        best_result = max(successful_results, key=lambda x: x.get("text_length", 0))
        print(f"\nBest extraction method: {best_result['method']} with {best_result['text_length']} characters")
    else:
        print("\nAll extraction methods failed")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_pdf_extraction.py path/to/your/pdf_file.pdf")
    else:
        test_extraction(sys.argv[1])