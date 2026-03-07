import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from delpro_backend.main import app
from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)


class TestMain(unittest.TestCase):
    def setUp(self):
        """Setup method to initialize the TestClient."""
        self.test_client = TestClient(app)

    def test_root_endpoint(self):
        """Test the root endpoint."""
        response = self.test_client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({"detail": "Alive!"}, response.json())

    def test_health_endpoint(self):
        """Test the health check endpoint."""
        response = self.test_client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({"status": "ok"}, response.json())


class TestLifespan(unittest.IsolatedAsyncioTestCase):
    """Tests for the application lifespan hook."""

    @patch("delpro_backend.main.engine")
    async def test_lifespan_creates_tables(self, mock_engine):
        """Test that lifespan hook creates database tables on startup."""
        from fastapi import FastAPI

        from delpro_backend.main import lifespan

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
