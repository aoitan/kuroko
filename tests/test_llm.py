import json
import unittest
from unittest.mock import patch, MagicMock
from kuroko.config import LLMConfig
from kuroko.llm import LLMClient

class TestLLMClient(unittest.TestCase):
    def setUp(self):
        self.config = LLMConfig(
            url="http://localhost:11434/v1",
            model="llama3",
            api_key="test-key"
        )
        self.client = LLMClient(self.config)

    @patch("urllib.request.urlopen")
    def test_chat_completion_success(self, mock_urlopen):
        # Mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "content": "Next step: Implement tests."
                }
            }]
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        messages = [{"role": "user", "content": "hello"}]
        result = self.client.chat_completion(messages)
        
        self.assertEqual(result, "Next step: Implement tests.")
        
        # Verify call
        args, kwargs = mock_urlopen.call_args
        req = args[0]
        self.assertEqual(req.full_url, "http://localhost:11434/v1/chat/completions")
        self.assertEqual(req.get_header("Content-type"), "application/json")
        self.assertEqual(req.get_header("Authorization"), "Bearer test-key")

    @patch("urllib.request.urlopen")
    def test_chat_completion_error(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Connection error")
        
        messages = [{"role": "user", "content": "hello"}]
        with self.assertRaises(RuntimeError) as cm:
            self.client.chat_completion(messages)
        self.assertIn("Error connecting to LLM API: Connection error", str(cm.exception))

if __name__ == "__main__":
    unittest.main()
