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
