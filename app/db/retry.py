import time
import functools
from typing import Any, Callable
from sqlalchemy.exc import OperationalError, DisconnectionError
import logging

logger = logging.getLogger(__name__)

def db_retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator to retry database operations on connection errors.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, DisconnectionError) as e:
                    last_exception = e
                    
                    # Don't retry on the last attempt
                    if attempt == max_retries:
                        logger.error(f"Database operation failed after {max_retries} retries: {e}")
                        raise e
                    
                    logger.warning(f"Database connection error on attempt {attempt + 1}/{max_retries + 1}: {e}")
                    logger.info(f"Retrying in {current_delay} seconds...")
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
                except Exception as e:
                    # Don't retry on non-connection errors
                    logger.error(f"Non-connection database error: {e}")
                    raise e
            
            # This should never be reached, but just in case
            raise last_exception
        
        return wrapper
    return decorator