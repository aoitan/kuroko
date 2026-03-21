import click
import json
from pathlib import Path
from datetime import datetime

from kuroko.application import render_report_to_path
from kuroko.collector import collect_checkpoints, save_checkpoints_to_db
from kuroko.memo_collector import collect_memo
from kuroko_core.config import load_config
from kuroko_core.db import init_db


@click.group()
@click.option('--config', default=None, help='Path to config file.')
@click.pass_context
def main(ctx, config):
    ctx.ensure_object(dict)
    cfg = load_config(config)

    if not cfg.projects and config is None:
        click.echo("Warning: No projects defined. Please create kuroko.config.yaml.", err=True)

    ctx.obj['config'] = cfg
    ctx.obj['config_path'] = config


@main.group()
def collect():
    """Collect data from projects."""
    pass


@collect.command()
@click.pass_context
def memo(ctx):
    """Collect memo.md files from projects."""
    cfg = ctx.obj['config']
    db_conn = init_db(cfg.db_path)

    total_new = 0
    total_updated = 0

    for project in cfg.projects:
        new_count, updated_count = collect_memo(project, db_conn)
        total_new += new_count
        total_updated += updated_count

    db_conn.close()
    click.echo(f"Imported {total_new} new memos, Updated {total_updated} existing memos.")


@collect.command()
@click.pass_context
def checkpoints(ctx):
    """Collect checkpoint files from projects and save to DB."""
    cfg = ctx.obj['config']
    db_conn = init_db(cfg.db_path)

    entries = collect_checkpoints(cfg)
    save_checkpoints_to_db(entries, db_conn)

    db_conn.close()
    click.echo(f"Successfully collected and indexed {len(entries)} checkpoint entries to DB.")


@main.command()
@click.argument('output_path', type=click.Path(dir_okay=False))
@click.option('--per-project-files', type=int, default=None, help='Max number of checkpoint files read per project.')
@click.option('--since', help='Include entries on/after the date (YYYY-MM-DD).')
@click.option('--until', help='Include entries on/before the date (YYYY-MM-DD).')
@click.option('--project', multiple=True, help='Filter to one project name (can be repeated).')
@click.option('--issue', help='Filter to one issue id (e.g., 153).')
@click.option('--include-path', is_flag=True, help='Include file_path in details and Sources section.')
@click.option('--include-evidence/--no-include-evidence', default=True, help='Include evd field in details sections.')
@click.option('--include-worklist', is_flag=True, help='Include open PRs and Issues from GitHub in the report.')
@click.option('--collapse-details/--no-collapse-details', default=True, help='Wrap per-item detail blocks in <details>.')
@click.option('--title', default='Kuroko Report', help='Title at the top of the report.')
@click.pass_context
def report(ctx, output_path, per_project_files, since, until, project, issue, include_path, include_evidence, include_worklist, collapse_details, title):
    """Generate a human-readable Markdown report."""
    try:
        render_report_to_path(
            output_path=Path(output_path),
            config_path=ctx.obj.get('config_path'),
            per_project_files=per_project_files,
            since=since,
            until=until,
            project=project,
            issue=issue,
            include_path=include_path,
            include_evidence=include_evidence,
            include_worklist=include_worklist,
            collapse_details=collapse_details,
            title=title,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Report successfully generated at {output_path}")


def print_json(entries):
    output = {
        "generated_at": datetime.now().isoformat(),
        "items": entries,
    }
    click.echo(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
