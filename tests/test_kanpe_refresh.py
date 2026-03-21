from unittest.mock import patch

import click

from kanpe.cli import render_markdown_to_html, refresh_report

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


def test_refresh_report_uses_shared_renderer_without_subprocess(tmp_path):
    report_path = tmp_path / "report.md"
    report_path.write_text("# Old", encoding="utf-8")

    with patch("kanpe.cli.render_report_to_path") as mock_render, \
         patch("subprocess.run") as mock_subprocess:
        refresh_report(
            report_path=report_path,
            kuroko_cmd="kuroko",
            report_args="--project kuroko --since 2026-03-01",
            include_worklist=False,
            config="kuroko.config.yaml",
        )

    mock_render.assert_called_once()
    kwargs = mock_render.call_args.kwargs
    assert kwargs["output_path"] == report_path
    assert kwargs["project"] == ("kuroko",)
    assert kwargs["since"] == "2026-03-01"
    assert kwargs["include_worklist"] is False
    assert kwargs["config_path"] == "kuroko.config.yaml"
    mock_subprocess.assert_not_called()


def test_refresh_report_preserves_worklist_section_when_present(tmp_path):
    report_path = tmp_path / "report.md"
    report_path.write_text("# Title\n\n## Worklist\n", encoding="utf-8")

    with patch("kanpe.cli.render_report_to_path") as mock_render:
        refresh_report(
            report_path=report_path,
            kuroko_cmd="kuroko",
            report_args="",
            include_worklist=False,
        )

    assert mock_render.call_args.kwargs["include_worklist"] is True


def test_refresh_report_wraps_invalid_report_args_as_click_error(tmp_path):
    report_path = tmp_path / "report.md"
    report_path.write_text("# Title\n", encoding="utf-8")

    try:
        refresh_report(
            report_path=report_path,
            kuroko_cmd="kuroko",
            report_args="--unknown-option",
        )
    except click.ClickException as exc:
        assert "Unsupported report args" in str(exc)
    else:
        raise AssertionError("Expected ClickException")
