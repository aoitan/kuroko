import shlex
import secrets
import socketserver
import subprocess
import webbrowser
import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

import click
import bleach
from markdown import markdown


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
    # Allow safe tags for report visualization.
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
    
    # Allow text-align for table cell alignment
    from bleach.css_sanitizer import CSSSanitizer
    css_sanitizer = CSSSanitizer(allowed_css_properties=['text-align'])
    
    return bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs, css_sanitizer=css_sanitizer)


def render_markdown_to_html(markdown_text: str, nonce: str) -> str:
    # md_in_html is required to parse Markdown inside <details> tags
    content_raw = markdown(markdown_text, extensions=["extra", "md_in_html"])
    content = clean_html(content_raw)
    return HTML_TEMPLATE.format(content=content, nonce=nonce)


def refresh_report(report_path: Path, kuroko_cmd: str, report_args: str, include_worklist: bool = False) -> None:
    # Auto-detect if current report has worklist to maintain state on refresh
    auto_include_worklist = include_worklist
    if not auto_include_worklist and report_path.exists():
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                if "## Worklist" in f.read():
                    auto_include_worklist = True
        except Exception:
            pass

    args = shlex.split(kuroko_cmd, posix=(sys.platform != "win32"))
    args.extend(["report", str(report_path)])
    
    if auto_include_worklist:
        args.append("--include-worklist")
        
    if report_args:
        args.extend(shlex.split(report_args, posix=(sys.platform != "win32")))

    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise click.ClickException(f"failed to run {' '.join(args)}: {stderr}")


def invoke_shinko(shinko_cmd: str, report_path: Path, config: str = None, mode: str = None, project: str = None) -> str:
    """Invokes shinko command and returns the suggestion."""
    # Resolve shinko command. Default to current python interpreter if it looks like a module path
    if shinko_cmd == "shinko":
        # Try to use current python if shinko command might not be in PATH
        # This is safer for development/venv environments
        cmd = [sys.executable, "-m", "shinko.cli", "--input-file", str(report_path), "--json-output"]
    else:
        cmd = shlex.split(shinko_cmd, posix=(sys.platform != "win32"))
        cmd.extend(["--input-file", str(report_path), "--json-output"])

    if config:
        cmd.extend(["--config", str(config)])

    if mode:
        cmd.extend(["--mode", mode])
    
    if project:
        cmd.extend(["--project", project])
        
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        raise RuntimeError(f"shinko command not found: '{cmd[0]}'. Please ensure it is installed.")
    except subprocess.TimeoutExpired:
        raise RuntimeError("shinko command timed out after 60 seconds.")

    if result.returncode != 0:
        stderr_snippet = (result.stderr[:500] + "...") if len(result.stderr) > 500 else result.stderr
        raise RuntimeError(f"shinko command failed (exit {result.returncode}): {stderr_snippet}")
        
    try:
        output_data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        stdout_snippet = (result.stdout[:500] + "...") if len(result.stdout) > 500 else result.stdout
        raise RuntimeError(f"Failed to parse shinko output as JSON: {e}\nOutput: {stdout_snippet}")

    return output_data.get("suggestion", "")


@click.command()
@click.option('--input-file', default='report.md', help='Markdown report file to render.')
@click.option('--refresh/--no-refresh', default=False, help='Run `kuroko report <input-file>` before rendering.')
@click.option('--report-args', default='', help='Extra args passed to `kuroko report` when --refresh is enabled.')
@click.option('--include-worklist', is_flag=True, help='Force include worklist in the generated report on refresh.')
@click.option('--kuroko-cmd', default='kuroko', help='Command name/path used to execute kuroko.')
@click.option('--shinko-cmd', default='shinko', help='Command name/path used to execute shinko.')
@click.option('--host', default='127.0.0.1', help='Host to bind web server.')
@click.option('--port', default=8765, type=int, help='Port to bind web server.')
@click.option('--open-browser/--no-open-browser', default=True, help='Open browser automatically.')
@click.option('--config', default=None, help='Path to kuroko.config.yaml')
@click.option(
    '--allow-remote',
    is_flag=True,
    help='Allow binding to non-localhost interfaces (unsafe; exposes /refresh and /suggest).'
)
def main(input_file, refresh, report_args, include_worklist, kuroko_cmd, shinko_cmd, host, port, open_browser, config, allow_remote):
    report_path = Path(input_file)
    current_nonce = secrets.token_hex(16)

    # Prevent accidental exposure on non-localhost interfaces unless explicitly allowed.
    normalized_host = (host or "").strip().lower()
    is_localhost = (
        normalized_host == "localhost"
        or normalized_host == "::1"
        or normalized_host.startswith("127.")
    )
    if not is_localhost and not allow_remote:
        raise click.ClickException(
            "Refusing to bind HTTP server to non-localhost host "
            f"({host!r}) without --allow-remote.\n"
            "The kanpe web UI exposes /refresh and /suggest endpoints that are only protected by a "
            "nonce embedded in the HTML. If you bind to a publicly reachable interface, third parties "
            "can fetch `/`, obtain the nonce, and replay these actions.\n"
            "Use --allow-remote only on trusted networks and behind appropriate access controls."
        )
    if not is_localhost and allow_remote:
        click.echo(
            "WARNING: kanpe HTTP server is bound to a non-localhost interface. "
            "The /refresh and /suggest endpoints are only protected by a nonce that can be obtained "
            "from GET `/`. Do NOT expose this to untrusted networks.",
            err=True,
        )

    if refresh:
        refresh_report(
            report_path=report_path,
            kuroko_cmd=kuroko_cmd,
            report_args=report_args,
            include_worklist=include_worklist
        )

    # Always check existence even after refresh
    if not report_path.exists():
        raise click.ClickException(
            f"report file not found: {report_path} (run `kuroko report {report_path}` first, or use --refresh)"
        )

    class Handler(BaseHTTPRequestHandler):
        def _get_post_params(self) -> dict:
            """Parses the POST body and returns params dict. Caches the result."""
            if hasattr(self, "_post_params"):
                return self._post_params
            
            try:
                max_body = 4096
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > max_body:
                    self._post_params = {}
                    return {}
                
                post_data = self.rfile.read(content_length).decode('utf-8')
                from urllib.parse import parse_qs
                self._post_params = {k: v[0] for k, v in parse_qs(post_data).items()}
                return self._post_params
            except Exception:
                self._post_params = {}
                return {}

        def _validate_nonce(self) -> bool:
            """Validates the nonce against current_nonce. Returns True if valid."""
            params = self._get_post_params()
            nonce_in_post = params.get("nonce")

            import hmac
            if nonce_in_post and hmac.compare_digest(nonce_in_post, current_nonce):
                return True
            else:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Forbidden: Invalid nonce.")
                return False

        def do_POST(self):
            if self.path == '/refresh':
                if not self._validate_nonce():
                    return

                try:
                    refresh_report(
                        report_path=report_path,
                        kuroko_cmd=kuroko_cmd,
                        report_args=report_args,
                        include_worklist=include_worklist
                    )
                    self.send_response(303)
                    self.send_header('Location', '/')
                    self.end_headers()
                    return
                except Exception as exc:
                    import traceback
                    traceback.print_exc()
                    self.send_response(500)
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(b"Failed to refresh report.")
                    return

            if self.path == '/suggest':
                if not self._validate_nonce():
                    return

                params = self._get_post_params()
                mode = params.get("mode")
                project = params.get("project")

                try:
                    suggestion = invoke_shinko(shinko_cmd, report_path, config, mode=mode, project=project)

                    # Print to console for server-side verification
                    print(f"\n--- Raw LLM Suggestion ---\n{suggestion}\n--------------------------\n")
                    
                    suggestion_html = clean_html(markdown(suggestion, extensions=["extra"]))
                    
                    # Append raw text in a details tag for UI verification
                    import html
                    raw_escaped = html.escape(suggestion)
                    suggestion_html += (
                        f'<hr><details style="margin-top: 1rem; color: #666; font-size: 0.85rem;">'
                        f'<summary style="cursor: pointer;">生の回答を表示 (Markdown)</summary>'
                        f'<pre style="white-space: pre-wrap; background: #eee; padding: 0.5rem; margin-top: 0.5rem; border-radius: 4px;">{raw_escaped}</pre>'
                        f'</details>'
                    )
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(suggestion_html.encode('utf-8'))
                    return
                except Exception as exc:
                    import traceback
                    traceback.print_exc()
                    # Do not leak internal error details (e.g. LLM URL, file paths) to the client
                    self.send_response(500)
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(b"Error: Failed to get suggestion. Check server logs for details.")
                    return

            self.send_response(404)
            self.end_headers()

        def do_GET(self):
            if self.path == '/':
                try:
                    with open(report_path, 'r', encoding='utf-8') as f:
                        markdown_text = f.read()
                    html = render_markdown_to_html(markdown_text, current_nonce)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(html.encode('utf-8'))
                except Exception:
                    import traceback
                    traceback.print_exc()
                    self.send_response(500)
                    self.send_header('Content-Type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(b"Error reading or rendering report.")
                return

            if self.path in ['/refresh', '/suggest']:
                self.send_response(405)
                self.end_headers()
                self.wfile.write(b"Method Not Allowed: Use POST.")
                return

            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

        def log_message(self, format, *args):
            return

    url = f"http://{host}:{port}"
    with ReusableTCPServer((host, port), Handler) as httpd:
        click.echo(f"kanpe running at {url}")
        click.echo("Press Ctrl+C to stop.")

        if open_browser:
            try:
                webbrowser.open(url)
            except Exception:
                click.echo("Could not open browser automatically.")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            click.echo("\nkanpe stopped.")


if __name__ == '__main__':
    main()
