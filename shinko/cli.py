import json
import re
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import click

from kuroko.application import build_shinko_context
from kuroko.collector import collect_checkpoints
from kuroko_core.config import load_config
from kuroko_core.history import HistorySummarizer, get_repo_root
from shinko.llm import LLMClient


@click.group()
@click.option('--config', default=None, help='Path to config file.')
@click.pass_context
def main(ctx, config):
    ctx.ensure_object(dict)
    cfg = load_config(config)
    ctx.obj['config'] = cfg
    ctx.obj['get_entries'] = lambda: collect_checkpoints(cfg)


@main.command()
@click.option('--n', default=10, help='Number of recent entries to show.')
@click.option('--json-output', is_flag=True, help='Output in JSON format.')
@click.pass_context
def recent(ctx, n, json_output):
    """Show recent activities."""
    entries = ctx.obj['get_entries']()[:n]
    if json_output:
        print_json(entries)
    else:
        for entry in entries:
            issue_str = f" / ISSUE-{entry['issue']}" if entry['issue'] else ""
            click.echo(f"{entry['date']} {entry['time']} [{entry['phase']}] {entry['project']}{issue_str}: {entry['act']}")


@main.command()
@click.option('--json-output', is_flag=True, help='Output in JSON format.')
@click.pass_context
def blockers(ctx, json_output):
    """Show active blockers."""
    from kuroko_core.constants import BLOCK_IGNORE

    entries = ctx.obj['get_entries']()
    blockers = [entry for entry in entries if entry['block'] and entry['block'].strip().lower() not in BLOCK_IGNORE]

    if json_output:
        print_json(blockers)
    else:
        if not blockers:
            click.echo("No active blockers found.")
            return
        for entry in blockers:
            click.echo(f"BLOCK: {entry['block']} @ {entry['project']} ({entry['date']} {entry['time']})")


@main.command()
@click.option('--json-output', is_flag=True, help='Output in JSON format.')
@click.pass_context
def status(ctx, json_output):
    """Show latest activity for each project."""
    latest_by_proj = {}
    for entry in ctx.obj['get_entries']():
        if entry['project'] not in latest_by_proj:
            latest_by_proj[entry['project']] = entry

    entries = list(latest_by_proj.values())
    if json_output:
        print_json(entries)
    else:
        for entry in entries:
            click.echo(f"{entry['project']}: {entry['date']} {entry['time']} [{entry['phase']}] {entry['act']}")


@main.command()
@click.option('--n', default=5, help='Number of items to show per category.')
@click.option('--json-output', is_flag=True, help='Output in JSON format.')
@click.pass_context
def worklist(ctx, n, json_output):
    """Show open PRs and Issues from GitHub."""
    from kuroko.worklist import fetch_worklist, format_total_count

    cfg = ctx.obj['config']
    results = []

    for project in cfg.projects:
        if not project.repo:
            continue
        try:
            data = fetch_worklist(project.repo, limit=n)
            data["project"] = project.name
            results.append(data)
        except RuntimeError as exc:
            click.echo(f"Warning: {exc}", err=True)

    if json_output:
        print_json(results)
    else:
        if not results:
            click.echo("No worklist items found (ensure 'repo' is set in kuroko.config.yaml).")
            return

        for result in results:
            pr_total_str = format_total_count(result.get("total_pull_requests", -1))
            issue_total_str = format_total_count(result.get("total_issues", -1))

            click.echo(f"## Project: {result['project']} ({result['repo']})")
            click.echo(f"Summary: {pr_total_str} Open PRs, {issue_total_str} Open Issues\n")

            click.echo("### Open Pull Requests")
            if not result["pull_requests"]:
                click.echo("No open PRs.")
            else:
                for pr in result["pull_requests"]:
                    click.echo(f"- #{pr['id']} {pr['title']} ({pr['url']})")

            click.echo("\n### Open Issues")
            if not result["issues"]:
                click.echo("No open issues.")
            else:
                for issue in result["issues"]:
                    click.echo(f"- #{issue['id']} {issue['title']} ({issue['url']})")
            click.echo("\n" + "-" * 40 + "\n")


def extract_project_contexts(report_text: str) -> dict:
    """Extract project-specific sections from a rendered report as a fallback."""
    contexts = {}

    status_match = re.search(r'## Status\n(.*?)(?:\n##|$)', report_text, re.DOTALL)
    status_rows = []
    if status_match:
        table_text = status_match.group(1).strip()
        rows = table_text.split('\n')
        if len(rows) > 2:
            status_rows = rows[2:]

    worklist_match = re.search(r'## Worklist\n(.*?)(?:\n##|$)', report_text, re.DOTALL)
    worklist_sections = {}
    if worklist_match:
        wl_text = worklist_match.group(1).strip()
        sections = re.split(r'\n### ', '\n' + wl_text)
        for section in sections:
            section = section.strip()
            if not section:
                continue
            header = section.split('\n')[0]
            proj_name = header.split(' ')[0].strip()
            worklist_sections[proj_name] = section

    all_projects = set(worklist_sections.keys())
    for row in status_rows:
        cells = [cell.strip() for cell in row.split('|')]
        if len(cells) >= 5:
            proj = cells[4]
            if proj and proj != '-' and proj != 'project':
                all_projects.add(proj)

    for proj in all_projects:
        proj_status = [row for row in status_rows if f'| {proj} |' in row]
        contexts[proj] = {
            "status": "\n".join(proj_status),
            "worklist": worklist_sections.get(proj, "(No worklist info)"),
        }

    return contexts


@main.command()
@click.option('--input-file', default=None, help='Markdown report file for insight context (fallback).')
@click.option('--json-output', is_flag=True, help='Output in JSON format.')
@click.option('--mode', type=click.Choice(['normal', 'rescue', 'deep']), default='normal', help='Suggestion mode (temperature).')
@click.option('--project', default=None, help='Target project to focus on.')
@click.option('--lang', default=None, help='Language for the LLM response.')
@click.pass_context
def insight(ctx, input_file, json_output, mode, project, lang):
    """Generate prioritized insights using DB/report context or live project data."""
    cfg = ctx.obj['config']
    lang = lang or cfg.llm.language

    sanitized_project = None
    if project:
        sanitized_project = re.sub(r'[^a-zA-Z0-9_\-]', '', project)[:64] or None

    contexts = {}
    report_path = Path(input_file) if input_file else Path("report.md")

    if sanitized_project:
        try:
            shared_context = build_shinko_context(cfg, report_path, project=sanitized_project, max_chars=20000)
        except FileNotFoundError:
            shared_context = None
        if shared_context:
            contexts[sanitized_project] = {
                "status": shared_context,
                "worklist": "(Shared context)",
            }

    if not contexts and input_file:
        if report_path.exists():
            with open(report_path, 'r', encoding='utf-8') as f:
                report_text = f.read()
            contexts = extract_project_contexts(report_text)
            if not contexts:
                contexts["overall"] = {
                    "status": report_text,
                    "worklist": "(No worklist info)",
                }

    if not contexts:
        all_entries = collect_checkpoints(cfg)
        for proj_cfg in cfg.projects:
            if sanitized_project and proj_cfg.name != sanitized_project:
                continue

            proj_entries = [entry for entry in all_entries if entry['project'] == proj_cfg.name]
            status_summary = "\n".join([f"{entry['date']} [{entry['phase']}] {entry['act']}" for entry in proj_entries[:3]])

            worklist_data = "(No worklist info)"
            if proj_cfg.repo:
                try:
                    from kuroko.worklist import fetch_worklist
                    worklist = fetch_worklist(proj_cfg.repo, limit=5)
                    pr_list = [f"PR #{pr['id']}: {pr['title']}" for pr in worklist['pull_requests']]
                    issue_list = [f"ISSUE #{issue['id']}: {issue['title']}" for issue in worklist['issues']]
                    worklist_data = f"Open PRs: {', '.join(pr_list)}\nOpen Issues: {', '.join(issue_list)}"
                except Exception:
                    pass

            contexts[proj_cfg.name] = {
                "status": status_summary or "(No recent activity)",
                "worklist": worklist_data,
            }

    target_projects = [sanitized_project] if sanitized_project else list(contexts.keys())
    results = []

    if mode == 'rescue':
        system_prompt = (
            "You are an expert developer assistant focused on project maintenance and rescue. "
            "Based on the project status report, suggest a step to resolve stale tasks (stale), "
            "dependencies, or blockers to keep the project healthy. "
        )
    elif mode == 'deep':
        system_prompt = (
            "You are an expert developer assistant focused on deep implementation and architectural design. "
            "Based on the project status report, suggest a significant or complex next step that "
            "requires a block of focused time, such as heavy implementation or design work. "
        )
    else:
        system_prompt = (
            "You are an expert developer assistant. Based on the project status report, "
            "suggest the single most important next step to take. Focus on the most immediate "
            "and natural next action. "
        )

    if sanitized_project:
        system_prompt += f"Focus your suggestion on project '{sanitized_project}'. "

    if lang.lower() == "japanese":
        system_prompt += "必ず日本語で回答してください。可能ならJSONのみで `suggestion` と `score` を返してください。"
    else:
        system_prompt += (
            f"Answer in {lang}. "
            "Answer in JSON when possible using keys `suggestion` and `score`."
        )

    summarizer = HistorySummarizer(cfg.history_path)
    secretary_insight = summarizer.get_summary(get_repo_root(None))
    if secretary_insight:
        system_prompt = f"{secretary_insight}\n\n{system_prompt}"

    client = LLMClient(cfg.llm)

    def analyze_project(proj):
        ctx_data = contexts[proj]
        if lang.lower() == "japanese":
            user_content = f"現在の進捗レポート:\n\nProject: {proj}\n\nStatus (Recent):\n{ctx_data['status']}\n\nWorklist:\n{ctx_data['worklist']}"
        else:
            user_content = f"Current status report:\n\nProject: {proj}\n\nStatus (Recent):\n{ctx_data['status']}\n\nWorklist:\n{ctx_data['worklist']}"
        try:
            response = client.chat_completion(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ]
            )
            clean_res = re.sub(r'^```json\s*|\s*```$', '', response.strip(), flags=re.MULTILINE)
            try:
                data = json.loads(clean_res)
                suggestion = data.get("suggestion", "No suggestion")
                score = data.get("score", 0)
            except json.JSONDecodeError:
                suggestion = response
                score = 0
            return {"project": proj, "suggestion": suggestion, "score": score}
        except Exception as exc:
            traceback.print_exc(file=sys.stderr)
            return {"project": proj, "suggestion": f"Error: {exc}", "score": 0}

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(analyze_project, proj) for proj in sorted(target_projects) if proj in contexts]
        results = [future.result() for future in futures]

    results.sort(key=lambda item: item['score'], reverse=True)

    if json_output:
        click.echo(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    else:
        title = "### 推奨される次の一手 (優先順位順)\n" if lang.lower() == "japanese" else "### Recommended Next Steps\n"
        output = [title]
        for item in results:
            output.append(f"#### {item['project']} (Score: {item['score']})\n{item['suggestion']}\n")
        click.echo("\n".join(output))


def print_json(entries):
    output = {
        "generated_at": datetime.now().isoformat(),
        "items": entries,
    }
    click.echo(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
