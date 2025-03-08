"""
Simple OCR test script that works without dependencies on the main application.
Just uses PyMuPDF and Tesseract directly.
"""
import os
import sys
import io
from PIL import Image
import pytesseract

try:
    import fitz  # PyMuPDF
    print("PyMuPDF imported successfully")
except ImportError:
    print("ERROR: PyMuPDF not installed. Run: pip install pymupdf")
    sys.exit(1)

# Check for Tesseract installation
try:
    pytesseract_ver = pytesseract.get_tesseract_version()
    print(f"Tesseract version: {pytesseract_ver}")
except:
    print("WARNING: Could not get Tesseract version")
    # Look for Tesseract in common locations
    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            print(f"Found Tesseract at: {path}")
            pytesseract.pytesseract.tesseract_cmd = path
            break
    else:
        print("ERROR: Tesseract not found. Install from: https://github.com/UB-Mannheim/tesseract/wiki")
        sys.exit(1)

def process_pdf(pdf_path):
    """Process PDF with direct image extraction and OCR"""
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        return
    
    print(f"Processing PDF: {pdf_path}")
    print(f"File size: {os.path.getsize(pdf_path)} bytes")
    
    # Open the PDF
    try:
        doc = fitz.open(pdf_path)
        print(f"PDF opened successfully. Pages: {len(doc)}")
        
        all_text = ""
        
        # Process each page
        for page_num in range(len(doc)):
            print(f"\nProcessing page {page_num+1}/{len(doc)}")
            page = doc.load_page(page_num)
            
            # First try normal text extraction
            text = page.get_text()
            if text and len(text.strip()) > 50:
                print(f"  Text extraction successful: {len(text.strip())} characters")
                all_text += f"--- Page {page_num+1} (Text) ---\n\n{text}\n\n"
                continue
            
            print(f"  Text extraction yielded only {len(text.strip())} characters")
            print("  Trying image extraction and OCR...")
            
            # Render page to image at high resolution
            zoom = 2.0  # Higher zoom = higher resolution
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            print(f"  Extracted image: {img.width}x{img.height} pixels")
            
            # Try multiple OCR configurations
            configs = [
                "--oem 1 --psm 6",  # Assume a single uniform block of text
                "--oem 1 --psm 3",  # Auto page segmentation, no OSD
                "--oem 1 --psm 1",  # Auto page segmentation with OSD
            ]
            
            best_text = ""
            best_config = ""
            best_len = 0
            
            for config in configs:
                print(f"  Trying OCR with config: {config}")
                try:
                    page_text = pytesseract.image_to_string(img, config=config)
                    text_len = len(page_text.strip())
                    print(f"    Extracted {text_len} characters")
                    
                    if text_len > best_len:
                        best_text = page_text
                        best_config = config
                        best_len = text_len
                except Exception as e:
                    print(f"    OCR failed with config {config}: {e}")
            
            if best_text:
                print(f"  Best OCR result: {best_len} chars with config {best_config}")
                all_text += f"--- Page {page_num+1} (OCR) ---\n\n{best_text}\n\n"
            else:
                print("  OCR failed on this page")
        
        doc.close()
        
        if all_text:
            print(f"\nSuccessfully extracted {len(all_text)} characters total")
            
            # Save to file
            output_file = os.path.splitext(pdf_path)[0] + "_ocr_text.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(all_text)
            print(f"Saved extracted text to: {output_file}")
            
            # Print preview
            preview_len = min(500, len(all_text))
            print(f"\nText preview (first {preview_len} chars):")
            print("-" * 50)
            print(all_text[:preview_len])
            print("-" * 50)
            
            return all_text
        else:
            print("\nNo text could be extracted from this PDF")
            return None
    
    except Exception as e:
        print(f"Error processing PDF: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python simple_ocr_test.py path/to/your/pdf_file.pdf")
        sys.exit(1)
    
    pdf_path = os.path.normpath(sys.argv[1])
    process_pdf(pdf_path)