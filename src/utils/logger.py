#!/usr/bin/env python3
"""
Logger utility module for the Telegram LibGen Bot.
Provides consistent logging configuration across the application.
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler


def setup_logger(name: str, level: str = None) -> logging.Logger:
    """
    Set up a logger with consistent formatting and handlers.
    
    Args:
        name: Logger name (usually __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    # Get log level from environment or use default
    if level is None:
        level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Create logger
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
        
    logger.setLevel(getattr(logging, level))
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(name)s: %(message)s (%(filename)s:%(lineno)d)'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler (if logs directory exists)
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    if os.path.exists(logs_dir):
        log_file = os.path.join(logs_dir, 'bot.log')
        
        # Rotating file handler (max 10MB, keep 5 backups)
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    
    # Error file handler for errors and above
    if os.path.exists(logs_dir):
        error_file = os.path.join(logs_dir, 'errors.log')
        error_handler = RotatingFileHandler(
            error_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        logger.addHandler(error_handler)
    
    return logger


def log_function_call(func):
    """
    Decorator to log function calls with parameters and execution time.
    
    Usage:
        @log_function_call
        def my_function(param1, param2):
            pass
    """
    import functools
    import time
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        
        # Log function entry
        args_str = ', '.join(str(arg) for arg in args[:3])  # Limit to first 3 args
        if len(args) > 3:
            args_str += ', ...'
            
        kwargs_str = ', '.join(f'{k}={v}' for k, v in list(kwargs.items())[:3])
        if len(kwargs) > 3:
            kwargs_str += ', ...'
            
        logger.debug(f"Calling {func.__name__}({args_str}{', ' + kwargs_str if kwargs_str else ''})")
        
        # Execute function and measure time
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} completed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {str(e)}")
            raise
            
    return wrapper


def log_async_function_call(func):
    """
    Decorator to log async function calls with parameters and execution time.
    
    Usage:
        @log_async_function_call
        async def my_async_function(param1, param2):
            pass
    """
    import functools
    import time
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        
        # Log function entry
        args_str = ', '.join(str(arg)[:50] for arg in args[:3])  # Limit arg length
        if len(args) > 3:
            args_str += ', ...'
            
        kwargs_str = ', '.join(f'{k}={str(v)[:50]}' for k, v in list(kwargs.items())[:3])
        if len(kwargs) > 3:
            kwargs_str += ', ...'
            
        logger.debug(f"Calling {func.__name__}({args_str}{', ' + kwargs_str if kwargs_str else ''})")
        
        # Execute function and measure time
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} completed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {str(e)}")
            raise
            
    return wrapper


class LoggerMixin:
    """
    Mixin class that provides a logger instance to any class.
    
    Usage:
        class MyClass(LoggerMixin):
            def __init__(self):
                super().__init__()
                self.logger.info("MyClass initialized")
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = setup_logger(self.__class__.__module__)


def create_startup_log():
    """Create a startup log entry with system information."""
    logger = setup_logger('startup')
    
    logger.info("=" * 60)
    logger.info("Telegram LibGen Bot Starting Up")
    logger.info("=" * 60)
    logger.info(f"Startup time: {datetime.now().isoformat()}")
    logger.info(f"Python version: {os.sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Log level: {os.getenv('LOG_LEVEL', 'INFO')}")
    logger.info("=" * 60)


# Example usage and testing
if __name__ == "__main__":
    # Test the logger
    test_logger = setup_logger(__name__)
    
    test_logger.debug("This is a debug message")
    test_logger.info("This is an info message")
    test_logger.warning("This is a warning message")
    test_logger.error("This is an error message")
    
    # Test decorator
    @log_function_call
    def test_function(param1, param2="default"):
        import time
        time.sleep(0.1)  # Simulate some work
        return f"Result: {param1} + {param2}"
    
    result = test_function("hello", param2="world")
    print(f"Function returned: {result}")
    
    # Test startup log
    create_startup_log()
