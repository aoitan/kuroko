import json
import re
from typing import Any


SCHEMA_VERSION = "shinko-insight-v1"
PROMPT_VERSION = "issue-23-v1"
VALID_KINDS = {"task", "agenda", "project_state", "blocked_reason", "next_action"}


def parse_insight_response(response_text: str, *, expected_project: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```json\s*|\s*```$", "", response_text.strip(), flags=re.MULTILINE)
    data = json.loads(cleaned)

    if not isinstance(data, dict):
        raise ValueError("Insight response must be a JSON object.")

    schema_version = data.get("schema_version", SCHEMA_VERSION)
    if schema_version != SCHEMA_VERSION:
        raise ValueError(f"Unsupported schema_version: {schema_version}")

    project = data.get("project", expected_project)
    if project != expected_project:
        raise ValueError(f"Insight project mismatch: expected {expected_project}, got {project}")

    raw_records = data.get("records")
    if not isinstance(raw_records, list) or not raw_records:
        raise ValueError("Insight response must include a non-empty records array.")

    records = [normalize_record(item) for item in raw_records]
    legacy = derive_legacy_fields(records)

    return {
        "schema_version": schema_version,
        "project": project,
        "records": records,
        "suggestion": legacy["suggestion"],
        "score": legacy["score"],
    }


def normalize_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("Each insight record must be an object.")

    kind = record.get("kind")
    if kind not in VALID_KINDS:
        raise ValueError(f"Unsupported insight kind: {kind}")

    summary = _require_text(record.get("summary"), "summary")
    confidence = float(record.get("confidence", 0))
    if confidence < 0 or confidence > 1:
        raise ValueError("confidence must be between 0 and 1.")

    raw_judgements = record.get("judgements")
    if not isinstance(raw_judgements, dict):
        raise ValueError("judgements must be an object.")

    judgements = {
        "is_todo": bool(raw_judgements.get("is_todo", False)),
        "is_ongoing": bool(raw_judgements.get("is_ongoing", False)),
        "should_review_this_week": bool(raw_judgements.get("should_review_this_week", False)),
    }

    evidence = record.get("evidence", [])
    if not isinstance(evidence, list):
        raise ValueError("evidence must be an array.")

    normalized_evidence = []
    for item in evidence:
        if not isinstance(item, dict):
            raise ValueError("Each evidence entry must be an object.")
        source_id = item.get("source_id")
        chunk_id = item.get("chunk_id")
        if source_id is None and chunk_id is None:
            raise ValueError("Evidence must include source_id or chunk_id.")
        normalized_evidence.append(
            {
                "source_id": int(source_id) if source_id is not None else None,
                "chunk_id": int(chunk_id) if chunk_id is not None else None,
                "quote_excerpt": _normalize_optional_text(item.get("quote_excerpt")),
            }
        )

    return {
        "kind": kind,
        "summary": summary,
        "judgements": judgements,
        "blocked_reason": _normalize_optional_text(record.get("blocked_reason")),
        "next_action": _normalize_optional_text(record.get("next_action")),
        "confidence": confidence,
        "evidence": normalized_evidence,
    }


def derive_legacy_fields(records: list[dict[str, Any]]) -> dict[str, Any]:
    next_steps = []
    for record in records:
        if record.get("next_action"):
            next_steps.append(record["next_action"])
            continue
        if record["kind"] == "next_action":
            next_steps.append(record["summary"])

    highlights = next_steps or [record["summary"] for record in records[:3]]
    suggestion = "\n".join(f"- {line}" for line in highlights if line).strip() or "No suggestion"
    score = int(round(max(record["confidence"] for record in records) * 100))
    return {"suggestion": suggestion, "score": score}


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Optional text fields must be strings when present.")
    normalized = value.strip()
    return normalized or None
