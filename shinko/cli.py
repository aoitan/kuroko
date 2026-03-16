import click
import json
import sys
from pathlib import Path
from datetime import datetime
from kuroko_core.config import load_config
from kuroko_core.history import HistorySummarizer, get_repo_root
from kuroko.collector import collect_checkpoints
from shinko.llm import LLMClient

@click.group()
@click.option('--config', default=None, help='Path to config file.')
@click.pass_context
def main(ctx, config):
    ctx.ensure_object(dict)
    cfg = load_config(config)
    ctx.obj['config'] = cfg
    # Maintain lazy evaluation for checkpoint collection
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
        for e in entries:
            issue_str = f" / ISSUE-{e['issue']}" if e['issue'] else ""
            click.echo(f"{e['date']} {e['time']} [{e['phase']}] {e['project']}{issue_str}: {e['act']}")

@main.command()
@click.option('--json-output', is_flag=True, help='Output in JSON format.')
@click.pass_context
def blockers(ctx, json_output):
    """Show active blockers."""
    from kuroko_core.constants import BLOCK_IGNORE
    entries = ctx.obj['get_entries']()
    blockers = [e for e in entries if e['block'] and e['block'].strip().lower() not in BLOCK_IGNORE]
    
    if json_output:
        print_json(blockers)
    else:
        if not blockers:
            click.echo("No active blockers found.")
            return
        for e in blockers:
            click.echo(f"BLOCK: {e['block']} @ {e['project']} ({e['date']} {e['time']})")

@main.command()
@click.option('--json-output', is_flag=True, help='Output in JSON format.')
@click.pass_context
def status(ctx, json_output):
    """Show latest activity for each project."""
    latest_by_proj = {}
    entries = ctx.obj['get_entries']()
    for e in entries:
        if e['project'] not in latest_by_proj:
            latest_by_proj[e['project']] = e
            
    entries = list(latest_by_proj.values())
    if json_output:
        print_json(entries)
    else:
        for e in entries:
            click.echo(f"{e['project']}: {e['date']} {e['time']} [{e['phase']}] {e['act']}")

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
        except RuntimeError as e:
            click.echo(f"Warning: {e}", err=True)

    if json_output:
        print_json(results)
    else:
        if not results:
            click.echo("No worklist items found (ensure 'repo' is set in kuroko.config.yaml).")
            return

        for res in results:
            pr_total_str = format_total_count(res.get("total_pull_requests", -1))
            issue_total_str = format_total_count(res.get("total_issues", -1))
            
            click.echo(f"## Project: {res['project']} ({res['repo']})")
            click.echo(f"Summary: {pr_total_str} Open PRs, {issue_total_str} Open Issues\n")
            
            click.echo("### Open Pull Requests")
            if not res["pull_requests"]:
                click.echo("No open PRs.")
            else:
                for pr in res["pull_requests"]:
                    click.echo(f"- #{pr['id']} {pr['title']} ({pr['url']})")
            
            click.echo("\n### Open Issues")
            if not res["issues"]:
                click.echo("No open issues.")
            else:
                for issue in res["issues"]:
                    click.echo(f"- #{issue['id']} {issue['title']} ({issue['url']})")
            click.echo("\n" + "-" * 40 + "\n")

@main.command()
@click.option('--input-file', default='report.md', help='Markdown report file for insight context.')
@click.option('--json-output', is_flag=True, help='Output in JSON format.')
@click.option('--mode', type=click.Choice(['normal', 'rescue', 'deep']), default='normal', help='Suggestion mode (temperature).')
@click.option('--project', default=None, help='Target project to focus on.')
@click.pass_context
def insight(ctx, input_file, json_output, mode, project):
    """Generate progress management insights using LLM."""
    cfg = ctx.obj['config']
    report_path = Path(input_file)
    if not report_path.exists():
        raise click.ClickException(f"Report file not found: {report_path}")

    with open(report_path, 'r', encoding='utf-8') as f:
        report_text = f.read()
    
    # Limit context size
    max_context_chars = 20000
    if len(report_text) > max_context_chars:
        report_text = report_text[:max_context_chars] + "\n\n(Truncated for LLM context...)"

    # Define prompts based on mode
    if mode == 'rescue':
        system_prompt = (
            "You are an expert developer assistant focused on project maintenance and rescue. "
            "Based on the project status report, suggest a step to resolve stale tasks (stale), "
            "dependencies, or blockers to keep the project healthy. Answer in Japanese."
        )
    elif mode == 'deep':
        system_prompt = (
            "You are an expert developer assistant focused on deep implementation and architectural design. "
            "Based on the project status report, suggest a significant or complex next step that "
            "requires a block of focused time, such as heavy implementation or design work. Answer in Japanese."
        )
    else:  # normal
        system_prompt = (
            "You are an expert developer assistant. Based on the project status report, "
            "suggest the single most important next step to take. Focus on the most immediate "
            "and natural next action. Answer in Japanese."
        )

    if project:
        import re
        project = re.sub(r'[^a-zA-Z0-9_\-]', '', project)[:64]
        if project:
            system_prompt += f" Focus your suggestion on project '{project}'."

    # Secretary Insight (History context)
    summarizer = HistorySummarizer(cfg.history_path)
    secretary_insight = summarizer.get_summary(get_repo_root(report_path))
    if secretary_insight:
        system_prompt = f"{secretary_insight}\n\n{system_prompt}"

    client = LLMClient(cfg.llm)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Current status report:\n\n{report_text}"}
    ]
    try:
        suggestion = client.chat_completion(messages)
    except Exception as e:
        raise click.ClickException(f"LLM request failed: {e}")

    if json_output:
        click.echo(json.dumps({"suggestion": suggestion}, ensure_ascii=False, indent=2))
    else:
        click.echo(suggestion)

def print_json(entries):
    output = {
        "generated_at": datetime.now().isoformat(),
        "items": entries
    }
    click.echo(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
