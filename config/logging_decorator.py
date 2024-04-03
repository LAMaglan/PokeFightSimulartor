import functools
import traceback
from config.logging_config import get_logger

def log_decorator(logger_name):
    logger = get_logger(logger_name)
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                logger.info(f"Executing {func.__name__} with args: {args}, kwargs: {kwargs}")  # Start executing
                response = await func(*args, **kwargs)
                logger.info(f"Executed {func.__name__} successfully")  # Finished executing
                return response
            except Exception as exc:
                logger.error(f"Exception in {func.__name__}: {exc}, Traceback: {traceback.format_exc()}")
                raise exc
        return wrapper
    return decorator