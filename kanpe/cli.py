import shlex
import secrets
import socketserver
import subprocess
import webbrowser
import json
import sys
import os
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime

import click
import bleach
from markdown import markdown
from kuroko_core.config import load_config
from kuroko_core.history import HistoryLogger, get_repo_root
from kuroko.collector import collect_checkpoints
from kuroko.reporter import generate_report

HTML_TEMPLATE = """<!doctype html>
<html lang="ja">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>kanpe report</title>
    <style>
      body {{ max-width: 900px; margin: 2rem auto; padding: 0 1rem; line-height: 1.7; position: relative; }}
      pre {{ overflow-x: auto; }}
      code {{ white-space: pre-wrap; }}
      table {{ border-collapse: collapse; }}
      th, td {{ padding: 0.4rem 0.6rem; border: 1px solid #ccc; }}
      .header-actions {{ position: sticky; top: 0; background: #fff; padding: 1rem 0; border-bottom: 1px solid #eee; margin-bottom: 1rem; display: flex; justify-content: flex-end; z-index: 100; }}
      .btn {{ padding: 0.5rem 1rem; border: 1px solid #007bff; background: #007bff; color: #fff; border-radius: 4px; cursor: pointer; text-decoration: none; font-size: 0.9rem; }}
      .btn:hover {{ background: #0056b3; }}
      .btn:active {{ background: #004085; }}
      .btn.loading {{ opacity: 0.6; pointer-events: none; }}
    </style>
  </head>
  <body>
    <div class="header-actions">
      <div style="margin-right: 1rem; display: flex; align-items: center;">
        <label for="project-select" style="font-size: 0.85rem; margin-right: 0.5rem; color: #666;">対象:</label>
        <select id="project-select" style="padding: 0.4rem; border-radius: 4px; border: 1px solid #ccc; font-size: 0.9rem;">
          <option value="">(全体)</option>
        </select>
      </div>
      <button id="suggest-btn-normal" class="btn" style="background: #28a745; border-color: #28a745; margin-right: 0.5rem;" onclick="getSuggestion('normal')">🚀 通常</button>
      <button id="suggest-btn-rescue" class="btn" style="background: #ffc107; border-color: #ffc107; color: #000; margin-right: 0.5rem;" onclick="getSuggestion('rescue')">🧹 保守救済</button>
      <button id="suggest-btn-deep" class="btn" style="background: #007bff; border-color: #007bff; margin-right: 0.5rem;" onclick="getSuggestion('deep')">🔍 深掘り</button>
      <form action="/refresh" method="post" style="display: inline;">
        <input type="hidden" name="nonce" value="{nonce}">
        <button type="submit" id="refresh-btn" class="btn" style="background: #6c757d; border-color: #6c757d;" onclick="this.classList.add('loading'); this.innerText='Refreshing...';">Refresh & Reload</button>
      </form>
    </div>
    <div id="suggestion-box" style="display: none; background: #f8f9fa; border: 1px solid #ddd; padding: 1rem; margin-bottom: 1rem; border-radius: 4px;">
      <strong>LLMの提案:</strong>
      <div id="suggestion-content" style="white-space: pre-wrap; margin-top: 0.5rem;"></div>
    </div>
    <div id="report-content">
      {content}
    </div>
    <script>
      // Initialize project select from Status table
      (function() {{
        const projects = new Set();
        // Assume Status table is the first table
        const table = document.querySelector('#report-content table');
        if (table) {{
          const rows = table.querySelectorAll('tbody tr');
          rows.forEach(row => {{
            const cells = row.querySelectorAll('td');
            if (cells.length >= 4) {{
              const project = cells[3].innerText.trim();
              if (project && project !== '-') {{
                projects.add(project);
              }}
            }}
          }});
        }}
        const select = document.getElementById('project-select');
        Array.from(projects).sort().forEach(project => {{
          const option = document.createElement('option');
          option.value = project;
          option.innerText = project;
          select.appendChild(option);
        }});
      }})();

      async function getSuggestion(mode) {{
        const btns = [
          document.getElementById('suggest-btn-normal'),
          document.getElementById('suggest-btn-rescue'),
          document.getElementById('suggest-btn-deep')
        ];
        const box = document.getElementById('suggestion-box');
        const content = document.getElementById('suggestion-content');
        const project = document.getElementById('project-select').value;
        
        btns.forEach(b => b.classList.add('loading'));
        box.style.display = 'block';
        content.innerText = 'LLMに問い合わせています... (' + mode + (project ? ' / ' + project : '') + ')';
        
        try {{
          const response = await fetch('/suggest', {{
            method: 'POST',
            body: new URLSearchParams({{ 
              'nonce': '{nonce}',
              'mode': mode,
              'project': project
            }})
          }});
          if (response.ok) {{
            const html = await response.text();
            content.innerHTML = html;
          }} else {{
            const errorText = await response.text();
            content.innerText = 'エラーが発生しました: ' + errorText;
          }}
        }} catch (e) {{
          content.innerText = '通信エラー: ' + e;
        }} finally {{
          btns.forEach(b => b.classList.remove('loading'));
        }}
      }}
    </script>
  </body>
</html>
"""

class ReusableTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

def clean_html(html: str) -> str:
    allowed_tags = list(bleach.ALLOWED_TAGS) + [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
        'p', 'br', 'hr', 'pre', 'code', 
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'details', 'summary', 'strong', 'em', 'ul', 'ol', 'li'
    ]
    allowed_attrs = bleach.ALLOWED_ATTRIBUTES.copy()
    allowed_attrs['a'] = ['href', 'title']
    allowed_attrs['th'] = ['style', 'align']
    allowed_attrs['td'] = ['style', 'align']
    
    from bleach.css_sanitizer import CSSSanitizer
    css_sanitizer = CSSSanitizer(allowed_css_properties=['text-align'])
    
    return bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs, css_sanitizer=css_sanitizer)

def render_markdown_to_html(markdown_text: str, nonce: str) -> str:
    content_raw = markdown(markdown_text, extensions=["extra", "md_in_html"])
    content = clean_html(content_raw)
    return HTML_TEMPLATE.format(content=content, nonce=nonce)

def refresh_report(report_path: Path, kanpe_cmd: str, report_args: str, include_worklist: bool = False) -> None:
    auto_include_worklist = include_worklist
    if not auto_include_worklist and report_path.exists():
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                if "## Worklist" in f.read():
                    auto_include_worklist = True
        except Exception:
            pass

    args = shlex.split(kanpe_cmd, posix=(sys.platform != "win32"))
    args.extend(["report", str(report_path)])
    
    if auto_include_worklist:
        args.append("--include-worklist")
        
    if report_args:
        args.extend(shlex.split(report_args, posix=(sys.platform != "win32")))

    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise click.ClickException(f"failed to run {' '.join(args)}: {stderr}")

def invoke_shinko(shinko_cmd: str, report_path: Path, config: str = None, mode: str = None, project: str = None, timeout: int = 60) -> str:
    if shinko_cmd == "shinko":
        cmd = [sys.executable, "-m", "shinko.cli", "insight", "--input-file", str(report_path), "--json-output"]
    else:
        cmd = shlex.split(shinko_cmd, posix=(sys.platform != "win32"))
        cmd.extend(["insight", "--input-file", str(report_path), "--json-output"])

    if config:
        cmd.extend(["--config", str(config)])
    if mode:
        cmd.extend(["--mode", mode])
    if project:
        cmd.extend(["--project", project])
        
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise RuntimeError(f"shinko command not found: '{cmd[0]}'.")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"shinko command timed out.")

    if result.returncode != 0:
        raise RuntimeError(f"shinko command failed (exit {result.returncode})")
        
    try:
        output_data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse shinko output as JSON: {e}")
        
    return output_data.get("suggestion", "")

@click.group()
@click.option('--config', default=None, help='Path to config file.')
@click.pass_context
def main(ctx, config):
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config

@main.command()
@click.argument('output_path', type=click.Path(dir_okay=False))
@click.option('--per-project-files', type=int, default=None, help='Max number of checkpoint files read per project.')
@click.option('--since', help='Include entries on/after the date (YYYY-MM-DD).')
@click.option('--until', help='Include entries on/before the date (YYYY-MM-DD).')
@click.option('--project', multiple=True, help='Filter to one project name.')
@click.option('--issue', help='Filter to one issue id.')
@click.option('--include-path', is_flag=True, help='Include file_path.')
@click.option('--include-evidence/--no-include-evidence', default=True, help='Include evd field.')
@click.option('--include-worklist', is_flag=True, help='Include open PRs and Issues.')
@click.option('--collapse-details/--no-collapse-details', default=True, help='Wrap in <details>.')
@click.option('--title', default='Kuroko Report', help='Title of the report.')
@click.pass_context
def report(ctx, output_path, per_project_files, since, until, project, issue, include_path, include_evidence, include_worklist, collapse_details, title):
    """Generate a human-readable Markdown report."""
    cfg = load_config(ctx.obj['config_path'])

    def validate_date(date_str, param_name):
        if not date_str: return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            raise click.ClickException(f"Error: Invalid date format for {param_name}.")

    since = validate_date(since, '--since')
    until = validate_date(until, '--until')
    clean_issue = issue.replace("ISSUE-", "").replace("#", "") if issue else None
    projects_list = list(project) if project else None
    actual_per_project = per_project_files if per_project_files is not None else cfg.defaults.per_project_files

    entries = collect_checkpoints(config=cfg, since=since, until=until, projects=projects_list, issue=clean_issue, per_project_files=actual_per_project)

    worklists = []
    if include_worklist:
        from kuroko.worklist import fetch_worklist
        for p_cfg in cfg.projects:
            if projects_list and p_cfg.name not in projects_list: continue
            if p_cfg.repo:
                try:
                    data = fetch_worklist(p_cfg.repo, limit=5)
                    data["project"] = p_cfg.name
                    worklists.append(data)
                except Exception as e:
                    click.echo(f"Warning: {e}", err=True)

    report_content = generate_report(entries=entries, title=title, per_project_files=actual_per_project, filters={}, include_path=include_path, include_evidence=include_evidence, collapse_details=collapse_details, worklists=worklists)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    click.echo(f"Report successfully generated at {output_path}")

@main.command()
@click.option('--input-file', default='report.md', help='Markdown report file to render.')
@click.option('--refresh/--no-refresh', default=False, help='Run report before rendering.')
@click.option('--report-args', default='', help='Extra args passed to report command.')
@click.option('--include-worklist', is_flag=True, help='Include worklist on refresh.')
@click.option('--kanpe-cmd', default='kanpe', help='Command to execute kanpe.')
@click.option('--shinko-cmd', default='shinko', help='Command to execute shinko.')
@click.option('--host', default='127.0.0.1', help='Host to bind.')
@click.option('--port', default=8765, type=int, help='Port to bind.')
@click.option('--open-browser/--no-open-browser', default=True, help='Open browser automatically.')
@click.option('--allow-remote', is_flag=True, help='Allow non-localhost.')
@click.pass_context
def view(ctx, input_file, refresh, report_args, include_worklist, kanpe_cmd, shinko_cmd, host, port, open_browser, allow_remote):
    """Start Web UI to view report."""
    report_path = Path(input_file)
    current_nonce = secrets.token_hex(16)
    config_path = ctx.obj['config_path']

    if refresh:
        refresh_report(report_path=report_path, kanpe_cmd=kanpe_cmd, report_args=report_args, include_worklist=include_worklist)

    if not report_path.exists():
        raise click.ClickException(f"report file not found: {report_path}")

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path == '/refresh':
                refresh_report(report_path=report_path, kanpe_cmd=kanpe_cmd, report_args=report_args, include_worklist=include_worklist)
                self.send_response(303); self.send_header('Location', '/'); self.end_headers()
                return
            if self.path == '/suggest':
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length).decode('utf-8')
                from urllib.parse import parse_qs
                params = {k: v[0] for k, v in parse_qs(post_data).items()}
                mode = params.get("mode"); project = params.get("project")
                suggestion = invoke_shinko(shinko_cmd, report_path, config_path, mode=mode, project=project)
                suggestion_html = clean_html(markdown(suggestion, extensions=["extra"]))
                self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers()
                self.wfile.write(suggestion_html.encode('utf-8'))
                return

        def do_GET(self):
            if self.path == '/':
                with open(report_path, 'r', encoding='utf-8') as f: markdown_text = f.read()
                html = render_markdown_to_html(markdown_text, current_nonce)
                self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers()
                self.wfile.write(html.encode('utf-8'))
                return
        def log_message(self, format, *args): return

    with ReusableTCPServer((host, port), Handler) as httpd:
        click.echo(f"kanpe running at http://{host}:{port}"); 
        if open_browser: webbrowser.open(f"http://{host}:{port}")
        try: httpd.serve_forever()
        except KeyboardInterrupt: click.echo("\nkanpe stopped.")

if __name__ == '__main__':
    main()
