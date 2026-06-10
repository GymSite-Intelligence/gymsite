"""Testes do wrapper generate_content_resilient (429 backoff)."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from tools._genai_client import (
    generate_content_resilient,
    is_resource_exhausted,
)


class TestIsResourceExhausted(unittest.TestCase):
    def test_message_429(self) -> None:
        self.assertTrue(is_resource_exhausted(RuntimeError("429 Too Many Requests")))

    def test_resource_exhausted_name(self) -> None:
        class ResourceExhausted(Exception):
            pass

        self.assertTrue(is_resource_exhausted(ResourceExhausted("quota")))

    def test_permanent_error(self) -> None:
        self.assertFalse(is_resource_exhausted(ValueError("invalid argument")))


class TestGenerateContentResilient(unittest.TestCase):
    @patch("tools._genai_client.time.sleep")
    def test_retries_on_429_then_succeeds(self, mock_sleep: MagicMock) -> None:
        client = MagicMock()
        ok = MagicMock()
        client.models.generate_content.side_effect = [
            RuntimeError("429 RESOURCE_EXHAUSTED"),
            RuntimeError("429 RESOURCE_EXHAUSTED"),
            ok,
        ]

        out = generate_content_resilient(
            client,
            model="gemini-2.5-flash",
            contents="q",
            max_retries=3,
            base_delay=4.0,
        )
        self.assertIs(out, ok)
        self.assertEqual(client.models.generate_content.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("tools._genai_client.time.sleep")
    def test_raises_after_max_retries(self, mock_sleep: MagicMock) -> None:
        client = MagicMock()
        client.models.generate_content.side_effect = RuntimeError(
            "429 RESOURCE_EXHAUSTED"
        )

        with self.assertRaises(RuntimeError):
            generate_content_resilient(
                client,
                model="gemini-2.5-flash",
                contents="q",
                max_retries=3,
                base_delay=4.0,
            )
        self.assertEqual(client.models.generate_content.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    def test_non_429_not_retried(self) -> None:
        client = MagicMock()
        client.models.generate_content.side_effect = ValueError("bad request")

        with self.assertRaises(ValueError):
            generate_content_resilient(
                client,
                model="gemini-2.5-flash",
                contents="q",
                max_retries=3,
            )
        self.assertEqual(client.models.generate_content.call_count, 1)


if __name__ == "__main__":
    unittest.main()
