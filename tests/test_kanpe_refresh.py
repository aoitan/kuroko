from kanpe.cli import render_markdown_to_html

def test_render_html_has_refresh_button():
    html = render_markdown_to_html("# Title", nonce="test-nonce")
    assert "Refresh & Reload" in html
    assert "id=\"refresh-btn\"" in html
    assert "value=\"test-nonce\"" in html

def test_render_html_has_suggest_buttons():
    html = render_markdown_to_html("# Title", nonce="test-nonce")
    assert "🚀 通常" in html
    assert "🧹 保守救済" in html
    assert "🔍 深掘り" in html
    assert "id=\"suggest-btn-normal\"" in html
    assert "id=\"project-select\"" in html
    assert "getSuggestion('normal')" in html
    assert "nonce': 'test-nonce'" in html
