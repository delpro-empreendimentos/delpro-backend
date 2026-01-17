import unittest

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
