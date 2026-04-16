from kanpe.brief_formatter import (
    VIEW_DAILY,
    VIEW_NEXT_ACTIONS,
    VIEW_PENDING,
    VIEW_PROJECT_BRIEF,
    VIEW_WEEKLY,
    format_shinko_results,
)


def test_project_brief_formats_sections_and_guards():
    results = [
        {
            "project": "kuroko",
            "score": 91,
            "analyzed_at": "2000-01-01T00:00:00+00:00",
            "source_hash": "hash-1",
            "payload_truncated": True,
            "records": [
                {
                    "kind": "project_state",
                    "summary": "見積もり待ちの案件が残っている",
                    "judgements": {
                        "is_todo": False,
                        "is_ongoing": True,
                        "should_review_this_week": True,
                    },
                    "blocked_reason": None,
                    "next_action": None,
                    "evidence": [{"source_id": 1, "chunk_id": 2, "quote_excerpt": "先方見積もり待ち"}],
                },
                {
                    "kind": "task",
                    "summary": "見積もり依頼を整理する",
                    "judgements": {
                        "is_todo": True,
                        "is_ongoing": False,
                        "should_review_this_week": False,
                    },
                    "blocked_reason": "先方回答待ち",
                    "next_action": "担当者へ連絡する",
                    "evidence": [],
                },
            ],
        }
    ]

    rendered = format_shinko_results(results, view=VIEW_PROJECT_BRIEF)

    assert "## 案件別ブリーフ" in rendered
    assert "### kuroko" in rendered
    assert "Freshness: 2000-01-01T00:00:00+00:00 (stale)" in rendered
    assert "Source hash: `hash-1`" in rendered
    assert "payload_truncated=true" in rendered
    assert "#### Summary" in rendered
    assert "- 見積もり待ちの案件が残っている" in rendered
    assert "#### Pending" in rendered
    assert "- 見積もり依頼を整理する" in rendered
    assert "#### This Week Review" in rendered
    assert "#### Next Actions" in rendered
    assert "- 担当者へ連絡する" in rendered
    assert "#### Caution" in rendered
    assert "- 先方回答待ち" in rendered
    assert "#### Evidence" in rendered
    assert "先方見積もり待ち (source:1, chunk:2)" in rendered


def test_project_brief_distinguishes_missing_records_from_missing_signal():
    rendered = format_shinko_results(
        [{"project": "legacy", "score": 0, "suggestion": "fallback", "records": []}],
        view=VIEW_PROJECT_BRIEF,
    )

    assert "未抽出: structured records がないため、brief を組み立てられません。" in rendered
    assert "Fallback suggestion: fallback" in rendered


def test_pending_view_dedupes_items_and_reports_missing_signals():
    results = [
        {
            "project": "alpha",
            "score": 80,
            "records": [
                {
                    "kind": "task",
                    "summary": "棚卸しする",
                    "judgements": {"is_todo": True, "is_ongoing": False, "should_review_this_week": False},
                    "blocked_reason": None,
                    "next_action": "棚卸しする",
                    "evidence": [],
                }
            ],
        },
        {
            "project": "beta",
            "score": 70,
            "analyzed_at": "2000-01-01T00:00:00+00:00",
            "payload_truncated": True,
            "records": [
                {
                    "kind": "task",
                    "summary": "棚卸しする",
                    "judgements": {"is_todo": True, "is_ongoing": False, "should_review_this_week": False},
                    "blocked_reason": None,
                    "next_action": None,
                    "evidence": [],
                }
            ],
        },
    ]

    rendered = format_shinko_results(results, view=VIEW_PENDING)
    assert "- [beta | Freshness: 2000-01-01T00:00:00+00:00 (stale) | truncated] 棚卸しする" in rendered
    assert "[alpha |" not in rendered

    empty_rendered = format_shinko_results(
        [
            {
                "project": "gamma",
                "score": 20,
                "records": [
                    {
                        "kind": "project_state",
                        "summary": "進行中",
                        "judgements": {"is_todo": False, "is_ongoing": True, "should_review_this_week": False},
                        "blocked_reason": None,
                        "next_action": None,
                        "evidence": [],
                    }
                ],
            }
        ],
        view=VIEW_PENDING,
    )
    assert "未検出: pending と判断できる項目はありません。" in empty_rendered


def test_next_actions_and_daily_views_render_cross_project_briefs():
    results = [
        {
            "project": "alpha",
            "score": 90,
            "analyzed_at": "2026-04-14T10:00:00+00:00",
            "payload_truncated": True,
            "records": [
                {
                    "kind": "next_action",
                    "summary": "担当者へ連絡する",
                    "judgements": {"is_todo": True, "is_ongoing": True, "should_review_this_week": False},
                    "blocked_reason": None,
                    "next_action": "担当者へ連絡する",
                    "evidence": [],
                }
            ],
        },
        {
            "project": "beta",
            "score": 50,
            "records": [],
            "suggestion": "fallback",
        },
    ]

    next_actions = format_shinko_results(results, view=VIEW_NEXT_ACTIONS)
    daily = format_shinko_results(results, view=VIEW_DAILY)

    assert "## 次アクション候補" in next_actions
    assert "- [alpha | Freshness: 2026-04-14T10:00:00+00:00 (stale) | truncated] 担当者へ連絡する" in next_actions
    assert "## 今日のメモ要約" in daily
    assert "### alpha" in daily
    assert "- 担当者へ連絡する" in daily
    assert "### beta" in daily
    assert "未抽出: structured records がないため今日向け summary を組み立てられません。" in daily


def test_weekly_view_uses_review_and_todo_signals():
    results = [
        {
            "project": "alpha",
            "score": 60,
            "records": [
                {
                    "kind": "project_state",
                    "summary": "週内に仕様確認が必要",
                    "judgements": {"is_todo": False, "is_ongoing": True, "should_review_this_week": True},
                    "blocked_reason": None,
                    "next_action": None,
                    "evidence": [],
                },
                {
                    "kind": "task",
                    "summary": "検証項目を整理する",
                    "judgements": {"is_todo": True, "is_ongoing": False, "should_review_this_week": False},
                    "blocked_reason": None,
                    "next_action": None,
                    "evidence": [],
                },
            ],
        }
    ]

    rendered = format_shinko_results(results, view=VIEW_WEEKLY)

    assert "## 今週の宿題候補" in rendered
    assert "- 週内に仕様確認が必要" in rendered
    assert "- 検証項目を整理する" in rendered
