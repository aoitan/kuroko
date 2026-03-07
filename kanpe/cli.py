import shlex
import secrets
import socketserver
import subprocess
import webbrowser
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
      <button id="suggest-btn" class="btn" style="background: #28a745; border-color: #28a745; margin-right: 0.5rem;" onclick="getSuggestion()">次の一手を提案</button>
      <form action="/refresh" method="post">
        <input type="hidden" name="nonce" value="{nonce}">
        <button type="submit" id="refresh-btn" class="btn" onclick="this.classList.add('loading'); this.innerText='Refreshing...';">Refresh & Reload</button>
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
      async function getSuggestion() {{
        const btn = document.getElementById('suggest-btn');
        const box = document.getElementById('suggestion-box');
        const content = document.getElementById('suggestion-content');
        
        btn.classList.add('loading');
        btn.innerText = '考え中...';
        box.style.display = 'block';
        content.innerText = 'LLMに問い合わせています...';
        
        try {{
          const response = await fetch('/suggest', {{
            method: 'POST',
            body: new URLSearchParams({{ 'nonce': '{nonce}' }})
          }});
          if (response.ok) {{
            const text = await response.text();
            content.innerText = text;
          }} else {{
            const errorText = await response.text();
            content.innerText = 'エラーが発生しました: ' + errorText;
          }}
        }} catch (e) {{
          content.innerText = '通信エラー: ' + e;
        }} finally {{
          btn.classList.remove('loading');
          btn.innerText = '次の一手を提案';
        }}
      }}
    </script>
  </body>
</html>
"""


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def render_markdown_to_html(markdown_text: str, nonce: str) -> str:
    # md_in_html is required to parse Markdown inside <details> tags
    content_raw = markdown(markdown_text, extensions=["extra", "md_in_html"])
    
    # Sanitize HTML after rendering from Markdown to prevent XSS (e.g., javascript: links)
    # Allow safe tags for report visualization.
    allowed_tags = list(bleach.ALLOWED_TAGS) + [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
        'p', 'br', 'hr', 'pre', 'code', 
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'details', 'summary'
    ]
    allowed_attrs = bleach.ALLOWED_ATTRIBUTES.copy()
    allowed_attrs['a'] = ['href', 'title']
    allowed_attrs['th'] = ['style', 'align']
    allowed_attrs['td'] = ['style', 'align']
    
    # Allow text-align for table cell alignment
    from bleach.css_sanitizer import CSSSanitizer
    css_sanitizer = CSSSanitizer(allowed_css_properties=['text-align'])
    
    content = bleach.clean(content_raw, tags=allowed_tags, attributes=allowed_attrs, css_sanitizer=css_sanitizer)
    return HTML_TEMPLATE.format(content=content, nonce=nonce)


def refresh_report(report_path: Path, kuroko_cmd: str, report_args: str, include_worklist: bool = False) -> None:
    import sys
    
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


@click.command()
@click.option('--input-file', default='report.md', help='Markdown report file to render.')
@click.option('--refresh/--no-refresh', default=False, help='Run `kuroko report <input-file>` before rendering.')
@click.option('--report-args', default='', help='Extra args passed to `kuroko report` when --refresh is enabled.')
@click.option('--include-worklist', is_flag=True, help='Force include worklist in the generated report on refresh.')
@click.option('--kuroko-cmd', default='kuroko', help='Command name/path used to execute kuroko.')
@click.option('--host', default='127.0.0.1', help='Host to bind web server.')
@click.option('--port', default=8765, type=int, help='Port to bind web server.')
@click.option('--open-browser/--no-open-browser', default=True, help='Open browser automatically.')
@click.option('--config', default=None, help='Path to kuroko.config.yaml')
def main(input_file, refresh, report_args, include_worklist, kuroko_cmd, host, port, open_browser, config):
    from kuroko.config import load_config
    kuroko_config = load_config(config)
    report_path = Path(input_file)
    current_nonce = secrets.token_hex(16)

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
        def do_POST(self):
            if self.path == '/refresh':
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length).decode('utf-8')
                
                from urllib.parse import parse_qs
                import hmac
                params = parse_qs(post_data)
                nonce_in_post = params.get("nonce", [None])[0]

                # Secure nonce check to prevent CSRF
                if nonce_in_post and hmac.compare_digest(nonce_in_post, current_nonce):
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
                else:
                    self.send_response(403)
                    self.end_headers()
                    self.wfile.write(b"Forbidden: Invalid nonce.")
                    return

            if self.path == '/suggest':
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length).decode('utf-8')
                
                from urllib.parse import parse_qs
                import hmac
                params = parse_qs(post_data)
                nonce_in_post = params.get("nonce", [None])[0]

                if nonce_in_post and hmac.compare_digest(nonce_in_post, current_nonce):
                    try:
                        with open(report_path, 'r', encoding='utf-8') as f:
                            report_text = f.read()
                        
                        from kuroko.llm import LLMClient
                        client = LLMClient(kuroko_config.llm)
                        messages = [
                            {"role": "system", "content": "You are an expert developer assistant. Based on the project status report, suggest the single most important next step to take. Answer in Japanese."},
                            {"role": "user", "content": f"Current status report:\n\n{report_text}"}
                        ]
                        suggestion = client.chat_completion(messages)
                        
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/plain; charset=utf-8')
                        self.end_headers()
                        self.wfile.write(suggestion.encode('utf-8'))
                        return
                    except Exception as exc:
                        import traceback
                        traceback.print_exc()
                        self.send_response(500)
                        self.send_header('Content-Type', 'text/plain; charset=utf-8')
                        self.end_headers()
                        self.wfile.write(f"Error: {str(exc)}".encode('utf-8'))
                        return
                else:
                    self.send_response(403)
                    self.end_headers()
                    self.wfile.write(b"Forbidden")
                    return

            self.send_response(404)
            self.end_headers()

        def do_GET(self):
            if self.path == '/refresh':
                # Reject GET requests to /refresh
                self.send_response(405)
                self.end_headers()
                self.wfile.write(b"Method Not Allowed: Use POST to refresh.")
                return

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
