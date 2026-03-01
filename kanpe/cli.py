import shlex
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
      body {{ max-width: 900px; margin: 2rem auto; padding: 0 1rem; line-height: 1.7; }}
      pre {{ overflow-x: auto; }}
      code {{ white-space: pre-wrap; }}
      table {{ border-collapse: collapse; }}
      th, td {{ padding: 0.4rem 0.6rem; border: 1px solid #ccc; }}
    </style>
  </head>
  <body>
    {content}
  </body>
</html>
"""


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def render_markdown_to_html(markdown_text: str) -> str:
    content_raw = markdown(markdown_text, extensions=["extra"])
    
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
    
    content = bleach.clean(content_raw, tags=allowed_tags, attributes=allowed_attrs)
    return HTML_TEMPLATE.format(content=content)


def refresh_report(report_path: Path, kuroko_cmd: str, report_args: str) -> None:
    args = [kuroko_cmd, "report", str(report_path)]
    if report_args:
        import sys
        args.extend(shlex.split(report_args, posix=(sys.platform != "win32")))

    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise click.ClickException(f"failed to run {' '.join(args)}: {stderr}")


@click.command()
@click.option('--input-file', default='report.md', help='Markdown report file to render.')
@click.option('--refresh/--no-refresh', default=False, help='Run `kuroko report <input-file>` before rendering.')
@click.option('--report-args', default='', help='Extra args passed to `kuroko report` when --refresh is enabled.')
@click.option('--kuroko-cmd', default='kuroko', help='Command name/path used to execute kuroko.')
@click.option('--host', default='127.0.0.1', help='Host to bind web server.')
@click.option('--port', default=8765, type=int, help='Port to bind web server.')
@click.option('--open-browser/--no-open-browser', default=True, help='Open browser automatically.')
def main(input_file, refresh, report_args, kuroko_cmd, host, port, open_browser):
    report_path = Path(input_file)

    if refresh:
        refresh_report(report_path=report_path, kuroko_cmd=kuroko_cmd, report_args=report_args)

    if not report_path.exists() and not refresh:
        raise click.ClickException(
            f"report file not found: {report_path} (run `kuroko report {report_path}` first, or use --refresh)"
        )

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            try:
                with open(report_path, 'r', encoding='utf-8') as f:
                    markdown_text = f.read()
                html = render_markdown_to_html(markdown_text)
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error reading report: {e}".encode('utf-8'))

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
