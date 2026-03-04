from kanpe.cli import render_markdown_to_html

def test_render_html_has_refresh_button():
    html = render_markdown_to_html("# Title", nonce="test-nonce")
    assert "Refresh & Reload" in html
    assert "id=\"refresh-btn\"" in html
    assert "value=\"test-nonce\"" in html
