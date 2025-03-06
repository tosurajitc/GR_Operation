"""
Streamlit Application

Frontend for the DGFT Regulatory Monitor.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
import streamlit as st
import pandas as pd
import json
from io import BytesIO
import base64

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from agents.coordinator_agent import CoordinatorAgent
from utils.date_utils import format_date
from utils.logging_utils import setup_logging

# Set up logging
logger = setup_logging(app_name="dgft_streamlit")

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Set page config
st.set_page_config(
    page_title="DGFT Regulatory Monitor",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to improve UI
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1, h2, h3 {
        margin-bottom: 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        border-radius: 4px;
        padding: 10px 16px;
    }
    .success-box {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 4px;
        border-left: 5px solid #28a745;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #d1ecf1;
        color: #0c5460;
        padding: 1rem;
        border-radius: 4px;
        border-left: 5px solid #17a2b8;
        margin-bottom: 1rem;
    }
    .warning-box {
        background-color: #fff3cd;
        color: #856404;
        padding: 1rem;
        border-radius: 4px;
        border-left: 5px solid #ffc107;
        margin-bottom: 1rem;
    }
    .stAlert {
        padding: 1rem;
        margin-bottom: 1.5rem;
    }
    .document-card {
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid #e6e6e6;
        margin-bottom: 1rem;
        background-color: #f9f9f9;
    }
    .metadata-table th {
        min-width: 150px;
        font-weight: bold;
    }
    .stMarkdown a {
        text-decoration: none;
    }
    .title-with-icon {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .icon-lg {
        font-size: 24px;
    }
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    .last-updated {
        font-size: 0.8rem;
        color: #6c757d;
    }
    /* Reduce excessive whitespace */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    div[data-testid="stVerticalBlock"] > div {
        padding-top: 0.5rem;
        padding-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Cache results to prevent unnecessary reprocessing
@st.cache_data(ttl=3600)  # Cache for 1 hour
def run_analysis(url=None, send_email=False, email_recipients=None):
    """Run the analysis and return results."""
    with st.spinner("Analyzing DGFT regulatory updates... This may take a few minutes."):
        coordinator = CoordinatorAgent(url=url, enable_email=send_email)
        results = coordinator.run(email_recipients=email_recipients)
        return results

def get_download_link(content, filename, text):
    """Generate a download link for content."""
    if isinstance(content, str):
        content = content.encode()
    b64 = base64.b64encode(content).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">{text}</a>'
    return href

def display_document_info(doc_info, doc_type):
    """Display document information."""
    date_str = format_date(doc_info.get("date")) if doc_info.get("date") else "N/A"
    
    st.markdown(f"""
    <div class="document-card">
        <h4>{doc_type} - {date_str}</h4>
        <table class="metadata-table">
            <tr>
                <th>Title</th>
                <td>{doc_info.get('description', 'N/A')}</td>
            </tr>
            <tr>
                <th>Date</th>
                <td>{date_str}</td>
            </tr>
            <tr>
                <th>Source</th>
                <td><a href="{doc_info.get('url', '#')}" target="_blank">View Original Document ↗</a></td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

def display_analysis_results(analysis_results):
    """Display the analysis results."""
    if not analysis_results:
        st.warning("No analysis results available.")
        return
    
    for idx, result in enumerate(analysis_results):
        doc_type = result.get("type", "Unknown")
        analysis = result.get("analysis", "No analysis available.")
        metadata = result.get("metadata", {})
        structured_data = result.get("structured_data", {})
        
        with st.expander(f"{doc_type} - {format_date(metadata.get('date'))}", expanded=(idx == 0)):
            # Document information in columns
            col1, col2 = st.columns([1, 2])
            with col1:
                st.subheader("Document Details")
                st.markdown(f"**Type:** {doc_type}")
                st.markdown(f"**Date:** {format_date(metadata.get('date'))}")
                st.markdown(f"**Title:** {metadata.get('description', 'N/A')}")
                if metadata.get('url'):
                    st.markdown(f"**Source:** [View Original Document]({metadata.get('url')})")
            
            # Analysis in the main section
            st.subheader("Analysis")
            st.markdown(analysis)
            
            # Structured data in expandable section
            if structured_data and structured_data != {}:
                with st.expander("Structured Information", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if structured_data.get("document_number"):
                            st.markdown(f"**Document Number:** {structured_data.get('document_number')}")
                        if structured_data.get("issued_by"):
                            st.markdown(f"**Issued By:** {structured_data.get('issued_by')}")
                        if structured_data.get("effective_date"):
                            st.markdown(f"**Effective Date:** {structured_data.get('effective_date')}")
                        if structured_data.get("expiry_date") and structured_data.get("expiry_date") != "null":
                            st.markdown(f"**Expiry Date:** {structured_data.get('expiry_date')}")
                    
                    with col2:
                        if structured_data.get("subject"):
                            st.markdown(f"**Subject:** {structured_data.get('subject')}")
                        if structured_data.get("penalties") and structured_data.get("penalties") != "null":
                            st.markdown(f"**Penalties:** {structured_data.get('penalties')}")
                    
                    # Lists in tables if they exist and are not empty
                    if structured_data.get("affected_hs_codes") and structured_data.get("affected_hs_codes") != ["null"]:
                        st.subheader("Affected HS Codes")
                        hs_df = pd.DataFrame({"HS Code": structured_data.get("affected_hs_codes")})
                        st.dataframe(hs_df, use_container_width=True, hide_index=True)
                    
                    if structured_data.get("affected_products") and structured_data.get("affected_products") != ["null"]:
                        st.subheader("Affected Products")
                        products_df = pd.DataFrame({"Product": structured_data.get("affected_products")})
                        st.dataframe(products_df, use_container_width=True, hide_index=True)
                    
                    if structured_data.get("key_requirements") and structured_data.get("key_requirements") != ["null"]:
                        st.subheader("Key Requirements")
                        req_df = pd.DataFrame({"Requirement": structured_data.get("key_requirements")})
                        st.dataframe(req_df, use_container_width=True, hide_index=True)
            
            # Download options
            col1, col2 = st.columns([1, 4])
            with col1:
                # JSON download
                json_str = json.dumps({
                    "document_type": doc_type,
                    "date": format_date(metadata.get("date")),
                    "title": metadata.get("description", "N/A"),
                    "analysis": analysis,
                    "structured_data": structured_data
                }, indent=2)
                
                st.download_button(
                    label="Download Analysis (JSON)",
                    data=json_str,
                    file_name=f"{doc_type.replace(' ', '_')}_{format_date(metadata.get('date'), '%Y%m%d')}.json",
                    mime="application/json"
                )

def display_summary(summary):
    """Display the summary report."""
    if not summary:
        st.info("No summary report available.")
        return
    
    st.markdown(f"""
    <div class="info-box">
        <h4>Executive Summary</h4>
        {summary}
    </div>
    """, unsafe_allow_html=True)

def display_key_changes(key_changes):
    """Display key changes extracted from documents."""
    if not key_changes:
        st.info("No key changes extracted.")
        return
    
    tabs = st.tabs([
        "⚖️ Policy Changes", 
        "📝 Compliance Requirements", 
        "📅 Important Dates", 
        "🏭 Affected Sectors"
    ])
    
    # Policy Changes tab
    with tabs[0]:
        if key_changes.get("policy_changes") and len(key_changes["policy_changes"]) > 0:
            changes_data = []
            for change in key_changes["policy_changes"]:
                changes_data.append({
                    "Document": change.get("document", ""),
                    "Change": change.get("change", "")
                })
            
            if changes_data:
                df = pd.DataFrame(changes_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Download option
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download as CSV",
                    data=csv,
                    file_name="policy_changes.csv",
                    mime="text/csv"
                )
        else:
            st.info("No policy changes found.")
    
    # Compliance Requirements tab
    with tabs[1]:
        if key_changes.get("compliance_requirements") and len(key_changes["compliance_requirements"]) > 0:
            req_data = []
            for req in key_changes["compliance_requirements"]:
                req_data.append({
                    "Document": req.get("document", ""),
                    "Requirement": req.get("requirement", "")
                })
            
            if req_data:
                df = pd.DataFrame(req_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Download option
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download as CSV",
                    data=csv,
                    file_name="compliance_requirements.csv",
                    mime="text/csv"
                )
        else:
            st.info("No compliance requirements found.")
    
    # Important Dates tab
    with tabs[2]:
        if key_changes.get("important_dates") and len(key_changes["important_dates"]) > 0:
            date_data = []
            for date_item in key_changes["important_dates"]:
                date_data.append({
                    "Document": date_item.get("document", ""),
                    "Type": date_item.get("date_type", ""),
                    "Date": date_item.get("date", "")
                })
            
            if date_data:
                df = pd.DataFrame(date_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Download option
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download as CSV",
                    data=csv,
                    file_name="important_dates.csv",
                    mime="text/csv"
                )
        else:
            st.info("No important dates found.")
    
    # Affected Sectors tab
    with tabs[3]:
        if key_changes.get("affected_sectors") and len(key_changes["affected_sectors"]) > 0:
            sector_data = []
            for sector in key_changes["affected_sectors"]:
                sector_data.append({
                    "Document": sector.get("document", ""),
                    "Sector": sector.get("sector", "")
                })
            
            if sector_data:
                df = pd.DataFrame(sector_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Download option
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download as CSV",
                    data=csv,
                    file_name="affected_sectors.csv",
                    mime="text/csv"
                )
        else:
            st.info("No affected sectors found.")

def main():
    """Main Streamlit application."""
    # App header
    st.markdown("""
    <div class="header-container">
        <div class="title-with-icon">
            <h1>DGFT Regulatory Updates Monitor</h1>
        </div>
    </div>        
    """, unsafe_allow_html=True)
    st.markdown(f"Last updated: {datetime.now().strftime('%d %b %Y, %H:%M')}")
    st.markdown("""
    This application monitors the latest regulatory updates from the Directorate General of Foreign Trade (DGFT) 
    including Notifications, Public Notices, and Circulars. It analyzes these documents using OCR and LLM 
    technologies to extract key insights and implications.
    """)
    
    # Sidebar for configuration and controls
    with st.sidebar:
        st.subheader("Configuration")
        
        # URL input with default value
        default_url = os.getenv("DGFT_URL", "https://www.dgft.gov.in/CP/?opt=regulatory-updates")
        url = st.text_input("DGFT Website URL", value=default_url, key="url_input")
        
        # Email configuration
        st.subheader("Email Notification")
        send_email = st.checkbox("Send Email Notification", value=False)
        
        email_recipients = None
        if send_email:
            # Get default recipients from env
            default_recipients = os.getenv("DEFAULT_RECIPIENTS", "")
            recipients_input = st.text_area(
                "Email Recipients (one per line)",
                value=default_recipients.replace(",", "\n"),
                height=100
            )
            
            if recipients_input:
                # Split by newlines and/or commas, then clean up
                email_recipients = []
                for line in recipients_input.split("\n"):
                    for email in line.split(","):
                        email = email.strip()
                        if email and "@" in email:
                            email_recipients.append(email)
            
            st.info(f"Will send email to {len(email_recipients) if email_recipients else 0} recipient(s)")
            
            # Show warning if SMTP not configured
            if not all([os.getenv(env) for env in ['SMTP_SERVER', 'SMTP_USERNAME', 'SMTP_PASSWORD']]):
                st.warning("Email configuration is incomplete. Please check your .env file.")
        
        # Run analysis button
        run_button = st.button("Run Analysis", type="primary")
        
        st.markdown("---")
        
        st.subheader("About")
        st.markdown("""
        This tool helps businesses and trade professionals stay updated with the 
        latest DGFT regulatory changes. It automatically:
        
        - Monitors DGFT regulatory updates
        - Extracts and processes PDF documents
        - Performs OCR on image-based PDFs
        - Analyzes content using LLM models
        - Provides structured insights and summaries
        """)
        
        st.markdown("---")
        st.markdown("© 2025 DGFT Regulatory Monitor")

    # Main content area
    if run_button or 'results' in st.session_state:
        if run_button:
            # Run analysis and store results in session state
            results = run_analysis(url, send_email, email_recipients)
            st.session_state.results = results
            
            # Show email notification status if applicable
            if send_email and email_recipients:
                st.success(f"Analysis completed and email notification sent to {len(email_recipients)} recipient(s)")
        else:
            # Use cached results
            results = st.session_state.results
        
        # Check for errors
        if results.get("error"):
            st.error(f"Error during analysis: {results['error']}")
            st.stop()
        
        # Main content tabs
        tabs = st.tabs(["📊 Dashboard", "📝 Document Analysis", "📋 Summary Report"])
        
        # Dashboard tab
        with tabs[0]:
            st.subheader("Overview")
            
            # Display summary statistics
            doc_count = len(results.get("analyses", []))
            doc_types = {result.get("type") for result in results.get("analyses", [])}
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Documents Analyzed", doc_count)
            with col2:
                st.metric("Document Types", len(doc_types))
            with col3:
                latest_date = max([result.get("metadata", {}).get("date") for result in results.get("analyses", []) 
                                  if result.get("metadata", {}).get("date")], default=None)
                st.metric("Latest Update", format_date(latest_date) if latest_date else "N/A")
            
            # Display key changes
            #st.subheader("Key Changes")
            #display_key_changes(results.get("key_changes", {}))  ------------------- can enable is extra details required
            
            # Display simplified document list
            #st.subheader("Latest Documents")
            # for result in results.get("analyses", []):
            #     doc_type = result.get("type", "Unknown")
            #     metadata = result.get("metadata", {})
            #     display_document_info(metadata, doc_type)
        
        # Document Analysis tab
        with tabs[1]:
            st.subheader("Detailed Document Analysis")
            display_analysis_results(results.get("analyses", []))
        
        # Summary Report tab
        with tabs[2]:
            st.subheader("Executive Summary Report")
            display_summary(results.get("summary", ""))
            
            # Export options
            st.subheader("Export Options")
            
            col1, col2 = st.columns(2)
            with col1:
                # Full report in JSON
                full_json = json.dumps({
                    "summary": results.get("summary", ""),
                    "analyses": results.get("analyses", []),
                    "key_changes": results.get("key_changes", {})
                }, indent=2, default=str)
                
                st.download_button(
                    label="Download Full Report (JSON)",
                    data=full_json,
                    file_name=f"dgft_report_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json"
                )
            
            with col2:
                # Summary report in text format
                summary_text = results.get("summary", "No summary available.")
                
                st.download_button(
                    label="Download Summary (TXT)",
                    data=summary_text,
                    file_name=f"dgft_summary_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain"
                )
    else:
        # Initial state - show instructions
        st.markdown("""
        <div class="info-box">
            <h3>Welcome to DGFT Regulatory Monitor</h3>
            <p>This tool automatically fetches, processes, and analyzes the latest regulatory updates from DGFT.</p>
            <p>Click the "Run Analysis" button in the sidebar to start monitoring DGFT updates.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Sample screenshot or explanation
        st.subheader("How it works")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            st.markdown("""
            ### 1. Data Collection
            - Scrapes latest updates from DGFT website
            - Downloads PDFs of Notifications, Circulars, and Public Notices
            - Processes image-based PDFs with OCR
            """)
        
        with col2:
            st.markdown("""
            ### 2. Analysis
            - Analyzes documents using GROQ LLM models
            - Extracts structured information
            - Identifies key policy changes
            - Determines compliance requirements
            """)
        
        with col3:
            st.markdown("""
            ### 3. Insights
            - Generates an executive summary
            - Provides detailed document analysis
            - Highlights important dates and deadlines
            - Identifies affected industry sectors
            """)

if __name__ == "__main__":
    main()