"""Tests for LLM client."""

import unittest
from unittest.mock import patch, MagicMock

from llm import get_commentary
from personalities import get_system_prompt, PERSONALITIES


class TestPersonalities(unittest.TestCase):
    def test_all_personalities_exist(self):
        expected = ["passive-aggressive", "existential", "supportive", "eco-guilt", "judgy", "unhinged"]
        for name in expected:
            self.assertIn(name, PERSONALITIES)
            self.assertIsInstance(PERSONALITIES[name], str)
            self.assertTrue(len(PERSONALITIES[name]) > 50)

    def test_get_system_prompt_builtin(self):
        prompt = get_system_prompt("judgy")
        self.assertEqual(prompt, PERSONALITIES["judgy"])

    def test_get_system_prompt_custom(self):
        custom = "You are a pirate printer. Arrr."
        prompt = get_system_prompt("custom", custom)
        self.assertEqual(prompt, custom)

    def test_get_system_prompt_unknown_falls_back(self):
        prompt = get_system_prompt("nonexistent")
        self.assertEqual(prompt, PERSONALITIES["passive-aggressive"])


class TestOpenAI(unittest.TestCase):
    @patch("llm.requests.post")
    def test_call_openai_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Nice document you got there."}}]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        config = {
            "llm": {"provider": "openai", "model": "gpt-4o", "api_key": "sk-test", "base_url": ""},
        }
        result = get_commentary("Hello world", "judgy", config)
        self.assertEqual(result, "Nice document you got there.")

        # Verify the request
        call_kwargs = mock_post.call_args
        self.assertIn("api.openai.com", call_kwargs[0][0])
        self.assertEqual(call_kwargs[1]["headers"]["Authorization"], "Bearer sk-test")

    @patch("llm.requests.post")
    def test_call_openai_no_key_raises(self, mock_post):
        config = {
            "llm": {"provider": "openai", "model": "gpt-4o", "api_key": "", "base_url": ""},
        }
        with self.assertRaises(ValueError):
            get_commentary("Hello", "judgy", config)


class TestAnthropic(unittest.TestCase):
    @patch("llm.requests.post")
    def test_call_anthropic_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "content": [{"text": "Interesting choice of document."}]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        config = {
            "llm": {"provider": "anthropic", "model": "claude-sonnet-4-20250514", "api_key": "sk-ant-test", "base_url": ""},
        }
        result = get_commentary("Hello world", "supportive", config)
        self.assertEqual(result, "Interesting choice of document.")


class TestOllama(unittest.TestCase):
    @patch("llm.requests.post")
    def test_call_ollama_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "message": {"content": "Trees died for this."}
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        config = {
            "llm": {"provider": "ollama", "model": "llama3.1", "api_key": "", "base_url": ""},
        }
        result = get_commentary("Hello world", "eco-guilt", config)
        self.assertEqual(result, "Trees died for this.")

        call_kwargs = mock_post.call_args
        self.assertIn("localhost:11434", call_kwargs[0][0])


class TestTextTruncation(unittest.TestCase):
    @patch("llm.requests.post")
    def test_long_text_is_truncated(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "That's a lot of text."}}]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        config = {
            "llm": {"provider": "openai", "model": "gpt-4o", "api_key": "sk-test", "base_url": ""},
        }
        long_text = "word " * 5000  # ~25000 chars
        get_commentary(long_text, "judgy", config)

        # Check that the user message was truncated
        call_kwargs = mock_post.call_args
        messages = call_kwargs[1]["json"]["messages"]
        user_msg = messages[1]["content"]
        self.assertIn("[Document truncated", user_msg)


if __name__ == "__main__":
    unittest.main()
