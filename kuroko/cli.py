import click
import json
import sys
from pathlib import Path
from datetime import datetime
from kuroko.config import load_config
from kuroko.collector import collect_checkpoints
from kuroko.reporter import generate_report

@click.group()
@click.option('--config', default=None, help='Path to config file.')
@click.pass_context
def main(ctx, config):
    ctx.ensure_object(dict)
    cfg = load_config(config)
    
    if not cfg.projects and config is None:
        click.echo("Warning: No projects defined. Please create kuroko.config.yaml.", err=True)
        
    ctx.obj['config'] = cfg
    # Lazy evaluation for other commands to prevent double parsing
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
            print(f"{e['date']} {e['time']} [{e['phase']}] {e['project']}{issue_str}: {e['act']}")

@main.command()
@click.option('--json-output', is_flag=True, help='Output in JSON format.')
@click.pass_context
def blockers(ctx, json_output):
    """Show active blockers."""
    from kuroko.constants import BLOCK_IGNORE
    entries = ctx.obj['get_entries']()
    blockers = [e for e in entries if e['block'] and e['block'].strip().lower() not in BLOCK_IGNORE]
    
    if json_output:
        print_json(blockers)
    else:
        if not blockers:
            click.echo("No active blockers found.")
            return
        for e in blockers:
            print(f"BLOCK: {e['block']} @ {e['project']} ({e['date']} {e['time']})")

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
            print(f"{e['project']}: {e['date']} {e['time']} [{e['phase']}] {e['act']}")

@main.command()
@click.argument('output_path', type=click.Path(dir_okay=False))
@click.option('--per-project-files', type=int, default=None, help='Max number of checkpoint files read per project.')
@click.option('--since', help='Include entries on/after the date (YYYY-MM-DD).')
@click.option('--until', help='Include entries on/before the date (YYYY-MM-DD).')
@click.option('--project', multiple=True, help='Filter to one project name (can be repeated).')
@click.option('--issue', help='Filter to one issue id (e.g., 153).')
@click.option('--include-path', is_flag=True, help='Include file_path in details and Sources section.')
@click.option('--include-evidence/--no-include-evidence', default=True, help='Include evd field in details sections.')
@click.option('--collapse-details/--no-collapse-details', default=True, help='Wrap per-item detail blocks in <details>.')
@click.option('--title', default='Kuroko Report', help='Title at the top of the report.')
@click.pass_context
def report(ctx, output_path, per_project_files, since, until, project, issue, include_path, include_evidence, collapse_details, title):
    """Generate a human-readable Markdown report."""
    cfg = ctx.obj['config']

    def validate_date(date_str, param_name):
        if not date_str:
            return None
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            raise click.ClickException(f"Error: Invalid date format for {param_name}. Must be YYYY-MM-DD.")

    since = validate_date(since, '--since')
    until = validate_date(until, '--until')

    clean_issue = None
    if issue:
        clean_issue = issue.replace("ISSUE-", "").replace("#", "")

    projects_list = list(project) if project else None
    actual_per_project = per_project_files if per_project_files is not None else cfg.defaults.per_project_files

    entries = collect_checkpoints(
        config=cfg,
        since=since,
        until=until,
        projects=projects_list,
        issue=clean_issue,
        per_project_files=actual_per_project
    )

    filters = {}
    if projects_list:
        filters['project'] = ",".join(projects_list)
    if clean_issue:
        filters['issue'] = clean_issue
    if since:
        filters['since'] = since
    if until:
        filters['until'] = until

    report_content = generate_report(
        entries=entries,
        title=title,
        per_project_files=actual_per_project,
        filters=filters,
        include_path=include_path,
        include_evidence=include_evidence,
        collapse_details=collapse_details
    )

    out_path = Path(output_path)
    if out_path.parent != Path(".") and not out_path.parent.exists():
        raise click.ClickException(f"Error: Directory '{out_path.parent}' does not exist.")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    click.echo(f"Report successfully generated at {out_path}")

def print_json(entries):
    output = {
        "generated_at": datetime.now().isoformat(),
        "items": entries
    }
    click.echo(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
