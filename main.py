"""
Main Application

Entry point for the DGFT Regulatory Monitor application.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

from agents.coordinator_agent import CoordinatorAgent
from utils.logging_utils import setup_logging, get_default_log_file

# Load environment variables
load_dotenv()

# Set up logger
logger = setup_logging(log_file=get_default_log_file())

def check_dependencies():
    """Check if key dependencies are available and provide guidance if not."""
    missing_deps = []
    
    # Check for Chrome/Firefox
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--headless")
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            driver.quit()
            logger.info("Chrome browser is available")
        except Exception:
            try:
                from selenium.webdriver.firefox.options import Options
                from selenium.webdriver.firefox.service import Service
                from webdriver_manager.firefox import GeckoDriverManager
                
                options = Options()
                options.add_argument("--headless")
                driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=options)
                driver.quit()
                logger.info("Firefox browser is available")
            except Exception:
                missing_deps.append(("Chrome or Firefox browser", "For web scraping with Selenium"))
    except ImportError:
        missing_deps.append(("Selenium", "For web scraping"))
    
    # Check for Tesseract
    try:
        import pytesseract
        try:
            pytesseract.get_tesseract_version()
            logger.info("Tesseract OCR is available")
        except Exception:
            missing_deps.append(("Tesseract OCR", "For OCR processing of image-based PDFs"))
    except ImportError:
        missing_deps.append(("pytesseract", "For OCR processing"))
    
    # Check for GROQ API key
    if not os.getenv("GROQ_API_KEY"):
        missing_deps.append(("GROQ API key", "For LLM analysis (set in .env file)"))
    
    # Check for email configuration
    if any(not os.getenv(env) for env in ['SMTP_SERVER', 'SMTP_USERNAME', 'SMTP_PASSWORD']):
        missing_deps.append(("Email configuration", "For sending email notifications (set in .env file)"))
    
    # Print guidance if dependencies are missing
    if missing_deps:
        print("\n" + "="*80)
        print("MISSING DEPENDENCIES")
        print("="*80)
        print("The following dependencies are missing or not properly configured:")
        print()
        
        for dep, purpose in missing_deps:
            print(f"- {dep}: {purpose}")
        
        print("\nThe application will attempt to run with reduced functionality.")
        print("Install the missing dependencies to enable all features.")
        print("="*80 + "\n")
    
    return len(missing_deps) == 0

def get_email_recipients_from_env() -> List[str]:
    """Get email recipients from environment variables.
    
    Returns:
        List of email addresses.
    """
    recipients_str = os.getenv("DEFAULT_RECIPIENTS", "")
    if not recipients_str:
        return []
    
    # Split by comma and strip whitespace
    return [email.strip() for email in recipients_str.split(",") if email.strip()]

def run_analysis(url=None, output_file=None, email_recipients=None, enable_email=True):
    """Run the DGFT analysis.
    
    Args:
        url: Optional URL to override the default.
        output_file: Optional path to save results.
        email_recipients: Optional list of email recipients.
        enable_email: Whether to enable email functionality.
    """
    try:
        logger.info("Starting DGFT Regulatory Monitor")
        
        # Initialize the coordinator agent
        coordinator = CoordinatorAgent(url=url, enable_email=enable_email)
        
        # Run the analysis
        logger.info("Running analysis")
        results = coordinator.run(email_recipients=email_recipients)
        
        # Log summary of results
        doc_count = len(results.get("analyses", []))
        logger.info(f"Analysis completed. Processed {doc_count} documents.")
        
        # Save results if output file specified
        if output_file:
            import json
            
            # Ensure the directory exists
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert dates to strings for JSON serialization
            import datetime
            def json_serializer(obj):
                if isinstance(obj, datetime.datetime):
                    return obj.isoformat()
                if isinstance(obj, Path):
                    return str(obj)
                raise TypeError(f"Type {type(obj)} not serializable")
            
            # Save to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=json_serializer)
            
            logger.info(f"Results saved to {output_path}")
        
        return results
        
    except Exception as e:
        logger.exception(f"Error in DGFT analysis: {str(e)}")
        raise

def run_streamlit():
    """Launch the Streamlit UI."""
    try:
        logger.info("Starting Streamlit UI")
        
        # Get the path to the Streamlit app
        app_path = Path(__file__).parent / "ui" / "app.py"
        
        if not app_path.exists():
            logger.error(f"Streamlit app not found at {app_path}")
            return False
        
        # Launch Streamlit
        import subprocess
        cmd = ["streamlit", "run", str(app_path)]
        subprocess.run(cmd)
        
        return True
        
    except Exception as e:
        logger.exception(f"Error launching Streamlit UI: {str(e)}")
        return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="DGFT Regulatory Monitor")
    
    parser.add_argument("--url", type=str, help="URL to scrape (overrides .env configuration)")
    parser.add_argument("--output", type=str, help="Path to save analysis results as JSON")
    parser.add_argument("--ui", action="store_true", help="Launch the Streamlit UI")
    parser.add_argument("--headless", action="store_true", help="Run analysis without UI")
    parser.add_argument("--check", action="store_true", help="Check dependencies and exit")
    parser.add_argument("--email", action="store_true", help="Send results via email")
    parser.add_argument("--recipients", type=str, help="Comma-separated list of email recipients")
    parser.add_argument("--no-email", action="store_true", help="Disable email functionality")
    
    args = parser.parse_args()
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    if args.check:
        # Exit after dependency check if --check flag was provided
        sys.exit(0 if deps_ok else 1)
    
    # Determine email recipients
    email_recipients = None
    if args.email or args.recipients:
        if args.recipients:
            email_recipients = [email.strip() for email in args.recipients.split(",") if email.strip()]
        else:
            email_recipients = get_email_recipients_from_env()
        
        if not email_recipients:
            logger.warning("Email sending requested but no recipients specified.")
    
    # Determine whether to enable email functionality
    enable_email = not args.no_email
    
    if args.ui:
        # Launch the Streamlit UI
        run_streamlit()
    elif args.headless or args.email or args.recipients:
        # Run in headless mode
        run_analysis(
            url=args.url, 
            output_file=args.output, 
            email_recipients=email_recipients,
            enable_email=enable_email
        )
    else:
        # If no specific mode is specified, default to UI
        run_streamlit()

if __name__ == "__main__":
    main()