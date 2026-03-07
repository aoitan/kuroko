import threading
import time
import urllib.request
import urllib.parse
import pytest
import hmac
from pathlib import Path
from kanpe.cli import main

@pytest.fixture
def run_kanpe_server(tmp_path):
    report_file = tmp_path / "report.md"
    report_file.write_text("# Test Report", encoding="utf-8")
    
    # We need to run the server in a separate thread.
    # However, main() starts a forever loop. We need to mock TCPServer or similar.
    # For now, let's focus on a more unit-testable approach if possible.
    pass

# Instead of full server integration test which is flaky in CI, 
# let's mock the Handler or test the logic directly if possible.
# Since Handler is local to main(), we can't easily import it.

# Let's add a test for LLMClient's error handling since we changed it.
from kuroko.llm import LLMClient
from kuroko.config import LLMConfig
from unittest.mock import patch, MagicMock

def test_llm_client_raises_on_error():
    config = LLMConfig(url="http://localhost:11434/v1")
    client = LLMClient(config)
    
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = Exception("API Down")
        with pytest.raises(RuntimeError) as excinfo:
            client.chat_completion([{"role": "user", "content": "hi"}])
        assert "Error connecting to LLM API: API Down" in str(excinfo.value)
