import click
import json
from pathlib import Path
from kuroko_core.config import load_config
from kuroko_core.history import HistorySummarizer, get_repo_root
from shinko.llm import LLMClient

@click.command()
@click.option('--input-file', default='report.md', help='Markdown report file for insight context.')
@click.option('--json-output', is_flag=True, help='Output in JSON format.')
@click.option('--config', default=None, help='Path to config file.')
@click.option('--mode', type=click.Choice(['normal', 'rescue', 'deep']), default='normal', help='Suggestion mode (temperature).')
@click.option('--project', default=None, help='Target project to focus on.')
def main(input_file, json_output, config, mode, project):
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

if __name__ == '__main__':
    main()
