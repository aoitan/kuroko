from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone


VIEW_PROJECT_BRIEF = "project_brief"
VIEW_PENDING = "pending"
VIEW_NEXT_ACTIONS = "next_actions"
VIEW_DAILY = "daily"
VIEW_WEEKLY = "weekly"

SUPPORTED_VIEWS = {
    VIEW_PROJECT_BRIEF,
    VIEW_PENDING,
    VIEW_NEXT_ACTIONS,
    VIEW_DAILY,
    VIEW_WEEKLY,
}


def format_shinko_results(results: list[dict], *, view: str = VIEW_PROJECT_BRIEF) -> str:
    if view not in SUPPORTED_VIEWS:
        view = VIEW_PROJECT_BRIEF

    normalized = [_normalize_result(item) for item in results]
    if not normalized:
        return "構造化インサイトの結果はありません。"

    if view == VIEW_PENDING:
        return _format_pending_view(normalized)
    if view == VIEW_NEXT_ACTIONS:
        return _format_next_actions_view(normalized)
    if view == VIEW_DAILY:
        return _format_daily_view(normalized)
    if view == VIEW_WEEKLY:
        return _format_weekly_view(normalized)
    return _format_project_brief_view(normalized)


def _normalize_result(item: dict) -> dict:
    records = item.get("records") or []
    return {
        "project": item.get("project", "unknown"),
        "score": item.get("score", 0),
        "suggestion": item.get("suggestion", "No suggestion"),
        "records": records,
        "source_hash": item.get("source_hash"),
        "payload_truncated": bool(item.get("truncated") or item.get("payload_truncated")),
        "analyzed_at": item.get("analyzed_at"),
        "has_structured_records": bool(records),
    }


def _format_project_brief_view(results: list[dict]) -> str:
    lines = ["## 案件別ブリーフ", ""]
    for index, result in enumerate(results):
        if index:
            lines.append("---")
            lines.append("")
        lines.extend(_render_project_brief(result))
    return "\n".join(lines).strip()


def _render_project_brief(result: dict) -> list[str]:
    records = result["records"]
    lines = [f"### {result['project']}", f"- Score: {result['score']}"]
    lines.extend(_format_freshness_lines(result))
    lines.append("")

    if not result["has_structured_records"]:
        lines.append("#### Summary")
        lines.append("- 未抽出: structured records がないため、brief を組み立てられません。")
        lines.append("- Fallback suggestion: " + result["suggestion"])
        return lines

    next_actions = _collect_next_actions(records)
    cautions = _collect_cautions(records)
    summary_items = _collect_summaries(records)
    pending_items = _collect_pending(records, exclude={item["key"] for item in next_actions})
    review_items = _collect_weekly_review(records, exclude={item["key"] for item in pending_items})
    evidence_items = _collect_evidence(records)

    _append_section(lines, "Summary", summary_items, "未抽出: summary に使える structured summary がありません。")
    _append_section(lines, "Pending", pending_items, _empty_detection_message(records, predicate=_has_pending_signal, label="pending"))
    _append_section(
        lines,
        "This Week Review",
        review_items,
        _empty_detection_message(records, predicate=_has_review_signal, label="今週確認"),
    )
    _append_section(
        lines,
        "Next Actions",
        next_actions,
        _empty_detection_message(records, predicate=_has_next_action_signal, label="次アクション"),
    )
    _append_section(
        lines,
        "Caution",
        cautions,
        _empty_detection_message(records, predicate=_has_caution_signal, label="注意点"),
    )
    _append_section(lines, "Evidence", evidence_items, "根拠なし: 紐づく evidence がありません。")
    return lines


def _format_pending_view(results: list[dict]) -> str:
    groups = defaultdict(lambda: {"project_labels": [], "detail": None})
    saw_structured = False
    saw_signal = False

    for result in results:
        if not result["has_structured_records"]:
            continue
        saw_structured = True
        next_keys = {item["key"] for item in _collect_next_actions(result["records"])}
        for item in _collect_pending(result["records"], exclude=next_keys):
            saw_signal = True
            entry = groups[item["key"]]
            entry["detail"] = entry["detail"] or item["text"]
            entry["project_labels"].append(_project_label(result))

    lines = ["## Pending 一覧", "", "最新 insight の TODO 判定ベースで表示しています。", ""]
    if not saw_structured:
        lines.append("- 未抽出: structured records がないため pending を集約できません。")
        return "\n".join(lines)
    if not saw_signal:
        lines.append("- 未検出: pending と判断できる項目はありません。")
        return "\n".join(lines)

    for payload in sorted(groups.values(), key=lambda item: (",".join(sorted(set(item["project_labels"]))), item["detail"])):
        projects = ", ".join(sorted(set(payload["project_labels"])))
        lines.append(f"- [{projects}] {payload['detail']}")
    return "\n".join(lines)


def _format_next_actions_view(results: list[dict]) -> str:
    groups = defaultdict(lambda: {"project_labels": [], "detail": None})
    saw_structured = False
    saw_signal = False

    for result in results:
        if not result["has_structured_records"]:
            continue
        saw_structured = True
        for item in _collect_next_actions(result["records"]):
            saw_signal = True
            entry = groups[item["key"]]
            entry["detail"] = entry["detail"] or item["text"]
            entry["project_labels"].append(_project_label(result))

    lines = ["## 次アクション候補", "", "next_action と next_action kind を優先して集約しています。", ""]
    if not saw_structured:
        lines.append("- 未抽出: structured records がないため次アクション候補を集約できません。")
        return "\n".join(lines)
    if not saw_signal:
        lines.append("- 未検出: 次アクション候補はありません。")
        return "\n".join(lines)

    for payload in sorted(groups.values(), key=lambda item: (",".join(sorted(set(item["project_labels"]))), item["detail"])):
        projects = ", ".join(sorted(set(payload["project_labels"])))
        lines.append(f"- [{projects}] {payload['detail']}")
    return "\n".join(lines)


def _format_daily_view(results: list[dict]) -> str:
    lines = [
        "## 今日のメモ要約",
        "",
        "最新 insight ベースの簡易ビューです。厳密な当日差分ではなく、freshness 情報つきの要約を返します。",
        "",
    ]
    rendered_any = False
    for result in results:
        lines.append(f"### {result['project']}")
        lines.extend(_format_freshness_lines(result))
        if not result["has_structured_records"]:
            lines.append("- 未抽出: structured records がないため今日向け summary を組み立てられません。")
            lines.append("")
            continue
        rendered_any = True
        summaries = _collect_summaries(result["records"], limit=2)
        for item in summaries:
            lines.append(f"- {item['text']}")
        if not summaries:
            lines.append("- 未抽出: summary に使える structured summary がありません。")
        lines.append("")

    if not rendered_any:
        lines.append("入力不足のため、today view は fallback 中です。")
    return "\n".join(lines).strip()


def _format_weekly_view(results: list[dict]) -> str:
    lines = [
        "## 今週の宿題候補",
        "",
        "現行 schema では週内変化を断定せず、review flag と TODO を候補としてまとめます。",
        "",
    ]
    rendered_any = False
    for result in results:
        lines.append(f"### {result['project']}")
        lines.extend(_format_freshness_lines(result))
        if not result["has_structured_records"]:
            lines.append("- 未抽出: structured records がないため今週候補を組み立てられません。")
            lines.append("")
            continue

        candidates = _collect_weekly_review(result["records"], exclude=set())
        candidates.extend(_collect_pending(result["records"], exclude={item["key"] for item in candidates}))
        candidates = _unique_items(candidates)
        if candidates:
            rendered_any = True
            for item in candidates:
                lines.append(f"- {item['text']}")
        else:
            lines.append("- 未検出: 今週確認または TODO と判断できる項目はありません。")
        lines.append("")

    if not rendered_any:
        lines.append("入力不足のため、weekly view は安全側で候補を絞っています。")
    return "\n".join(lines).strip()


def _format_freshness_lines(result: dict) -> list[str]:
    analyzed_at = result.get("analyzed_at")
    stale_note = _stale_note(analyzed_at)
    freshness = analyzed_at or "unavailable"
    lines = [f"- Freshness: {freshness}{stale_note}"]
    source_hash = result.get("source_hash")
    if source_hash:
        lines.append(f"- Source hash: `{source_hash}`")
    else:
        lines.append("- Source hash: unavailable")
    if result.get("payload_truncated"):
        lines.append("- Warning: payload_truncated=true のため、要約元データが省略されている可能性があります。")
    return lines


def _stale_note(value: str | None) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - parsed > timedelta(days=2):
        return " (stale)"
    return ""


def _project_label(result: dict) -> str:
    freshness = result.get("analyzed_at") or "unavailable"
    flags = [f"Freshness: {freshness}{_stale_note(result.get('analyzed_at'))}"]
    if result.get("payload_truncated"):
        flags.append("truncated")
    return f"{result['project']} | {' | '.join(flags)}"


def _append_section(lines: list[str], title: str, items: list[dict], empty_message: str) -> None:
    lines.append(f"#### {title}")
    if items:
        for item in items:
            lines.append(f"- {item['text']}")
    else:
        lines.append(f"- {empty_message}")
    lines.append("")


def _collect_summaries(records: list[dict], *, limit: int = 3) -> list[dict]:
    preferred = []
    fallback = []
    for record in records:
        text = record.get("summary")
        if not text:
            continue
        item = _item(text, key=text)
        if record.get("kind") in {"project_state", "agenda", "task"}:
            preferred.append(item)
        else:
            fallback.append(item)
    merged = _unique_items(preferred + fallback)
    return merged[:limit]


def _collect_pending(records: list[dict], *, exclude: set[str]) -> list[dict]:
    items = []
    for record in records:
        if not (record.get("judgements") or {}).get("is_todo"):
            continue
        text = record.get("summary")
        if not text:
            continue
        item = _item(text, key=text)
        if item["key"] in exclude:
            continue
        items.append(item)
    return _unique_items(items)


def _collect_weekly_review(records: list[dict], *, exclude: set[str]) -> list[dict]:
    items = []
    for record in records:
        if not (record.get("judgements") or {}).get("should_review_this_week"):
            continue
        text = record.get("summary")
        if not text:
            continue
        item = _item(text, key=text)
        if item["key"] in exclude:
            continue
        items.append(item)
    return _unique_items(items)


def _collect_next_actions(records: list[dict]) -> list[dict]:
    items = []
    for record in records:
        text = record.get("next_action") or (record.get("summary") if record.get("kind") == "next_action" else None)
        if text:
            items.append(_item(text, key=text))
    return _unique_items(items)


def _collect_cautions(records: list[dict]) -> list[dict]:
    items = []
    for record in records:
        text = record.get("blocked_reason") or (record.get("summary") if record.get("kind") == "blocked_reason" else None)
        if text:
            items.append(_item(text, key=text))
    return _unique_items(items)


def _collect_evidence(records: list[dict], *, limit: int = 3) -> list[dict]:
    items = []
    for record in records:
        evidence = record.get("evidence") or []
        if not evidence:
            continue
        evidence_head = evidence[0]
        excerpt = evidence_head.get("quote_excerpt") or "quote なし"
        source_id = evidence_head.get("source_id")
        chunk_id = evidence_head.get("chunk_id")
        locator = []
        if source_id is not None:
            locator.append(f"source:{source_id}")
        if chunk_id is not None:
            locator.append(f"chunk:{chunk_id}")
        prefix = f"{record.get('summary', 'No summary')}: "
        suffix = f" ({', '.join(locator)})" if locator else ""
        items.append(_item(prefix + excerpt + suffix, key=prefix + excerpt + suffix))
    return _unique_items(items)[:limit]


def _empty_detection_message(records: list[dict], *, predicate, label: str) -> str:
    if not records:
        return f"未抽出: structured records がないため {label} を判断できません。"
    if any(predicate(record) for record in records):
        return f"未抽出: {label} の候補はありますが表示用に整形できませんでした。"
    return f"未検出: {label} と判断できる項目はありません。"


def _has_pending_signal(record: dict) -> bool:
    return bool((record.get("judgements") or {}).get("is_todo"))


def _has_review_signal(record: dict) -> bool:
    return bool((record.get("judgements") or {}).get("should_review_this_week"))


def _has_next_action_signal(record: dict) -> bool:
    return bool(record.get("next_action") or record.get("kind") == "next_action")


def _has_caution_signal(record: dict) -> bool:
    return bool(record.get("blocked_reason") or record.get("kind") == "blocked_reason")


def _item(text: str, *, key: str) -> dict:
    clean = text.strip()
    return {"text": clean, "key": _canonicalize(key)}


def _canonicalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _unique_items(items: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for item in items:
        key = item["key"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique
