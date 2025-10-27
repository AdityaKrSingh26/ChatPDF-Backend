# app/utils/timeout_handler.py
"""
Timeout handling for PDF processing operations.
"""

import asyncio
import logging
from typing import Any, Callable, Optional
from functools import wraps
from .pdf_exceptions import ProcessingTimeoutError

logger = logging.getLogger(__name__)

class TimeoutHandler:
    """Handles timeout for PDF processing operations"""
    
    def __init__(self, timeout_seconds: int = 300):
        """
        Initialize timeout handler
        
        Args:
            timeout_seconds: Timeout duration in seconds (default: 5 minutes)
        """
        self.timeout_seconds = timeout_seconds
    
    async def with_timeout(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute an async function with timeout
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            ProcessingTimeoutError: If function times out
        """
        try:
            logger.info(f"Executing function {func.__name__} with {self.timeout_seconds}s timeout")
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.timeout_seconds
            )
            logger.info(f"Function {func.__name__} completed successfully")
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Function {func.__name__} timed out after {self.timeout_seconds} seconds")
            raise ProcessingTimeoutError(self.timeout_seconds)
        except Exception as e:
            logger.error(f"Function {func.__name__} failed: {str(e)}")
            raise

def with_timeout(timeout_seconds: int = 300):
    """
    Decorator for adding timeout to functions
    
    Args:
        timeout_seconds: Timeout duration in seconds
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            timeout_handler = TimeoutHandler(timeout_seconds)
            return await timeout_handler.with_timeout(func, *args, **kwargs)
        
        return async_wrapper
    
    return decorator
