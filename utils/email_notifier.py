"""
Email Notification Module

This module is responsible for:
1. Formatting analysis results into email content
2. Attaching original PDFs and analysis results
3. Sending email notifications to specified recipients
"""

import os
import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import formatdate
from typing import Dict, List, Optional, Union
from pathlib import Path
import json
from datetime import datetime

from utils.date_utils import format_date

logger = logging.getLogger(__name__)

class EmailNotifier:
    """Email notification service for DGFT regulatory updates."""
    
    def __init__(self, smtp_server: Optional[str] = None, 
                 smtp_port: Optional[int] = None,
                 smtp_username: Optional[str] = None, 
                 smtp_password: Optional[str] = None,
                 use_tls: bool = True):
        """Initialize the email notifier.
        
        Args:
            smtp_server: SMTP server address. If None, uses SMTP_SERVER from env.
            smtp_port: SMTP server port. If None, uses SMTP_PORT from env.
            smtp_username: SMTP username. If None, uses SMTP_USERNAME from env.
            smtp_password: SMTP password. If None, uses SMTP_PASSWORD from env.
            use_tls: Whether to use TLS for the connection.
        """
        self.smtp_server = smtp_server or os.getenv("SMTP_SERVER")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = smtp_username or os.getenv("SMTP_USERNAME")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.use_tls = use_tls
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_username)
        
        # Validate required fields
        if not all([self.smtp_server, self.smtp_port, self.smtp_username, self.smtp_password]):
            logger.warning("Email configuration is incomplete. Some env variables may be missing.")
    
    def format_email_body(self, results: Dict) -> str:
        """Format the analysis results into HTML email content.
        
        Args:
            results: The analysis results dictionary.
            
        Returns:
            Formatted HTML email content.
        """
        # Start with basic HTML structure
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                h1, h2, h3 {{ color: #1a5276; }}
                .summary {{ background-color: #f8f9fa; padding: 15px; border-left: 4px solid #3498db; margin-bottom: 20px; }}
                .document {{ background-color: #f8f9fa; padding: 15px; margin-bottom: 20px; border: 1px solid #ddd; border-radius: 4px; }}
                .document h3 {{ margin-top: 0; color: #2874a6; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                .footer {{ font-size: 12px; color: #777; margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>DGFT Regulatory Updates Report</h1>
                <p>This automated report provides an analysis of the latest regulatory updates from the Directorate General of Foreign Trade (DGFT).</p>
                <p><strong>Generated on:</strong> {datetime.now().strftime('%d %B, %Y at %H:%M')}</p>
        """
        
        # Add summary section
        summary = results.get("summary", "No summary available.")
        html += f"""
                <h2>Executive Summary</h2>
                <div class="summary">
                    {summary}
                </div>
        """
        
        # Add key changes section if available
        key_changes = results.get("key_changes", {})
        if key_changes:
            html += f"""
                <h2>Key Changes</h2>
            """
            
            # Add policy changes
            if key_changes.get("policy_changes"):
                html += f"""
                    <h3>Policy Changes</h3>
                    <table>
                        <tr>
                            <th>Document</th>
                            <th>Change</th>
                        </tr>
                """
                for change in key_changes["policy_changes"]:
                    html += f"""
                        <tr>
                            <td>{change.get("document", "")}</td>
                            <td>{change.get("change", "")}</td>
                        </tr>
                    """
                html += "</table>"
            
            # Add compliance requirements
            if key_changes.get("compliance_requirements"):
                html += f"""
                    <h3>Compliance Requirements</h3>
                    <table>
                        <tr>
                            <th>Document</th>
                            <th>Requirement</th>
                        </tr>
                """
                for req in key_changes["compliance_requirements"]:
                    html += f"""
                        <tr>
                            <td>{req.get("document", "")}</td>
                            <td>{req.get("requirement", "")}</td>
                        </tr>
                    """
                html += "</table>"
            
            # Add important dates
            if key_changes.get("important_dates"):
                html += f"""
                    <h3>Important Dates</h3>
                    <table>
                        <tr>
                            <th>Document</th>
                            <th>Type</th>
                            <th>Date</th>
                        </tr>
                """
                for date_item in key_changes["important_dates"]:
                    html += f"""
                        <tr>
                            <td>{date_item.get("document", "")}</td>
                            <td>{date_item.get("date_type", "")}</td>
                            <td>{date_item.get("date", "")}</td>
                        </tr>
                    """
                html += "</table>"
            
            # Add affected sectors
            if key_changes.get("affected_sectors"):
                html += f"""
                    <h3>Affected Sectors</h3>
                    <table>
                        <tr>
                            <th>Document</th>
                            <th>Sector</th>
                        </tr>
                """
                for sector in key_changes["affected_sectors"]:
                    html += f"""
                        <tr>
                            <td>{sector.get("document", "")}</td>
                            <td>{sector.get("sector", "")}</td>
                        </tr>
                    """
                html += "</table>"
        
        # Add documents section
        analyses = results.get("analyses", [])
        if analyses:
            html += f"""
                <h2>Document Analysis</h2>
            """
            
            for result in analyses:
                doc_type = result.get("type", "Unknown")
                analysis = result.get("analysis", "No analysis available.")
                metadata = result.get("metadata", {})
                
                date_str = format_date(metadata.get("date")) if metadata.get("date") else "N/A"
                title = metadata.get("description", "N/A")
                
                html += f"""
                    <div class="document">
                        <h3>{doc_type} - {date_str}</h3>
                        <p><strong>Title:</strong> {title}</p>
                        <p><strong>Date:</strong> {date_str}</p>
                        <h4>Analysis</h4>
                        <div class="analysis">
                            {analysis.replace('\n', '<br>')}
                        </div>
                    </div>
                """
        
        # Add footer
        html += f"""
                <div class="footer">
                    <p>This is an automated report from the DGFT Regulatory Monitor. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def format_email_subject(self, results: Dict) -> str:
        """Format the email subject based on the analysis results.
        
        Args:
            results: The analysis results dictionary.
            
        Returns:
            Formatted email subject.
        """
        analyses = results.get("analyses", [])
        doc_count = len(analyses)
        
        if doc_count == 0:
            return "DGFT Regulatory Updates - No New Updates"
        
        # Get document types
        doc_types = set()
        for result in analyses:
            doc_type = result.get("type", "Unknown")
            doc_types.add(doc_type)
        
        # Create subject line
        today_str = datetime.now().strftime("%d %b %Y")
        
        if len(doc_types) == 1:
            doc_type = next(iter(doc_types))
            return f"DGFT {doc_type} Updates ({today_str}) - {doc_count} {'Document' if doc_count == 1 else 'Documents'}"
        else:
            return f"DGFT Regulatory Updates ({today_str}) - {doc_count} {'Document' if doc_count == 1 else 'Documents'} Across {len(doc_types)} Categories"
    
    def create_email_message(self, recipients: List[str], results: Dict, 
                            attach_pdfs: bool = True, attach_json: bool = True) -> MIMEMultipart:
        """Create an email message with the analysis results.
        
        Args:
            recipients: List of email addresses to send to.
            results: The analysis results dictionary.
            attach_pdfs: Whether to attach the original PDFs.
            attach_json: Whether to attach the results as JSON.
            
        Returns:
            Email message object.
        """
        # Create message container
        msg = MIMEMultipart('mixed')
        msg['From'] = self.from_email
        msg['To'] = ', '.join(recipients)
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = self.format_email_subject(results)
        
        # Create HTML email body
        html_body = self.format_email_body(results)
        msg.attach(MIMEText(html_body, 'html'))
        
        # Attach original PDFs if requested
        if attach_pdfs:
            documents = results.get("documents", {})
            for doc_type, doc_info in documents.items():
                try:
                    pdf_path = doc_info.get("path")
                    if pdf_path and Path(pdf_path).exists():
                        with open(pdf_path, 'rb') as f:
                            pdf_attachment = MIMEApplication(f.read(), _subtype='pdf')
                        
                        # Create a safe filename
                        date_str = ""
                        if doc_info.get("date"):
                            date_str = doc_info.get("date").strftime("%Y%m%d_")
                        
                        safe_filename = f"{date_str}{doc_type.replace(' ', '_')}.pdf"
                        pdf_attachment.add_header('Content-Disposition', 'attachment', filename=safe_filename)
                        msg.attach(pdf_attachment)
                except Exception as e:
                    logger.error(f"Error attaching PDF {doc_type}: {str(e)}")
        
        # Attach JSON results if requested
        if attach_json:
            try:
                # Convert dates to strings for JSON serialization
                def json_serializer(obj):
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    if isinstance(obj, Path):
                        return str(obj)
                    raise TypeError(f"Type {type(obj)} not serializable")
                
                # Format with nice indentation
                json_str = json.dumps(results, indent=2, default=json_serializer)
                
                # Create JSON attachment
                json_attachment = MIMEText(json_str, 'plain')
                json_attachment.add_header('Content-Disposition', 'attachment', 
                                          filename=f"dgft_analysis_{datetime.now().strftime('%Y%m%d')}.json")
                msg.attach(json_attachment)
            except Exception as e:
                logger.error(f"Error attaching JSON results: {str(e)}")
        
        return msg
    
    def send_email(self, recipients: Union[str, List[str]], results: Dict, 
                  attach_pdfs: bool = True, attach_json: bool = True) -> bool:
        """Send an email with the analysis results.
        
        Args:
            recipients: Email address(es) to send to.
            results: The analysis results dictionary.
            attach_pdfs: Whether to attach the original PDFs.
            attach_json: Whether to attach the results as JSON.
            
        Returns:
            True if the email was sent successfully, False otherwise.
        """
        if not all([self.smtp_server, self.smtp_port, self.smtp_username, self.smtp_password]):
            logger.error("Email configuration is incomplete. Cannot send email.")
            return False
        
        # Normalize recipients to a list
        if isinstance(recipients, str):
            recipients = [recipients]
        
        try:
            # Create the email message
            msg = self.create_email_message(recipients, results, attach_pdfs, attach_json)
            
            # Set up the SMTP connection
            context = ssl.create_default_context() if self.use_tls else None
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls(context=context)
                
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {len(recipients)} recipient(s)")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False