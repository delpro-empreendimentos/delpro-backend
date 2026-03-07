"""Tests for dev_state module."""

import unittest

import delpro_backend.utils.dev_state as dev_state


class TestDevState(unittest.TestCase):
    """Tests for dev_state toggle/is_active functions."""

    def setUp(self):
        """Reset dev_state to False before each test."""
        dev_state._active = False

    def test_is_active_default_false(self):
        """dev_state starts as inactive."""
        self.assertFalse(dev_state.is_active())

    def test_toggle_activates(self):
        """First toggle returns True and sets state to active."""
        result = dev_state.toggle()
        self.assertTrue(result)
        self.assertTrue(dev_state.is_active())

    def test_toggle_twice_returns_to_false(self):
        """Two toggles return to the original inactive state."""
        dev_state.toggle()
        result = dev_state.toggle()
        self.assertFalse(result)
        self.assertFalse(dev_state.is_active())
