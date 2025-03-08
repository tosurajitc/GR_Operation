"""
Streamlit frontend for DGFT Regulatory Updates Monitoring System.
This application provides a user interface for:
1. Viewing regulatory updates (Notifications, Public Notices, Circulars)
2. Searching and filtering updates
3. Viewing document details including OCR analysis
4. Sending email notifications
"""
import os
import sys
import time
import datetime
import streamlit as st
import pandas as pd
import json

# Add parent directory to path to import project modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import project modules
from agents.web_agent import WebAgent
from agents.pdf_agent import PDFAgent
from agents.email_agent import EmailAgent
from agents.query_agent import QueryAgent
from utils.data_handler import DataHandler
from utils.config import Config

# Set page configuration
st.set_page_config(
    page_title="DGFT Regulatory Updates Monitor",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load configuration
@st.cache_resource
def load_config():
    return Config()

config = load_config()

# Initialize data handler
@st.cache_resource
def load_data_handler():
    return DataHandler()

data_handler = load_data_handler()

# Initialize agents
@st.cache_resource
def load_agents():
    return {
        "web_agent": WebAgent(),
        "pdf_agent": PDFAgent(),
        "email_agent": EmailAgent(),
        "query_agent": QueryAgent()
    }

agents = load_agents()

# Helper functions
def fetch_updates(url=None):
    """Fetch updates from DGFT portal"""
    with st.spinner("Fetching updates from DGFT portal..."):
        web_agent = agents["web_agent"]
        if url:
            web_agent.base_url = url
        
        updates = web_agent.get_latest_updates()
        
        # Store updates in data handler
        for section, docs in updates.items():
            data_handler.add_documents(section, docs)
        
        # Save state
        data_handler.save_state()
        
        return updates

def format_date(date_str):
    """Format date string as DD MMM YYYY"""
    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%d %b %Y")
    except:
        return date_str

def process_document(section, document, download=True):
    """Process document: download PDF and extract text"""
    document_id = data_handler.generate_document_id(
        section, document["date"], document["description"][:50]
    )
    
    # Check if document is already processed
    processed_doc = data_handler.get_processed_document(document_id)
    if processed_doc:
        st.success("Document already processed")
        return processed_doc
    
    # Get PDF agent
    pdf_agent = agents["pdf_agent"]
    
    # Check if URL exists
    if not document.get("attachment"):
        st.error("No attachment URL found")
        return None
    
    # Download attachment
    pdf_path = None
    if download:
        with st.spinner("Downloading document..."):
            web_agent = agents["web_agent"]
            pdf_path = web_agent.download_attachment(document["attachment"])
            
            if not pdf_path:
                st.error("Failed to download document")
                return None
    else:
        st.info("Skipping download")
        return None
    
    # Process PDF
    with st.spinner("Processing document with OCR..."):
        result = pdf_agent.process_pdf(pdf_path, section, document["date"])
        
        if not result["success"]:
            st.error(f"Failed to process document: {result['error']}")
            return None
    
    # Create processed document
    processed_doc = {
        "id": document_id,
        "section": section,
        "date": document["date"],
        "description": document["description"],
        "attachment_url": document["attachment"],
        "pdf_path": pdf_path,
        "text": result["text"],
        "analysis": result["analysis"],
        "processed_at": datetime.datetime.now().isoformat()
    }
    
    # Store processed document
    data_handler.add_processed_document(document_id, processed_doc)
    
    return processed_doc

def send_email_notification(document_data):
    """Send email notification with document details"""
    email_agent = agents["email_agent"]
    
    with st.spinner("Sending email notification..."):
        success = email_agent.notify_update(
            document_data["section"],
            format_date(document_data["date"]),
            document_data["description"],
            document_data["analysis"],
            document_data.get("pdf_path")
        )
        
        if success:
            st.success("Email notification sent")
        else:
            st.error("Failed to send email notification")
        
        return success

def process_query(query_text):
    """Process user query to find relevant documents"""
    query_agent = agents["query_agent"]
    
    with st.spinner("Processing query..."):
        # Get all documents
        documents = data_handler.get_documents()
        
        # Process query
        results = query_agent.process_query(query_text, documents)
        
        return results

# Main application
def main():
    # Add custom CSS
    st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            color: #1E88E5;
            margin-bottom: 1rem;
        }
        .section-header {
            font-size: 1.8rem;
            color: #0D47A1;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }
        .subsection-header {
            font-size: 1.4rem;
            color: #1565C0;
            margin-top: 1.5rem;
            margin-bottom: 0.5rem;
        }
        .date-text {
            color: #546E7A;
            font-weight: bold;
        }
        .desc-text {
            color: #424242;
        }
        .alert-box {
            padding: 0.5rem;
            border-radius: 0.3rem;
            margin-bottom: 1rem;
        }
        .info-box {
            background-color: #E3F2FD;
            border-left: 5px solid #2196F3;
        }
        .warning-box {
            background-color: #FFF8E1;
            border-left: 5px solid #FFC107;
        }
        .success-box {
            background-color: #E8F5E9;
            border-left: 5px solid #4CAF50;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Page header
    st.markdown('<h1 class="main-header">DGFT Regulatory Updates Monitor</h1>', unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.markdown('<h2 class="subsection-header">Configuration</h2>', unsafe_allow_html=True)
    
    # URL input
    dgft_url = st.sidebar.text_input("DGFT Portal URL", value=config.dgft_url)
    
    # Google Drive sync
    gdrive_folder = config.gdrive_local_folder
    if gdrive_folder:
        st.sidebar.markdown("### Google Drive Integration")
        st.sidebar.info(f"Google Drive folder: {gdrive_folder}")
        
        if st.sidebar.button("Sync Downloads to Google Drive"):
            with st.sidebar.status("Syncing to Google Drive...", expanded=True) as status:
                try:
                    # Import the sync function from main
                    import sys
                    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    from main import sync_downloads_to_gdrive
                    
                    result = sync_downloads_to_gdrive()
                    if result:
                        status.update(label="Sync completed successfully!", state="complete")
                    else:
                        status.update(label="Sync failed. Check logs for details.", state="error")
                except Exception as e:
                    status.update(label=f"Error: {str(e)}", state="error")
    
    # Configuration status
    status = config.get_status()
    
    if status["validation_errors"]:
        st.sidebar.markdown('<div class="alert-box warning-box">', unsafe_allow_html=True)
        st.sidebar.warning("Configuration Errors:")
        for error in status["validation_errors"]:
            st.sidebar.markdown(f"- {error}")
        st.sidebar.markdown('</div>', unsafe_allow_html=True)
    
    # Display configuration status
    with st.sidebar.expander("Configuration Status"):
        st.write("DGFT URL:", "✅ Configured" if status["dgft_url_configured"] else "❌ Not configured")
        st.write("Email:", "✅ Configured" if status["email_configured"] else "❌ Not configured")
        st.write("GROQ API:", "✅ Configured" if status["groq_configured"] else "❌ Not configured")
    
    # Actions
    st.sidebar.markdown('<h2 class="subsection-header">Actions</h2>', unsafe_allow_html=True)
    
    if st.sidebar.button("Fetch Latest Updates"):
        fetch_updates(dgft_url)
        # Force refresh
        st.experimental_rerun()
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["Updates", "Search", "Analysis"])
    
    # Updates Tab
    with tab1:
        st.markdown('<h2 class="section-header">Regulatory Updates</h2>', unsafe_allow_html=True)
        
        # Load data from data handler
        documents = data_handler.get_documents()
        
        # Check if data is available
        if not any(docs for docs in documents.values()):
            st.info("No updates available. Click 'Fetch Latest Updates' to retrieve data.")
        else:
            # Display each section
            for section in ["Notifications", "Public Notices", "Circulars"]:
                docs = documents.get(section, [])
                
                if docs:
                    st.markdown(f'<h3 class="subsection-header">{section}</h3>', unsafe_allow_html=True)
                    
                    # Create dataframe for display
                    df = pd.DataFrame(docs)
                    
                    # Format dates for display
                    if "date" in df.columns:
                        df["formatted_date"] = df["date"].apply(format_date)
                    
                    # Display as table
                    st.dataframe(
                        df[["date", "description"]].rename(
                            columns={"date": "Date", "description": "Description"}
                        ),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Select document for details
                    st.markdown('<div class="alert-box info-box">', unsafe_allow_html=True)
                    selected_desc = st.selectbox(
                        "Select document to view details:",
                        options=[doc["description"] for doc in docs],
                        key=f"select_{section}"
                    )
                    
                    # Get selected document
                    selected_doc = next((doc for doc in docs if doc["description"] == selected_desc), None)
                    
                    if selected_doc:
                        # Show document details
                        st.write("**Date:**", format_date(selected_doc["date"]))
                        st.write("**Description:**", selected_doc["description"])
                        
                        # Actions
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("Download & Process", key=f"process_{section}"):
                                processed_doc = process_document(section, selected_doc)
                                if processed_doc:
                                    # Store in session state for display
                                    st.session_state["current_document"] = processed_doc
                                    # Force refresh to show analysis tab
                                    st.rerun()
                        
                        with col2:
                            if st.button("Send Email Notification", key=f"email_{section}"):
                                # Check if document is processed
                                document_id = data_handler.generate_document_id(
                                    section, selected_doc["date"], selected_doc["description"][:50]
                                )
                                processed_doc = data_handler.get_processed_document(document_id)
                                
                                if processed_doc:
                                    send_email_notification(processed_doc)
                                else:
                                    # Process document first
                                    processed_doc = process_document(section, selected_doc)
                                    if processed_doc:
                                        send_email_notification(processed_doc)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
    
    # Search Tab
    with tab2:
        st.markdown('<h2 class="section-header">Search Updates</h2>', unsafe_allow_html=True)
        
        query = st.text_input("Enter your search query:", placeholder="e.g., Show me the latest notifications about exports")
        
        if st.button("Search") and query:
            results = process_query(query)
            
            if results:
                st.success(f"Found {len(results)} matching document(s)")
                
                # Display results
                results_df = pd.DataFrame([
                    {
                        "Section": r["section"],
                        "Date": format_date(r["date"]),
                        "Description": r["description"]
                    }
                    for r in results
                ])
                
                st.dataframe(results_df, use_container_width=True, hide_index=True)
                
                # Select document for processing
                st.markdown('<div class="alert-box info-box">', unsafe_allow_html=True)
                if len(results) == 1:
                    selected_result = results[0]
                else:
                    selected_desc = st.selectbox(
                        "Select document to process:",
                        options=[r["description"] for r in results]
                    )
                    selected_result = next((r for r in results if r["description"] == selected_desc), None)
                
                if selected_result:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("Download & Process", key="process_search"):
                            processed_doc = process_document(
                                selected_result["section"],
                                selected_result
                            )
                            if processed_doc:
                                # Store in session state for display
                                st.session_state["current_document"] = processed_doc
                                # Force refresh to show analysis tab
                                st.experimental_rerun()
                    
                    with col2:
                        if st.button("Send Email Notification", key="email_search"):
                            # Check if document is processed
                            document_id = data_handler.generate_document_id(
                                selected_result["section"],
                                selected_result["date"],
                                selected_result["description"][:50]
                            )
                            processed_doc = data_handler.get_processed_document(document_id)
                            
                            if processed_doc:
                                send_email_notification(processed_doc)
                            else:
                                # Process document first
                                processed_doc = process_document(
                                    selected_result["section"],
                                    selected_result
                                )
                                if processed_doc:
                                    send_email_notification(processed_doc)
                
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("No matching documents found")
    
    # Analysis Tab
    with tab3:
        st.markdown('<h2 class="section-header">Document Analysis</h2>', unsafe_allow_html=True)
        
        # Check if current document is available in session
        current_doc = st.session_state.get("current_document")
        
        # If no current document, try to load the latest document
        if not current_doc:
            # Find the latest document across all sections
            latest_section = None
            latest_doc = None
            latest_date = None
            
            for section, docs in data_handler.get_documents().items():
                if docs and (latest_date is None or docs[0]["date"] > latest_date):
                    latest_section = section
                    latest_doc = docs[0]
                    latest_date = docs[0]["date"]
            
            if latest_doc:
                st.info(f"Automatically loading the latest document from {latest_section}")
                
                # Process the latest document
                document_id = data_handler.generate_document_id(
                    latest_section, latest_doc["date"], latest_doc["description"][:50]
                )
                
                # Check if it's already processed
                current_doc = data_handler.get_processed_document(document_id)
                
                # If not processed, process it now
                if not current_doc:
                    with st.spinner(f"Processing latest {latest_section} document..."):
                        current_doc = process_document(latest_section, latest_doc, download=True)
                        if current_doc:
                            st.session_state["current_document"] = current_doc
        
        if current_doc:
            # Display document details
            st.markdown(f'<h3 class="subsection-header">{current_doc["section"]}</h3>', unsafe_allow_html=True)
            
            st.markdown('<div class="alert-box success-box">', unsafe_allow_html=True)
            st.write("**Date:**", format_date(current_doc["date"]))
            st.write("**Description:**", current_doc["description"])
            
            if "pdf_path" in current_doc and current_doc["pdf_path"]:
                st.write("**File:**", os.path.basename(current_doc["pdf_path"]))
                
                # Add Google Drive upload button if GDRIVE_FOLDER_URL is configured
                gdrive_url = config.gdrive_folder_url
                if gdrive_url:
                    st.markdown(f"**Google Drive:** [View Folder]({gdrive_url})")
            
            if "processed_at" in current_doc:
                st.write("**Processed:**", current_doc["processed_at"])
            st.markdown('</div>', unsafe_allow_html=True)
            
            # PART 1: Always show the raw extracted text first
            st.markdown("### 1. Raw Extracted Text")
            if "text" in current_doc and current_doc["text"]:
                # Display text length
                text_length = len(current_doc["text"])
                st.info(f"Extracted {text_length} characters of text from the document")
                
                # Always show some text, even if minimal
                text_to_show = current_doc["text"][:5000] + ("..." if len(current_doc["text"]) > 5000 else "")
                st.text_area("Extracted text preview:", text_to_show, height=200)
            else:
                st.error("No text could be extracted from this document. The PDF may be an image-only document or there might be issues with text extraction.")
            
            # PART 2: Show the analysis
            st.markdown("### 2. Document Analysis")
            if "analysis" in current_doc and current_doc["analysis"]:
                st.markdown(current_doc["analysis"])
            else:
                st.warning("No analysis available for this document.")
            
            # Email action
            if st.button("Send Email Notification", key="email_analysis"):
                send_email_notification(current_doc)
        else:
            st.info("No document analyzed yet. Process a document from the Updates or Search tab, or check for OCR configuration issues if document processing fails.")

# Run the application
if __name__ == "__main__":
    main()