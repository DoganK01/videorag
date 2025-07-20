"""
Reusable decorators for enhancing application logic, such as retries.
"""
import asyncio
import logging
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)

def async_retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0) -> Callable:
    """
    A decorator to add exponential backoff retry logic to an async function.

    Args:
        max_retries: The maximum number of times to retry.
        delay: The initial delay between retries in seconds.
        backoff: The multiplier for the delay after each retry.
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            tries = 0
            current_delay = delay
            while tries < max_retries:
                try:
                    return await f(*args, **kwargs)
                except Exception as e:
                    tries += 1
                    if tries == max_retries:
                        logger.error(
                            f"Function '{f.__name__}' failed after {max_retries} retries. Giving up.",
                            exc_info=True
                        )
                        raise
                    
                    logging.warning(
                        f"Function '{f.__name__}' failed with {type(e).__name__}: {e}. "
                        f"Retrying in {current_delay:.2f}s... ({tries}/{max_retries})"
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator