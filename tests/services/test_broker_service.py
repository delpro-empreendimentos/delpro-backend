"""Tests for BrokerService."""

import datetime
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)

from delpro_backend.models.v1.broker_models import (  # noqa: E402
    CreateBrokerRequest,
    UpdateBrokerRequest,
)
from delpro_backend.models.v1.exception_models import (  # noqa: E402
    InvalidRequestError,
    ResourceNotFoundError,
)
from delpro_backend.services.broker_service import BrokerService  # noqa: E402

PATCH_TARGET = "delpro_backend.services.broker_service.AsyncSessionFactory"


class TestCreateBroker(unittest.IsolatedAsyncioTestCase):
    """Tests for BrokerService.create_broker."""

    @patch(PATCH_TARGET)
    async def test_create_success(self, mock_factory):
        """Test creating a new broker succeeds."""
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        mock_factory.return_value.__aenter__.return_value = mock_session

        svc = BrokerService()
        data = CreateBrokerRequest(phone_number="5511999", name="John")
        await svc.create_broker(data)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()

    @patch(PATCH_TARGET)
    async def test_create_duplicate_raises(self, mock_factory):
        """Test creating a duplicate broker raises InvalidRequestError."""
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=MagicMock())
        mock_factory.return_value.__aenter__.return_value = mock_session

        svc = BrokerService()
        data = CreateBrokerRequest(phone_number="5511999", name="John")

        with self.assertRaises(InvalidRequestError):
            await svc.create_broker(data)


class TestGetBroker(unittest.IsolatedAsyncioTestCase):
    """Tests for BrokerService.get_broker."""

    @patch(PATCH_TARGET)
    async def test_get_success(self, mock_factory):
        """Test getting an existing broker succeeds."""
        mock_row = MagicMock()
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_row)
        mock_factory.return_value.__aenter__.return_value = mock_session

        svc = BrokerService()
        result = await svc.get_broker("5511999")
        self.assertEqual(result, mock_row)

    @patch(PATCH_TARGET)
    async def test_get_not_found_raises(self, mock_factory):
        """Test getting a non-existent broker raises ResourceNotFoundError."""
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        mock_factory.return_value.__aenter__.return_value = mock_session

        svc = BrokerService()

        with self.assertRaises(ResourceNotFoundError):
            await svc.get_broker("999")


class TestListBrokers(unittest.IsolatedAsyncioTestCase):
    """Tests for BrokerService.list_brokers."""

    @patch(PATCH_TARGET)
    async def test_list_returns_all(self, mock_factory):
        """Test listing brokers returns all rows with total."""
        mock_rows = [MagicMock(), MagicMock()]
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 2
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = mock_rows

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[mock_count_result, mock_data_result])
        mock_factory.return_value.__aenter__.return_value = mock_session

        svc = BrokerService()
        rows, total = await svc.list_brokers()
        self.assertEqual(len(rows), 2)
        self.assertEqual(total, 2)

    @patch(PATCH_TARGET)
    async def test_list_invalid_sort_defaults(self, mock_factory):
        """Test listing with invalid sort_by defaults to interactions."""
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[mock_count_result, mock_data_result])
        mock_factory.return_value.__aenter__.return_value = mock_session

        svc = BrokerService()
        rows, total = await svc.list_brokers(sort_by="invalid_column")
        self.assertEqual(rows, [])
        self.assertEqual(total, 0)


class TestUpdateBroker(unittest.IsolatedAsyncioTestCase):
    """Tests for BrokerService.update_broker."""

    @patch(PATCH_TARGET)
    async def test_update_success(self, mock_factory):
        """Test updating a broker succeeds."""
        mock_row = MagicMock()
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_row)
        mock_factory.return_value.__aenter__.return_value = mock_session

        svc = BrokerService()
        data = UpdateBrokerRequest(name="Jane")
        await svc.update_broker("5511999", data)

        mock_session.commit.assert_awaited_once()
        self.assertEqual(mock_row.name, "Jane")

    @patch(PATCH_TARGET)
    async def test_update_not_found_raises(self, mock_factory):
        """Test updating non-existent broker raises ResourceNotFoundError."""
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        mock_factory.return_value.__aenter__.return_value = mock_session

        svc = BrokerService()
        data = UpdateBrokerRequest(name="Jane")

        with self.assertRaises(ResourceNotFoundError):
            await svc.update_broker("999", data)


class TestDeleteBroker(unittest.IsolatedAsyncioTestCase):
    """Tests for BrokerService.delete_broker."""

    @patch(PATCH_TARGET)
    async def test_delete_success(self, mock_factory):
        """Test deleting a broker succeeds."""
        mock_row = MagicMock()
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_row)
        mock_factory.return_value.__aenter__.return_value = mock_session

        svc = BrokerService()
        await svc.delete_broker("5511999")

        mock_session.delete.assert_awaited_once_with(mock_row)
        mock_session.commit.assert_awaited_once()

    @patch(PATCH_TARGET)
    async def test_delete_not_found_raises(self, mock_factory):
        """Test deleting non-existent broker raises ResourceNotFoundError."""
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        mock_factory.return_value.__aenter__.return_value = mock_session

        svc = BrokerService()

        with self.assertRaises(ResourceNotFoundError):
            await svc.delete_broker("999")


class TestUpsertFromInteraction(unittest.IsolatedAsyncioTestCase):
    """Tests for BrokerService.upsert_from_interaction."""

    @patch(PATCH_TARGET)
    async def test_upsert_creates_new(self, mock_factory):
        """Test upsert creates new broker when not found."""
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        mock_factory.return_value.__aenter__.return_value = mock_session

        svc = BrokerService()
        await svc.upsert_from_interaction("5511999", "John")

        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()

    @patch(PATCH_TARGET)
    async def test_upsert_updates_existing(self, mock_factory):
        """Test upsert increments interactions for existing broker."""
        mock_row = MagicMock()
        mock_row.interactions = 3

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_row)
        mock_factory.return_value.__aenter__.return_value = mock_session

        svc = BrokerService()
        await svc.upsert_from_interaction("5511999", "John")

        self.assertEqual(mock_row.interactions, 4)
        self.assertEqual(mock_row.name, "John")
        mock_session.commit.assert_awaited_once()

    @patch(PATCH_TARGET)
    async def test_upsert_empty_name_does_not_update_name(self, mock_factory):
        """Test upsert with empty name does not overwrite broker's name."""
        mock_row = MagicMock()
        mock_row.interactions = 2
        mock_row.name = "ExistingName"

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_row)
        mock_factory.return_value.__aenter__.return_value = mock_session

        svc = BrokerService()
        await svc.upsert_from_interaction("5511999", "")

        self.assertEqual(mock_row.name, "ExistingName")
        self.assertEqual(mock_row.interactions, 3)


class TestGetMessages(unittest.IsolatedAsyncioTestCase):
    """Tests for BrokerService.get_messages."""

    @patch(PATCH_TARGET)
    async def test_get_messages_returns_list_and_total(self, mock_factory):
        """Test get_messages returns list of messages and total count."""
        mock_rows = [MagicMock(), MagicMock()]
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 2
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = mock_rows

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[mock_count_result, mock_data_result])
        mock_factory.return_value.__aenter__.return_value = mock_session

        svc = BrokerService()
        rows, total = await svc.get_messages("5511999")
        self.assertEqual(len(rows), 2)
        self.assertEqual(total, 2)

    @patch(PATCH_TARGET)
    async def test_get_messages_empty_returns_zero(self, mock_factory):
        """Test get_messages returns empty list when no messages."""
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[mock_count_result, mock_data_result])
        mock_factory.return_value.__aenter__.return_value = mock_session

        svc = BrokerService()
        rows, total = await svc.get_messages("5511999", skip=0, limit=30)
        self.assertEqual(rows, [])
        self.assertEqual(total, 0)


class TestListBrokersSearch(unittest.IsolatedAsyncioTestCase):
    """Tests for BrokerService.list_brokers with search."""

    @patch(PATCH_TARGET)
    async def test_list_with_search_filters_results(self, mock_factory):
        """Test listing with search parameter uses ilike filter."""
        mock_rows = [MagicMock()]
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = mock_rows

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[mock_count_result, mock_data_result])
        mock_factory.return_value.__aenter__.return_value = mock_session

        svc = BrokerService()
        rows, total = await svc.list_brokers(search="john")
        self.assertEqual(len(rows), 1)
        self.assertEqual(total, 1)

    @patch(PATCH_TARGET)
    async def test_list_with_asc_order(self, mock_factory):
        """Test listing with ascending order."""
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[mock_count_result, mock_data_result])
        mock_factory.return_value.__aenter__.return_value = mock_session

        svc = BrokerService()
        rows, total = await svc.list_brokers(order="asc")
        self.assertEqual(rows, [])
        self.assertEqual(total, 0)
