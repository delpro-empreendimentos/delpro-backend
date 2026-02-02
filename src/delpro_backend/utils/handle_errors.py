"""Decorator to handle errors in FastAPI routes."""

import inspect
from functools import wraps

from fastapi import HTTPException, status
from pydantic import ValidationError

from delpro_backend.utils.logger import get_logger

logger_extra = {"component.name": "ErrorHandler", "component.version": "v2"}
logger = get_logger(__name__)


def handle_errors(func):
    """Decorator to handle errors in FastAPI routes."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            res = func(*args, **kwargs)

            if inspect.isawaitable(res):
                return await res
            else:
                return res

        except ValidationError as e:
            logger.exception("Validation error: %s", e, extra=logger_extra)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=e.errors()
            ) from e
        except ValueError as e:
            logger.exception("Value error: %s", str(e), exc_info=e, extra=logger_extra)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        except HTTPException as e:
            logger.error(str(e), extra=logger_extra)
            raise e
        except Exception as e:
            error_msg = f"An unexpected error occurred: {str(e)}"
            logger.exception(error_msg, exc_info=e, extra=logger_extra)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg
            ) from e

    return wrapper
