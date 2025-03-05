"""
Logging Utilities

Helper functions and configuration for logging.
"""

import os
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

def setup_logging(
    log_level: int = logging.INFO,
    log_file: Optional[str] = None,
    log_to_console: bool = True,
    app_name: str = "dgft_monitor"
) -> logging.Logger:
    """Set up logging configuration.
    
    Args:
        log_level: The logging level (e.g., logging.INFO, logging.DEBUG).
        log_file: Path to the log file. If None, logs are only sent to console.
        log_to_console: Whether to log to console.
        app_name: Name of the application for the logger.
        
    Returns:
        Configured logger instance.
    """
    # Create logger
    logger = logging.getLogger(app_name)
    logger.setLevel(log_level)
    logger.handlers = []  # Clear existing handlers
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler if requested
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Create file handler if log file provided
    if log_file:
        # Ensure the directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_default_log_file() -> str:
    """Get a default log file path based on current date/time.
    
    Returns:
        Path to the default log file.
    """
    # Create logs directory in the current working directory
    logs_dir = Path.cwd() / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Create a timestamped log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"dgft_monitor_{timestamp}.log"
    
    return str(log_file)

class LogCapture:
    """Context manager to capture log messages."""
    
    def __init__(self, logger_name: str = None, level: int = logging.INFO):
        """Initialize the log capture.
        
        Args:
            logger_name: Name of the logger to capture. If None, captures the root logger.
            level: Minimum log level to capture.
        """
        self.logger_name = logger_name
        self.level = level
        self.messages = []
        self.handler = None
    
    def __enter__(self):
        """Set up the log capture when entering the context."""
        logger = logging.getLogger(self.logger_name)
        
        # Create a handler that appends to our messages list
        class ListHandler(logging.Handler):
            def __init__(self, messages_list):
                super().__init__()
                self.messages_list = messages_list
            
            def emit(self, record):
                self.messages_list.append(self.format(record))
        
        self.handler = ListHandler(self.messages)
        self.handler.setLevel(self.level)
        
        # Create formatter
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        self.handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(self.handler)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up when exiting the context."""
        if self.handler:
            logger = logging.getLogger(self.logger_name)
            logger.removeHandler(self.handler)
    
    def get_messages(self) -> list:
        """Get the captured log messages.
        
        Returns:
            List of captured log messages.
        """
        return self.messages

def log_execution_time(logger: logging.Logger):
    """Decorator to log function execution time.
    
    Args:
        logger: The logger to use.
        
    Returns:
        Decorated function.
    """
    import time
    import functools
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            
            execution_time = end_time - start_time
            logger.info(f"Function '{func.__name__}' executed in {execution_time:.2f} seconds")
            
            return result
        return wrapper
    
    return decorator

def log_exceptions(logger: logging.Logger, reraise: bool = True):
    """Decorator to log exceptions raised by a function.
    
    Args:
        logger: The logger to use.
        reraise: Whether to re-raise the exception after logging.
        
    Returns:
        Decorated function.
    """
    import functools
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Exception in '{func.__name__}': {str(e)}")
                if reraise:
                    raise
        return wrapper
    
    return decorator