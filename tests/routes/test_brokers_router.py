"""Tests for brokers_router via TestClient."""

import datetime
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)

from delpro_backend.main import app  # noqa: E402
from delpro_backend.models.v1.exception_models import (  # noqa: E402
    InvalidRequestError,
    ResourceNotFoundError,
)


def _make_broker_row(
    phone="5511999",
    name="John",
    interactions=5,
    product_type_luxo=False,
    product_type_alto=False,
    product_type_medio=False,
    product_type_mcmv=False,
    sell_type_investimento=False,
    sell_type_moradia=False,
    region_zona_norte=False,
    region_zona_sul=False,
    region_zona_central=False,
    sold_delpro_product=False,
):
    """Create a MagicMock representing a BrokerRow."""
    row = MagicMock()
    row.phone_number = phone
    row.name = name
    row.interactions = interactions
    row.product_type_luxo = product_type_luxo
    row.product_type_alto = product_type_alto
    row.product_type_medio = product_type_medio
    row.product_type_mcmv = product_type_mcmv
    row.sell_type_investimento = sell_type_investimento
    row.sell_type_moradia = sell_type_moradia
    row.region_zona_norte = region_zona_norte
    row.region_zona_sul = region_zona_sul
    row.region_zona_central = region_zona_central
    row.sold_delpro_product = sold_delpro_product
    row.date_joined = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)
    row.last_message_at = datetime.datetime(2024, 6, 1, tzinfo=datetime.UTC)
    return row


class TestBrokersRouterList(unittest.TestCase):
    """Tests for GET /brokers list endpoint."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.brokers_router.broker_service")
    def test_list_returns_200(self, mock_svc):
        """Test listing brokers returns 200 with paginated envelope."""
        mock_svc.list_brokers = AsyncMock(return_value=([_make_broker_row()], 1))
        response = self.client.get("/brokers")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(len(body["items"]), 1)

    @patch("delpro_backend.routes.v1.brokers_router.broker_service")
    def test_list_empty_returns_200(self, mock_svc):
        """Test listing with no brokers returns empty paginated envelope."""
        mock_svc.list_brokers = AsyncMock(return_value=([], 0))
        response = self.client.get("/brokers")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["items"], [])
        self.assertEqual(body["total"], 0)

    @patch("delpro_backend.routes.v1.brokers_router.broker_service")
    def test_list_with_search(self, mock_svc):
        """Test listing with search parameter."""
        mock_svc.list_brokers = AsyncMock(return_value=([_make_broker_row()], 1))
        response = self.client.get("/brokers?search=john")
        self.assertEqual(response.status_code, 200)
        mock_svc.list_brokers.assert_awaited_once_with(
            sort_by="interactions", order="desc", search="john", skip=0, limit=20
        )

    @patch("delpro_backend.routes.v1.brokers_router.broker_service")
    def test_list_with_sort(self, mock_svc):
        """Test listing with custom sort parameters."""
        mock_svc.list_brokers = AsyncMock(return_value=([], 0))
        response = self.client.get("/brokers?sort_by=name&order=asc")
        self.assertEqual(response.status_code, 200)
        mock_svc.list_brokers.assert_awaited_once_with(
            sort_by="name", order="asc", search=None, skip=0, limit=20
        )

    @patch("delpro_backend.routes.v1.brokers_router.broker_service")
    def test_list_pagination_params(self, mock_svc):
        """Test skip/limit query params are forwarded to service."""
        mock_svc.list_brokers = AsyncMock(return_value=([], 50))
        response = self.client.get("/brokers?skip=20&limit=20")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 50)
        mock_svc.list_brokers.assert_awaited_once_with(
            sort_by="interactions", order="desc", search=None, skip=20, limit=20
        )


class TestBrokersRouterGet(unittest.TestCase):
    """Tests for GET /brokers/{phone_number} endpoint."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.brokers_router.broker_service")
    def test_get_returns_200(self, mock_svc):
        """Test getting a broker returns 200."""
        mock_svc.get_broker = AsyncMock(return_value=_make_broker_row())
        response = self.client.get("/brokers/5511999")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["phone_number"], "5511999")
        self.assertEqual(data["name"], "John")

    @patch("delpro_backend.routes.v1.brokers_router.broker_service")
    def test_get_not_found_returns_404(self, mock_svc):
        """Test getting a non-existent broker returns 404."""
        mock_svc.get_broker = AsyncMock(
            side_effect=ResourceNotFoundError("Broker", "999")
        )
        response = self.client.get("/brokers/999")
        self.assertEqual(response.status_code, 404)


class TestBrokersRouterCreate(unittest.TestCase):
    """Tests for POST /brokers endpoint."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.brokers_router.broker_service")
    def test_create_returns_201(self, mock_svc):
        """Test creating a broker returns 201."""
        mock_svc.create_broker = AsyncMock(return_value=_make_broker_row())
        response = self.client.post(
            "/brokers",
            json={"phone_number": "5511999", "name": "John"},
        )
        self.assertEqual(response.status_code, 201)

    @patch("delpro_backend.routes.v1.brokers_router.broker_service")
    def test_create_duplicate_returns_400(self, mock_svc):
        """Test creating a duplicate broker returns 400."""
        mock_svc.create_broker = AsyncMock(
            side_effect=InvalidRequestError("Broker already exists")
        )
        response = self.client.post(
            "/brokers",
            json={"phone_number": "5511999", "name": "John"},
        )
        self.assertEqual(response.status_code, 400)


class TestBrokersRouterUpdate(unittest.TestCase):
    """Tests for PUT /brokers/{phone_number} endpoint."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.brokers_router.broker_service")
    def test_update_returns_200(self, mock_svc):
        """Test updating a broker returns 200."""
        mock_svc.update_broker = AsyncMock(
            return_value=_make_broker_row(name="Jane")
        )
        response = self.client.put(
            "/brokers/5511999",
            json={"name": "Jane"},
        )
        self.assertEqual(response.status_code, 200)

    @patch("delpro_backend.routes.v1.brokers_router.broker_service")
    def test_update_not_found_returns_404(self, mock_svc):
        """Test updating a non-existent broker returns 404."""
        mock_svc.update_broker = AsyncMock(
            side_effect=ResourceNotFoundError("Broker", "999")
        )
        response = self.client.put(
            "/brokers/999",
            json={"name": "X"},
        )
        self.assertEqual(response.status_code, 404)


class TestBrokersRouterDelete(unittest.TestCase):
    """Tests for DELETE /brokers/{phone_number} endpoint."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app, raise_server_exceptions=False)

    @patch("delpro_backend.routes.v1.brokers_router.broker_service")
    def test_delete_returns_204(self, mock_svc):
        """Test deleting a broker returns 204."""
        mock_svc.delete_broker = AsyncMock()
        response = self.client.delete("/brokers/5511999")
        self.assertEqual(response.status_code, 204)

    @patch("delpro_backend.routes.v1.brokers_router.broker_service")
    def test_delete_not_found_returns_404(self, mock_svc):
        """Test deleting a non-existent broker returns 404."""
        mock_svc.delete_broker = AsyncMock(
            side_effect=ResourceNotFoundError("Broker", "999")
        )
        response = self.client.delete("/brokers/999")
        self.assertEqual(response.status_code, 404)
