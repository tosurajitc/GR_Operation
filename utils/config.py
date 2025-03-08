"""
Configuration utility for loading environment variables.
This utility is responsible for:
1. Loading environment variables from .env file
2. Providing configuration validation
3. Exposing configuration to other components
"""
import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Config:
    def __init__(self, env_file=".env"):
        """Initialize configuration from environment variables"""
        # Load environment variables from .env file
        if os.path.exists(env_file):
            load_dotenv(env_file)
            logger.info(f"Loaded environment variables from {env_file}")
        else:
            logger.warning(f"Environment file {env_file} not found")
        
        # DGFT Portal URLs
        self.dgft_url = os.getenv("DGFT_URL", "https://www.dgft.gov.in/CP/?opt=regulatory-updates")
        self.dgft_notifications_url = os.getenv("DGFT_NOTIFICATIONS_URL", "https://www.dgft.gov.in/CP/?opt=notification")
        self.dgft_public_notices_url = os.getenv("DGFT_PUBLIC_NOTICES_URL", "https://www.dgft.gov.in/CP/?opt=public-notice")
        self.dgft_circulars_url = os.getenv("DGFT_CIRCULARS_URL", "https://www.dgft.gov.in/CP/?opt=circular")
        
        # Google Drive integration
        self.gdrive_folder_url = os.getenv("GDRIVE_FOLDER_URL", "")
        self.gdrive_local_folder = os.getenv("GDRIVE_LOCAL_FOLDER", "")
        
        # Email Configuration
        self.email_sender = os.getenv("EMAIL_SENDER")
        self.email_password = os.getenv("EMAIL_PASSWORD")
        self.email_recipient = os.getenv("EMAIL_RECIPIENT")
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = os.getenv("SMTP_PORT", "587")
        
        # GROQ API Configuration
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_model = os.getenv("GROQ_MODEL", "llama3-70b-8192")
        
        # OCR Configuration
        self.ocr_language = os.getenv("OCR_LANGUAGE", "eng")
    
    def validate(self):
        """
        Validate configuration values
        Returns a list of validation errors or empty list if all valid
        """
        errors = []
        
        # Check required values
        if not self.dgft_url:
            errors.append("DGFT_URL is missing")
        
        # Check email configuration if any email setting is provided
        if any([self.email_sender, self.email_password, self.email_recipient, self.smtp_server]):
            # Check if all email settings are provided
            if not self.email_sender:
                errors.append("EMAIL_SENDER is missing")
            if not self.email_password:
                errors.append("EMAIL_PASSWORD is missing")
            if not self.email_recipient:
                errors.append("EMAIL_RECIPIENT is missing")
            if not self.smtp_server:
                errors.append("SMTP_SERVER is missing")
        
        # Check GROQ API configuration if API key is provided
        if self.groq_api_key and not self.groq_model:
            errors.append("GROQ_MODEL is missing")
        
        return errors
    
    def display(self, include_secrets=False):
        """
        Display configuration values
        Returns a dictionary of configuration values
        """
        config = {
            "DGFT Portal URL": self.dgft_url,
            "Email Sender": self.email_sender,
            "Email Recipient": self.email_recipient,
            "SMTP Server": self.smtp_server,
            "SMTP Port": self.smtp_port,
            "GROQ Model": self.groq_model,
            "OCR Language": self.ocr_language
        }
        
        if include_secrets:
            config["Email Password"] = self.email_password if self.email_password else "[Not Set]"
            config["GROQ API Key"] = self.groq_api_key if self.groq_api_key else "[Not Set]"
        
        return config
    
    def get_status(self):
        """
        Get configuration status
        Returns a dictionary with status information
        """
        email_configured = bool(
            self.email_sender and 
            self.email_password and 
            self.email_recipient and 
            self.smtp_server
        )
        
        groq_configured = bool(self.groq_api_key and self.groq_model)
        
        return {
            "dgft_url_configured": bool(self.dgft_url),
            "email_configured": email_configured,
            "groq_configured": groq_configured,
            "validation_errors": self.validate()
        }

if __name__ == "__main__":
    # Simple test
    config = Config()
    
    # Display configuration
    print("Configuration:")
    for key, value in config.display().items():
        print(f"- {key}: {value}")
    
    # Check validation
    errors = config.validate()
    if errors:
        print("\nValidation Errors:")
        for error in errors:
            print(f"- {error}")
    else:
        print("\nConfiguration is valid")
    
    # Get status
    status = config.get_status()
    print("\nStatus:")
    for key, value in status.items():
        if key != "validation_errors":
            print(f"- {key}: {value}")