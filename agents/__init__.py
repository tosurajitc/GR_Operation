# agents/__init__.py
"""
Agent modules for DGFT regulatory monitor.
"""

from .web_scraper_agent import WebScraperAgent
from .pdf_extractor_agent import PDFExtractorAgent
from .ocr_agent import OCRAgent
from .analysis_agent import AnalysisAgent
from .coordinator_agent import CoordinatorAgent

__all__ = [
    'WebScraperAgent',
    'PDFExtractorAgent',
    'OCRAgent',
    'AnalysisAgent',
    'CoordinatorAgent'
]
