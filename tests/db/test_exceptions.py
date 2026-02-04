"""Tests for database exceptions."""

import os
import unittest

from delpro_backend.db.exceptions import DocumentProcessingError, ResourceNotFoundError
from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)
os.environ.setdefault("MAX_TOKENS_SUMMARY", "500")


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
