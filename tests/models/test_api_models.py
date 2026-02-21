"""Tests for api_models Pydantic models."""

import os
import unittest

from tests.keys_test import DEFAULT_KEYS

for key, value in DEFAULT_KEYS.items():
    os.environ.setdefault(key, value)

from pydantic import ValidationError  # noqa: E402

from delpro_backend.models.v1.api_models import SendMessageRequest, SendMessageResponse  # noqa: E402


class TestSendMessageRequest(unittest.TestCase):
    """Tests for SendMessageRequest model."""

    def test_valid_request(self):
        """Test that a valid request is constructed correctly."""
        req = SendMessageRequest(
            session_id="5511999990000",
            input="Hello there",
            user_name="Carlos Mendes",
        )
        self.assertEqual(req.session_id, "5511999990000")
        self.assertEqual(req.input, "Hello there")
        self.assertEqual(req.user_name, "Carlos Mendes")

    def test_empty_session_id_raises(self):
        """Test that empty session_id raises ValidationError."""
        with self.assertRaises(ValidationError):
            SendMessageRequest(session_id="", input="Hi", user_name="User")

    def test_session_id_too_long_raises(self):
        """Test that session_id exceeding 64 chars raises ValidationError."""
        with self.assertRaises(ValidationError):
            SendMessageRequest(session_id="x" * 65, input="Hi", user_name="User")

    def test_empty_input_raises(self):
        """Test that empty input raises ValidationError."""
        with self.assertRaises(ValidationError):
            SendMessageRequest(session_id="abc", input="", user_name="User")

    def test_user_name_too_long_raises(self):
        """Test that user_name exceeding 100 chars raises ValidationError."""
        with self.assertRaises(ValidationError):
            SendMessageRequest(session_id="abc", input="Hi", user_name="x" * 101)

    def test_missing_fields_raise(self):
        """Test that missing required fields raise ValidationError."""
        with self.assertRaises(ValidationError):
            SendMessageRequest()  # type: ignore


class TestSendMessageResponse(unittest.TestCase):
    """Tests for SendMessageResponse model."""

    def test_valid_response(self):
        """Test that a valid response is constructed correctly."""
        resp = SendMessageResponse(
            session_id="5511999990000",
            response="Here is your answer.",
        )
        self.assertEqual(resp.session_id, "5511999990000")
        self.assertEqual(resp.response, "Here is your answer.")

    def test_missing_fields_raise(self):
        """Test that missing required fields raise ValidationError."""
        with self.assertRaises(ValidationError):
            SendMessageResponse()  # type: ignore

    def test_serializes_to_dict(self):
        """Test model_dump produces expected keys."""
        resp = SendMessageResponse(session_id="s1", response="r1")
        d = resp.model_dump()
        self.assertIn("session_id", d)
        self.assertIn("response", d)
