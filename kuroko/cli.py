import click
import json
import sys
from datetime import datetime
from kuroko.config import load_config
from kuroko.collector import collect_checkpoints

@click.group()
@click.option('--config', default=None, help='Path to config file.')
@click.pass_context
def main(ctx, config):
    ctx.ensure_object(dict)
    cfg = load_config(config)
    
    if not cfg.projects and config is None:
        # 設定ファイルが見つからず、プロジェクトも未定義の場合
        click.echo("Warning: No projects defined. Please create kuroko.config.yaml.", err=True)
        
    ctx.obj['config'] = cfg
    ctx.obj['entries'] = collect_checkpoints(cfg)

@main.command()
@click.option('--n', default=10, help='Number of recent entries to show.')
@click.option('--json-output', is_flag=True, help='Output in JSON format.')
@click.pass_context
def recent(ctx, n, json_output):
    """Show recent activities."""
    entries = ctx.obj['entries'][:n]
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
    block_ignore = ["なし", "none", "n/a", "nothing"]
    blockers = [e for e in ctx.obj['entries'] if e['block'] and e['block'].lower() not in block_ignore]
    
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
    for e in ctx.obj['entries']:
        if e['project'] not in latest_by_proj:
            latest_by_proj[e['project']] = e
            
    entries = list(latest_by_proj.values())
    if json_output:
        print_json(entries)
    else:
        for e in entries:
            print(f"{e['project']}: {e['date']} {e['time']} [{e['phase']}] {e['act']}")

def print_json(entries):
    output = {
        "generated_at": datetime.now().isoformat(),
        "items": entries
    }
    click.echo(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
