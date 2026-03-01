import pytest
from datetime import datetime
from kuroko.reporter import generate_report


@pytest.fixture
def dummy_entries():
    return [
        {
            "date": "2026-02-28",
            "time": "17:00",
            "phase": "closing",
            "project": "kuroko",
            "issue": None,
            "act": "READMEへの案内を追加",
            "evd": "git push origin main",
            "block": "なし",
            "file_path": "/path/to/2026-02-28__kuroko__misc.md"
        },
        {
            "date": "2026-02-28",
            "time": "11:30",
            "phase": "coding",
            "project": "kuroko",
            "issue": "1",
            "act": "parserとcollectorを実装",
            "evd": "uv run pytest",
            "block": "依存関係の解決に少し手間取った",
            "file_path": "/path/to/2026-02-28__kuroko__ISSUE-1.md"
        }
    ]


def test_generate_report(dummy_entries):
    report = generate_report(
        entries=dummy_entries,
        title="Test Report",
        generated_at=datetime(2026, 2, 28, 15, 58, 59),
        per_project_files=5,
        filters={"project": "kuroko"},
        include_path=True,
        include_evidence=True,
        collapse_details=True
    )
    
    assert "# Test Report" in report
    assert "- generated_at: 2026-02-28T15:58:59" in report
    assert "## Status" in report
    assert "## Blockers" in report
    assert "## Recent" in report
    assert "## Sources" in report
    
    # Status table
    assert "| 2026-02-28 | 17:00 | done | kuroko | - | READMEへの案内を追加 |" in report
    
    # Blocker list
    assert "依存関係の解決に少し手間取った" in report
    assert "<details markdown=\"1\"><summary>details</summary>" in report
    
    # Recent list
    assert "- 17:00 done kuroko - READMEへの案内を追加" in report
    assert "- 11:30 code kuroko #1 parserとcollectorを実装" in report
