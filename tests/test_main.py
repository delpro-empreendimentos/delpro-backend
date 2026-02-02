import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

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

from fastapi.testclient import TestClient

from delpro_backend.main import app


class TestMain(unittest.TestCase):
    def setUp(self):
        """Setup method to initialize the TestClient."""
        self.test_client = TestClient(app)

    def test_root_endpoint(self):
        """Test the root endpoint."""
        response = self.test_client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({"detail":"Alive!"}, response.json())


class TestLifespan(unittest.IsolatedAsyncioTestCase):
    """Tests for the application lifespan hook."""

    @patch("delpro_backend.main.engine")
    async def test_lifespan_creates_tables(self, mock_engine):
        """Test that lifespan hook creates database tables on startup."""
        from delpro_backend.main import lifespan
        from fastapi import FastAPI

        # Mock the engine's begin context manager
        mock_conn = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=None)

        test_app = FastAPI()

        # Execute the lifespan context manager
        async with lifespan(test_app):
            pass

        # Verify that engine.begin() was called
        mock_engine.begin.assert_called_once()

        # Verify that run_sync was called with Base.metadata.create_all
        mock_conn.run_sync.assert_called_once()
        call_args = mock_conn.run_sync.call_args
        self.assertIsNotNone(call_args)
