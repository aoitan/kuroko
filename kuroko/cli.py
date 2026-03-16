import click
import json
import sys
from pathlib import Path
from datetime import datetime
from kuroko_core.config import load_config
from kuroko_core.db import init_db
from kuroko.collector import collect_checkpoints, save_checkpoints_to_db
from kuroko.memo_collector import collect_memo

@click.group()
@click.option('--config', default=None, help='Path to config file.')
@click.pass_context
def main(ctx, config):
    ctx.ensure_object(dict)
    cfg = load_config(config)
    
    if not cfg.projects and config is None:
        click.echo("Warning: No projects defined. Please create kuroko.config.yaml.", err=True)
        
    ctx.obj['config'] = cfg

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

def print_json(entries):
    output = {
        "generated_at": datetime.now().isoformat(),
        "items": entries
    }
    click.echo(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
