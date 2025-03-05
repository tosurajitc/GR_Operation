"""
Date Utilities

Helper functions for date parsing, comparison, and formatting.
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

def parse_date(date_string: str) -> Optional[datetime]:
    """Parse a date string in various formats.
    
    Args:
        date_string: The date string to parse.
        
    Returns:
        Parsed datetime object or None if parsing fails.
    """
    if not date_string:
        return None
    
    # Clean the date string
    date_string = date_string.strip()
    
    # Try common Indian date formats
    formats = [
        # DD/MM/YYYY
        "%d/%m/%Y",
        # DD-MM-YYYY
        "%d-%m-%Y",
        # DD.MM.YYYY
        "%d.%m.%Y",
        # DD MMM, YYYY (e.g., 15 Jan, 2023)
        "%d %b, %Y",
        # DD MMMM, YYYY (e.g., 15 January, 2023)
        "%d %B, %Y",
        # YYYY-MM-DD (ISO format)
        "%Y-%m-%d",
        # MM/DD/YYYY (US format - less likely but possible)
        "%m/%d/%Y",
        # DD Month YYYY
        "%d %B %Y",
        # DD Mon YYYY
        "%d %b %Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    
    # Try to extract date using regex if standard formats fail
    try:
        # Match patterns like "15th January, 2023" or "15 Jan 2023"
        day_pattern = r'(\d{1,2})(st|nd|rd|th)?'
        month_pattern = r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
        year_pattern = r'(20\d{2})'  # Assuming years from 2000 to 2099
        
        pattern = fr'{day_pattern}\s+{month_pattern}[\s,]+{year_pattern}'
        match = re.search(pattern, date_string, re.IGNORECASE)
        
        if match:
            day = int(match.group(1))
            month = match.group(3)
            year = int(match.group(5))
            
            # Convert month name to month number
            month_map = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            
            month_num = month_map.get(month.lower()[:3])
            
            if month_num:
                return datetime(year, month_num, day)
    except Exception as e:
        logger.warning(f"Error extracting date with regex: {str(e)}")
    
    logger.warning(f"Failed to parse date string: {date_string}")
    return None

def is_recent_date(date_obj: datetime, days: int = 30) -> bool:
    """Check if a date is within the specified number of days from today.
    
    Args:
        date_obj: The date to check.
        days: The number of days to consider as recent.
        
    Returns:
        True if the date is within the specified number of days, False otherwise.
    """
    if not date_obj:
        return False
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff_date = today - timedelta(days=days)
    
    return date_obj >= cutoff_date

def format_date(date_obj: datetime, format_str: str = "%d %B, %Y") -> str:
    """Format a datetime object as a string.
    
    Args:   
        date_obj: The datetime object to format.
        format_str: The format string to use.
        
    Returns:
        Formatted date string or "N/A" if date_obj is None.
    """
    if not date_obj:
        return "N/A"
    
    return date_obj.strftime(format_str)

def get_date_range(start_date: datetime, end_date: datetime) -> str:
    """Get a formatted date range string.
    
    Args:
        start_date: The start date.
        end_date: The end date.
        
    Returns:
        Formatted date range string.
    """
    if not start_date or not end_date:
        return "N/A"
    
    start_str = format_date(start_date)
    end_str = format_date(end_date)
    
    return f"{start_str} to {end_str}"