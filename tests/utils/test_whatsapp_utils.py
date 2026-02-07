"""Tests for WhatsApp utility functions."""

import unittest

from delpro_backend.utils.whatsapp_utils import is_valid_whatsapp_message


class TestIsValidWhatsappMessage(unittest.TestCase):
    """Tests for the is_valid_whatsapp_message function."""

    def test_valid_message_structure(self):
        """Should return True for a valid WhatsApp message."""
        body = {
            "object": "whatsapp_business_account",
            "entry": [
                {"changes": [{"value": {"messages": [{"id": "msg_123", "text": {"body": "Hi"}}]}}]}
            ],
        }
        self.assertTrue(is_valid_whatsapp_message(body))

    def test_missing_object(self):
        """Should return False if object is missing."""
        body = {"entry": [{"changes": [{"value": {"messages": [{}]}}]}]}
        self.assertFalse(is_valid_whatsapp_message(body))

    def test_missing_entry(self):
        """Should return False if entry is missing."""
        body = {"object": "whatsapp"}
        self.assertFalse(is_valid_whatsapp_message(body))

    def test_missing_changes(self):
        """Should return False if changes is missing."""
        body = {"object": "whatsapp", "entry": [{}]}
        self.assertFalse(is_valid_whatsapp_message(body))

    def test_missing_value(self):
        """Should return False if value is missing."""
        body = {"object": "whatsapp", "entry": [{"changes": [{}]}]}
        self.assertFalse(is_valid_whatsapp_message(body))

    def test_missing_messages(self):
        """Should return False if messages is missing."""
        body = {"object": "whatsapp", "entry": [{"changes": [{"value": {}}]}]}
        self.assertFalse(is_valid_whatsapp_message(body))

    def test_empty_messages(self):
        """Should return False if messages is empty."""
        body = {"object": "whatsapp", "entry": [{"changes": [{"value": {"messages": []}}]}]}
        self.assertFalse(is_valid_whatsapp_message(body))

    def test_empty_body(self):
        """Should return False for empty dict."""
        self.assertFalse(is_valid_whatsapp_message({}))

    def test_none_values(self):
        """Should return False if any key is None."""
        body = {"object": None, "entry": [{"changes": [{"value": {"messages": [{}]}}]}]}
        self.assertFalse(is_valid_whatsapp_message(body))


if __name__ == "__main__":
    unittest.main()
