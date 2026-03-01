---
name: kuroko-report
title: Kuroko CLI `report` Command Specification
version: 0.1
status: draft
---

# Overview

`kuroko report` is a CLI command that generates a human-readable Markdown report from collected checkpoint timelines.
The report is intended to be viewed in editors such as VSCode and optimized for quick scanning (status / blockers / recent).

# Goals

- Produce a single Markdown file that is easy to read, search, and share locally.
- Reduce “eye-sliding” by using tables, headings, and optional collapsible sections.
- Do not invent information: the report must be derived only from checkpoint entries.

# Non-Goals

- No TUI/UI rendering (handled by editors).
- No online integration (GitHub, Slack, etc.).
- No automatic summarization by LLM in this command (future extension).

# Command

## Synopsis

```bash
kuroko report <output_path> [options]
```

## Output

- Generates a Markdown file at `<output_path>`.
- Overwrites the file if it already exists (default behavior).
  - Optional future: `--no-overwrite` to fail if exists.

# Inputs

`kuroko report` uses the same data sources as the existing collector:

- Project roots are loaded from configuration.
- For each project root, checkpoint files are discovered under `checkpoint/` (configurable).
- Parsing extracts timeline entries with fields:
  - `date`, `time`, `phase`, `project`, `issue`, `act`, `evd`, `block`, `file_path`

# Options

## Selection & Limits

- `--per-project-files <N>`
  - Default: `5`
  - Max number of checkpoint files read per project (newest first).

- `--since <YYYY-MM-DD>`
  - Include entries on/after the date (optional filter).

- `--until <YYYY-MM-DD>`
  - Include entries on/before the date (optional filter).

- `--project <name>`
  - Filter to one project name (can be repeated).

- `--issue <id>`
  - Filter to one issue id (e.g., `153`). Matches `ISSUE-153` and `#153` style in output.

## Display Controls (Markdown)

- `--include-path`
  - Include `file_path` in blocker details and/or in a “Sources” section.
  - Default: off.

- `--include-evidence`
  - Include `evd` field in details sections.
  - Default: on (recommended), but can be toggled if noise.

- `--collapse-details`
  - Wrap per-item detail blocks (act/evd/path) in `<details>` sections.
  - Default: on for blockers, off for status/recent.

## Output Metadata

- `--title <string>`
  - Title at the top of the report.
  - Default: `Kuroko Report`

# Report Structure (Markdown)

The report MUST follow this structure, in order:

1. Header
2. Status
3. Blockers
4. Recent
5. (Optional) Sources

## 1) Header

Contains report metadata:

- Title (H1)
- Generated timestamp
- Configuration summary (optional, minimal)
- Applied filters (if any)

Example:

```md
# Kuroko Report

- generated_at: 2026-02-28T15:58:59+09:00
- per_project_files: 5
- filters: project=*, issue=*, since=*, until=*
```

## 2) Status Section

Purpose: show the latest entry per project (after filters).

Format: Markdown table.

Columns (fixed order):

| date | time | phase | project | issue | act |
|---|---:|---|---|---:|---|

Rules:
- `phase` may be shortened for readability:
  - planning→plan, coding→code, review→rev, fix→fix, closing→done
- `issue` is `-` if absent, else `#<id>`
- `act` is plain text; do not force-wrap
- If a project has no entries, it is omitted.

## 3) Blockers Section

Purpose: list entries where `block` is present and not equivalent to “none”.

Block equivalence (case-insensitive trim match):
- `なし`, `none`, `n/a`, `na`, `-`

Format: bulleted list, newest first.

Each item headline MUST be a single line with emphasized blocker text:

- **[project issue | date time | phase] <block>**

Then optional details:

- act
- evd (if `--include-evidence`)
- file_path (if `--include-path`)

Details rendering:
- If `--collapse-details` is enabled, wrap details in `<details><summary>details</summary> ... </details>`.

## 4) Recent Section

Purpose: show a chronological slice across all projects.

Format:
- Group by date (descending).
- Under each date, list entries by time (descending).

Line format:

- `HH:MM <phase> <project> <issue> <act>`

Rules:
- `issue` is omitted or shown as `#<id>` (consistent within report).
- Do not include `block` here (blockers already have dedicated section).

## 5) Sources Section (Optional)

Included only if `--include-path` is enabled.

Purpose: show where entries came from.

Format: list of unique checkpoint file paths (or relative paths if implementable).

# Sorting Rules

- Primary sort key: `date` (descending)
- Secondary sort key: `time` (descending)
- Tertiary sort key: `project` (ascending) for stability

For Status:
- Pick the latest entry per `project` after filters.

# Error Handling

- If `<output_path>` directory does not exist: return non-zero and print an actionable error.
- If no entries are found after filtering:
  - Still create a report with header and an explicit “No entries found” note in each section.

# Security & Privacy Considerations

- The report may contain local file paths and command logs (`evd`).
- Default behavior should avoid emitting absolute paths unless explicitly requested (`--include-path`).
- Intended for local use; do not auto-publish or auto-commit reports.

# Example Output (Skeleton)

```md
# Kuroko Report
- generated_at: 2026-02-28T15:58:59+09:00
- per_project_files: 5

## Status
| date | time | phase | project | issue | act |
|---|---:|---|---|---:|---|
| 2026-02-28 | 17:00 | done | kuroko | - | READMEへの案内を追加 |
| 2026-02-28 | 04:05 | done | multi-llm-chat | #153 | 自動保存失敗の非致命化と警告統一… |

## Blockers
- **[kuroko #1 | 2026-02-28 11:30 | code] 依存関係の解決に少し手間取った**
  <details><summary>details</summary>

  - act: parserとcollectorを実装
  - evd: `uv run pytest`

  </details>

## Recent
### 2026-02-28
- 17:00 done kuroko - READMEへの案内を追加
- 16:50 code kuroko - 検索範囲を深さ無制限に変更…

### 2026-02-24
- 05:45 done project-analyzer-mcp #2 Issue #2 全工程完了

## Sources
- /Users/.../checkpoint/2026-02-28__kuroko__misc.md
- /Users/.../checkpoint/2026-02-28__kuroko__ISSUE-1.md
```
