"""Tests for exception models."""

import os
import unittest

from delpro_backend.models.v1.exception_models import (
    DocumentProcessingError,
    DuplicatedWhatsappRequestError,
    InvalidRequestError,
    InvalidWhatsappMessageError,
    MissingParametersRequestError,
    ResourceNotFoundError,
    WebhookValidationError,
)
from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)


class TestResourceNotFoundError(unittest.TestCase):
    """Tests for ResourceNotFoundError exception."""

    def test_creates_with_resource_type_and_id(self):
        """Test exception stores resource type and ID."""
        error = ResourceNotFoundError("Document", "doc-123")

        self.assertEqual(error.resource_type, "Document")
        self.assertEqual(error.resource_id, "doc-123")

    def test_message_includes_resource_info(self):
        """Test exception message includes resource type and ID."""
        error = ResourceNotFoundError("Chunk", "chunk-456")

        self.assertIn("Chunk", str(error))
        self.assertIn("chunk-456", str(error))
        self.assertIn("not found", str(error))


class TestDocumentProcessingError(unittest.TestCase):
    """Tests for DocumentProcessingError exception."""

    def test_creates_with_document_id_and_reason(self):
        """Test exception stores document ID and reason."""
        error = DocumentProcessingError("doc-789", "PDF parsing failed")

        self.assertEqual(error.document_id, "doc-789")
        self.assertEqual(error.reason, "PDF parsing failed")

    def test_message_includes_document_info(self):
        """Test exception message includes document ID and reason."""
        error = DocumentProcessingError("doc-abc", "Invalid format")

        self.assertIn("doc-abc", str(error))
        self.assertIn("Invalid format", str(error))
        self.assertIn("Failed to process", str(error))


class TestOtherExceptions(unittest.TestCase):
    """Tests for remaining exception classes."""

    def test_webhook_validation_error_is_exception(self):
        """Test WebhookValidationError is an Exception."""
        err = WebhookValidationError("bad webhook")
        self.assertIsInstance(err, Exception)

    def test_invalid_whatsapp_message_error(self):
        """Test InvalidWhatsappMessageError is an Exception."""
        err = InvalidWhatsappMessageError()
        self.assertIsInstance(err, Exception)

    def test_duplicated_whatsapp_request_error(self):
        """Test DuplicatedWhatsappRequestError is an Exception."""
        err = DuplicatedWhatsappRequestError()
        self.assertIsInstance(err, Exception)

    def test_missing_parameters_request_error(self):
        """Test MissingParametersRequestError is an Exception."""
        err = MissingParametersRequestError()
        self.assertIsInstance(err, Exception)

    def test_invalid_request_error(self):
        """Test InvalidRequestError is an Exception."""
        err = InvalidRequestError("bad request")
        self.assertIsInstance(err, Exception)
