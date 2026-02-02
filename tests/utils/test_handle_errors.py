"""Tests for the error handling decorator."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_db")
os.environ.setdefault("WPP_PHONE_ID", "test")
os.environ.setdefault("WPP_TEST_NUMER", "test")
os.environ.setdefault("WPP_TOKEN", "test")
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("PROJECT_ID", "test")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.0-flash")
os.environ.setdefault("MAX_TOKENS", "1024")
os.environ.setdefault("LLM_TEMPERATURE", "0")
os.environ.setdefault("MAX_HISTORY_MESSAGES", "20")

from fastapi import HTTPException, status
from pydantic import BaseModel, ValidationError

from delpro_backend.utils.handle_errors import handle_errors


class TestHandleErrors(unittest.IsolatedAsyncioTestCase):
    """Tests for handle_errors decorator."""

    async def test_handles_async_function_success(self):
        """Test that async functions return correctly."""

        @handle_errors
        async def async_func():
            return "success"

        result = await async_func()
        self.assertEqual(result, "success")

    async def test_handles_sync_function_success(self):
        """Test that sync functions return correctly."""

        @handle_errors
        def sync_func():
            return "success"

        result = await sync_func()  # type: ignore[misc]
        self.assertEqual(result, "success")

    async def test_handles_validation_error(self):
        """Test that ValidationError is converted to 422 HTTPException."""

        class TestModel(BaseModel):
            value: int

        @handle_errors
        async def func_with_validation_error():
            # Force a validation error by trying to validate invalid data
            try:
                TestModel(value="abc")  # type: ignore[arg-type]
            except ValidationError as e:
                raise e

        with self.assertRaises(HTTPException) as cm:
            await func_with_validation_error()

        self.assertEqual(cm.exception.status_code, status.HTTP_422_UNPROCESSABLE_CONTENT)

    async def test_handles_value_error(self):
        """Test that ValueError is converted to 400 HTTPException."""

        @handle_errors
        async def func_with_value_error():
            raise ValueError("Invalid value")

        with self.assertRaises(HTTPException) as cm:
            await func_with_value_error()

        self.assertEqual(cm.exception.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, "Invalid value")

    async def test_handles_http_exception(self):
        """Test that HTTPException is re-raised as-is."""

        @handle_errors
        async def func_with_http_exception():
            raise HTTPException(status_code=404, detail="Not found")

        with self.assertRaises(HTTPException) as cm:
            await func_with_http_exception()

        self.assertEqual(cm.exception.status_code, 404)
        self.assertEqual(cm.exception.detail, "Not found")

    async def test_handles_generic_exception(self):
        """Test that generic Exception is converted to 500 HTTPException."""

        @handle_errors
        async def func_with_generic_error():
            raise Exception("Something went wrong")

        with self.assertRaises(HTTPException) as cm:
            await func_with_generic_error()

        self.assertEqual(cm.exception.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("Something went wrong", cm.exception.detail)
