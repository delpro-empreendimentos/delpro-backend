"""Tests for whatsapp_api module (WhatsappAPI class methods)."""

import json
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)

from delpro_backend.services.whatsapp_api import WhatsappAPI  # noqa: E402


def _api():
    return WhatsappAPI()


class TestSendMessage(unittest.IsolatedAsyncioTestCase):
    """Tests for WhatsappAPI.send_message."""

    @patch("delpro_backend.services.whatsapp_api.httpx.AsyncClient")
    async def test_send_text_message_success(self, mock_client_class):
        """Test sending a text message calls the right endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)

        await _api().send_message(to="5511999", text="Hello!", msg_type="text")

        mock_client.post.assert_awaited_once()
        call_kwargs = mock_client.post.call_args
        payload = json.loads(call_kwargs[1]["content"])
        self.assertEqual(payload["type"], "text")
        self.assertEqual(payload["text"]["body"], "Hello!")
        self.assertEqual(payload["to"], "5511999")

    @patch("delpro_backend.services.whatsapp_api.httpx.AsyncClient")
    async def test_send_image_message_success(self, mock_client_class):
        """Test sending an image message with media_id."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)

        await _api().send_message(to="5511999", msg_type="image", media_id="media-123")

        call_kwargs = mock_client.post.call_args
        payload = json.loads(call_kwargs[1]["content"])
        self.assertEqual(payload["type"], "image")
        self.assertEqual(payload["image"]["id"], "media-123")

    @patch("delpro_backend.services.whatsapp_api.httpx.AsyncClient")
    async def test_send_document_message_success(self, mock_client_class):
        """Test sending a document message with media_id and filename."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)

        await _api().send_message(
            to="5511999", msg_type="document",
            media_id="media-456", filename="report.pdf",
        )

        call_kwargs = mock_client.post.call_args
        payload = json.loads(call_kwargs[1]["content"])
        self.assertEqual(payload["type"], "document")
        self.assertEqual(payload["document"]["id"], "media-456")
        self.assertEqual(payload["document"]["filename"], "report.pdf")

    @patch("delpro_backend.services.whatsapp_api.httpx.AsyncClient")
    async def test_send_message_calls_raise_for_status(self, mock_client_class):
        """Test that raise_for_status is called on the response."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)

        await _api().send_message(to="5511999", text="Hi", msg_type="text")

        mock_response.raise_for_status.assert_called_once()

    @patch("delpro_backend.services.whatsapp_api.httpx.AsyncClient")
    async def test_send_message_unknown_type_sends_no_body_key(self, mock_client_class):
        """Test that an unknown msg_type skips all if/elif branches."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)

        await _api().send_message(to="5511999", msg_type="audio")

        call_kwargs = mock_client.post.call_args
        payload = json.loads(call_kwargs[1]["content"])
        self.assertNotIn("text", payload)
        self.assertNotIn("image", payload)
        self.assertNotIn("document", payload)
        self.assertEqual(payload["type"], "audio")


class TestUploadMedia(unittest.IsolatedAsyncioTestCase):
    """Tests for WhatsappAPI.upload_media."""

    @patch("delpro_backend.services.whatsapp_api.httpx.AsyncClient")
    async def test_upload_image_calls_send_as_image(self, mock_client_class):
        """Test that uploading an image sends it as image msg_type."""
        mock_upload_resp = MagicMock()
        mock_upload_resp.raise_for_status = MagicMock()
        mock_upload_resp.json.return_value = {"id": "media-abc-123"}

        mock_send_resp = MagicMock()
        mock_send_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[mock_upload_resp, mock_send_resp])
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)

        await _api().upload_media(
            file_bytes=b"\xff\xd8\xff" + b"x" * 100,
            mime_type="image/jpeg",
            filename="photo.jpg",
            phone_number="5511999",
        )

        self.assertEqual(mock_client.post.await_count, 2)

    @patch("delpro_backend.services.whatsapp_api.httpx.AsyncClient")
    async def test_upload_pdf_calls_send_as_document(self, mock_client_class):
        """Test that uploading a PDF sends it as document msg_type."""
        mock_upload_resp = MagicMock()
        mock_upload_resp.raise_for_status = MagicMock()
        mock_upload_resp.json.return_value = {"id": "media-pdf-456"}

        mock_send_resp = MagicMock()
        mock_send_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[mock_upload_resp, mock_send_resp])
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)

        await _api().upload_media(
            file_bytes=b"%PDF-1.4" + b"x" * 100,
            mime_type="application/pdf",
            filename="report.pdf",
            phone_number="5511999",
        )

        self.assertEqual(mock_client.post.await_count, 2)

    @patch("delpro_backend.services.whatsapp_api.httpx.AsyncClient")
    async def test_upload_media_propagates_http_error(self, mock_client_class):
        """Test that HTTP errors from upload are propagated."""
        import httpx

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.RequestError("Connection failed"),
        )
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=False)

        with self.assertRaises(httpx.RequestError):
            await _api().upload_media(
                file_bytes=b"fake",
                mime_type="image/jpeg",
                filename="photo.jpg",
                phone_number="5511999",
            )
