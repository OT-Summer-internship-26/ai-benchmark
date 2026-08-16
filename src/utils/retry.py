"""
Retry logic with exponential backoff for LLM and API calls.
"""

import time
import logging
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,),
):
    """
    Decorator for retry logic with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay between retries
        max_delay: Maximum delay between retries
        exceptions: Tuple of exceptions to catch and retry on
    
    Example:
        @retry_with_backoff(max_attempts=3, exceptions=(TimeoutError, ConnectionError))
        def call_api():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    logger.debug(f"Attempt {attempt}/{max_attempts} for {func.__name__}")
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {str(e)}"
                        )
                        raise
                    
                    # Calculate delay with backoff
                    delay = min(delay * backoff_factor, max_delay)
                    jitter = delay * 0.1  # 10% jitter to avoid thundering herd
                    actual_delay = delay - jitter + (jitter * 2 * (__import__('random').random()))
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}. "
                        f"Retrying in {actual_delay:.2f}s. Error: {str(e)}"
                    )
                    time.sleep(actual_delay)
            
            raise last_exception
        
        return wrapper
    return decorator


def retry_on_status_code(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    status_codes: tuple = (429, 500, 502, 503, 504),  # Rate limit, server errors
):
    """
    Decorator for retry on specific HTTP status codes.
    Expects function to return response object with .status_code attribute.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            
            for attempt in range(1, max_attempts + 1):
                response = func(*args, **kwargs)
                
                if not hasattr(response, 'status_code') or response.status_code not in status_codes:
                    return response
                
                if attempt == max_attempts:
                    logger.error(
                        f"Max retries reached for {func.__name__} (status {response.status_code})"
                    )
                    return response
                
                delay = min(delay * backoff_factor, 60.0)
                logger.warning(
                    f"Status {response.status_code} from {func.__name__}. "
                    f"Retrying in {delay:.2f}s"
                )
                time.sleep(delay)
            
            return response
        
        return wrapper
    return decorator
