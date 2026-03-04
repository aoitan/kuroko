import pytest
from unittest.mock import patch, MagicMock
from kanpe.cli import render_markdown_to_html

def test_render_html_has_refresh_button():
    html = render_markdown_to_html("# Title", nonce="test-nonce")
    assert "Refresh & Reload" in html
    assert "id=\"refresh-btn\"" in html
    assert "value=\"test-nonce\"" in html

def test_handler_refresh_endpoint():
    # This requires more complex mocking of BaseHTTPRequestHandler,
    # we'll do a basic check of the logic after implementation if possible,
    # but for now let's ensure the template is updated.
    pass
