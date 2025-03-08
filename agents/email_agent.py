"""
Email Agent for sending notification emails.
This agent is responsible for:
1. Composing emails with regulatory update information
2. Sending emails to specified recipients
"""
import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmailAgent:
    def __init__(self):
        """Initialize Email Agent with SMTP settings from environment variables"""
        self.sender_email = os.getenv("EMAIL_SENDER")
        self.sender_password = os.getenv("EMAIL_PASSWORD")
        self.recipient_email = os.getenv("EMAIL_RECIPIENT")
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        
        # Check if email settings are configured
        self.is_configured = bool(
            self.sender_email and 
            self.sender_password and 
            self.recipient_email and 
            self.smtp_server
        )
        
        if not self.is_configured:
            logger.warning("Email settings not fully configured. Check your .env file.")
    
    def compose_email(self, subject, document_data, pdf_path=None):
        """
        Compose email with regulatory document information
        Returns a MIMEMultipart email object
        """
        try:
            message = MIMEMultipart()
            message["From"] = self.sender_email
            message["To"] = self.recipient_email
            message["Subject"] = subject
            
            # Create HTML content
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                    .container {{ padding: 20px; }}
                    h1 {{ color: #2C3E50; }}
                    h2 {{ color: #3498DB; }}
                    .details {{ margin-bottom: 20px; }}
                    .analysis {{ background-color: #F8F9FA; padding: 15px; border-left: 5px solid #3498DB; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>DGFT Regulatory Update: {document_data.get('section', '')}</h1>
                    
                    <div class="details">
                        <p><strong>Date:</strong> {document_data.get('date', '')}</p>
                        <p><strong>Description:</strong> {document_data.get('description', '')}</p>
                    </div>
                    
                    <h2>Document Analysis</h2>
                    <div class="analysis">
                        {document_data.get('analysis', '').replace('\n', '<br>')}
                    </div>
                    
                    <p>This is an automated notification from the DGFT Regulatory Updates Monitoring System.</p>
                </div>
            </body>
            </html>
            """
            
            # Attach HTML content
            message.attach(MIMEText(html_content, "html"))
            
            # Attach PDF if provided
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as file:
                    part = MIMEApplication(file.read(), Name=os.path.basename(pdf_path))
                
                # Add header
                part["Content-Disposition"] = f'attachment; filename="{os.path.basename(pdf_path)}"'
                message.attach(part)
                logger.info(f"Attached PDF: {pdf_path}")
            
            return message
        except Exception as e:
            logger.error(f"Error composing email: {e}")
            return None
    
    def send_email(self, message):
        """
        Send email using SMTP
        Returns True if successful, False otherwise
        """
        if not self.is_configured:
            logger.error("Email settings not configured. Cannot send email.")
            return False
        
        server = None
        try:
            # Connect to SMTP server
            logger.info(f"Connecting to SMTP server: {self.smtp_server}:{self.smtp_port}")
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            
            # Log in to server
            logger.info(f"Logging in as: {self.sender_email}")
            server.login(self.sender_email, self.sender_password)
            
            # Send email
            logger.info(f"Sending email to: {self.recipient_email}")
            server.send_message(message)
            
            logger.info(f"Email sent successfully to {self.recipient_email}")
            return True
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            
            # Provide specific guidance for Gmail users
            if 'gmail' in self.smtp_server.lower():
                logger.error("""
                Gmail authentication failed. If you're using Gmail, you likely need to:
                1. Create an App Password instead of using your regular password
                2. To create an App Password: 
                   a. Enable 2-Step Verification on your Google account
                   b. Go to https://myaccount.google.com/apppasswords
                   c. Create a new App Password for "Mail" and your app
                3. Use that App Password in your .env file
                """)
            return False
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
        finally:
            if server:
                server.quit()
                logger.info("SMTP server connection closed")
    
    def notify_update(self, section, date, description, analysis, pdf_path=None):
        """
        Send notification email for a regulatory update
        Returns True if successful, False otherwise
        """
        try:
            # Format subject
            subject = f"DGFT Update: {section} - {date}"
            
            # Ensure we have valid analysis text
            if not analysis or analysis.strip() == "":
                logger.warning("No analysis provided for email. Creating a basic one.")
                analysis = f"""
                # {section} Update
                
                **Date**: {date}
                **Description**: {description}
                
                *Note: Detailed document analysis is not available for this document.*
                """
            
            # Prepare document data
            document_data = {
                "section": section,
                "date": date,
                "description": description,
                "analysis": analysis
            }
            
            # Check if PDF exists
            pdf_exists = False
            if pdf_path and os.path.exists(pdf_path):
                pdf_exists = True
            else:
                logger.warning(f"PDF file not found or not provided. Email will be sent without attachment.")
            
            # Compose email
            message = self.compose_email(subject, document_data, pdf_path if pdf_exists else None)
            if not message:
                return False
            
            # Send email
            return self.send_email(message)
        except Exception as e:
            logger.error(f"Error in notify_update: {e}")
            return False

if __name__ == "__main__":
    # Simple test
    email_agent = EmailAgent()
    
    # Check if email is configured
    if email_agent.is_configured:
        # Test data
        test_data = {
            "section": "Test Section",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "description": "This is a test description for email functionality testing.",
            "analysis": "# Test Analysis\n\n- Point 1\n- Point 2\n\nThis is a test analysis."
        }
        
        # Send test email
        result = email_agent.notify_update(
            test_data["section"],
            test_data["date"],
            test_data["description"],
            test_data["analysis"]
        )
        
        print(f"Email send result: {'Success' if result else 'Failed'}")
    else:
        print("Email not configured. Check your .env file.")