# app/utils/retry_handler.py
"""
Retry mechanism for handling transient PDF processing failures.
"""

import asyncio
import logging
from typing import Callable, Any, Optional
from functools import wraps
from .pdf_exceptions import RetryExhaustedError

logger = logging.getLogger(__name__)

class RetryHandler:
    """Handles retry logic for PDF processing operations"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        """
        Initialize retry handler
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def exponential_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        delay = self.base_delay * (2 ** attempt)
        return min(delay, self.max_delay)
    
    async def retry_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Retry an async function with exponential backoff
        
        Args:
            func: Async function to retry
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            RetryExhaustedError: If all retries are exhausted
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"Attempt {attempt + 1}/{self.max_retries + 1} for function {func.__name__}")
                result = await func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"Function {func.__name__} succeeded on attempt {attempt + 1}")
                return result
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed for function {func.__name__}: {str(e)}")
                
                if attempt < self.max_retries:
                    delay = self.exponential_backoff(attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All retry attempts exhausted for function {func.__name__}")
        
        raise RetryExhaustedError(self.max_retries) from last_exception
    
    def retry_sync(self, func: Callable, *args, **kwargs) -> Any:
        """
        Retry a sync function with exponential backoff
        
        Args:
            func: Sync function to retry
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            RetryExhaustedError: If all retries are exhausted
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"Attempt {attempt + 1}/{self.max_retries + 1} for function {func.__name__}")
                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"Function {func.__name__} succeeded on attempt {attempt + 1}")
                return result
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed for function {func.__name__}: {str(e)}")
                
                if attempt < self.max_retries:
                    delay = self.exponential_backoff(attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    import time
                    time.sleep(delay)
                else:
                    logger.error(f"All retry attempts exhausted for function {func.__name__}")
        
        raise RetryExhaustedError(self.max_retries) from last_exception

def retry_on_failure(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator for retrying functions on failure
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            retry_handler = RetryHandler(max_retries, base_delay)
            return await retry_handler.retry_async(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            retry_handler = RetryHandler(max_retries, base_delay)
            return retry_handler.retry_sync(func, *args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
