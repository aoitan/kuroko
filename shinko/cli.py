import click
import json
from pathlib import Path
from kuroko_core.config import load_config
from shinko.llm import LLMClient

@click.command()
@click.option('--input-file', default='report.md', help='Markdown report file for insight context.')
@click.option('--json-output', is_flag=True, help='Output in JSON format.')
@click.option('--config', default=None, help='Path to config file.')
def main(input_file, json_output, config):
    """Generate progress management insights using LLM."""
    cfg = load_config(config)
    report_path = Path(input_file)
    if not report_path.exists():
        raise click.ClickException(f"Report file not found: {report_path}")

    with open(report_path, 'r', encoding='utf-8') as f:
        report_text = f.read()
    
    # Limit context size
    max_context_chars = 20000
    if len(report_text) > max_context_chars:
        report_text = report_text[:max_context_chars] + "\n\n(Truncated for LLM context...)"

    client = LLMClient(cfg.llm)
    messages = [
        {"role": "system", "content": "You are an expert developer assistant. Based on the project status report, suggest the single most important next step to take. Answer in Japanese."},
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

if __name__ == '__main__':
    main()
