import click
import json
import sys
import re
import traceback
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from kuroko_core.config import load_config
from kuroko_core.history import HistorySummarizer, get_repo_root
from kuroko.collector import collect_checkpoints
from kuroko.worklist import fetch_worklist
from shinko.llm import LLMClient

@click.group()
@click.option('--config', default=None, help='Path to config file.')
@click.pass_context
def main(ctx, config):
    ctx.ensure_object(dict)
    cfg = load_config(config)
    ctx.obj['config'] = cfg
    # Maintain lazy evaluation for checkpoint collection
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
            click.echo(f"{e['date']} {e['time']} [{e['phase']}] {e['project']}{issue_str}: {e['act']}")

@main.command()
@click.option('--json-output', is_flag=True, help='Output in JSON format.')
@click.pass_context
def blockers(ctx, json_output):
    """Show active blockers."""
    from kuroko_core.constants import BLOCK_IGNORE
    entries = ctx.obj['get_entries']()
    blockers = [e for e in entries if e['block'] and e['block'].strip().lower() not in BLOCK_IGNORE]
    
    if json_output:
        print_json(blockers)
    else:
        if not blockers:
            click.echo("No active blockers found.")
            return
        for e in blockers:
            click.echo(f"BLOCK: {e['block']} @ {e['project']} ({e['date']} {e['time']})")

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
            click.echo(f"{e['project']}: {e['date']} {e['time']} [{e['phase']}] {e['act']}")

@main.command()
@click.option('--n', default=5, help='Number of items to show per category.')
@click.option('--json-output', is_flag=True, help='Output in JSON format.')
@click.pass_context
def worklist(ctx, n, json_output):
    """Show open PRs and Issues from GitHub."""
    cfg = ctx.obj['config']
    results = []
    
    for project in cfg.projects:
        if not project.repo:
            continue
        try:
            data = fetch_worklist(project.repo, limit=n)
            data["project"] = project.name
            results.append(data)
        except RuntimeError as e:
            click.echo(f"Warning: {e}", err=True)

    if json_output:
        print_json(results)
    else:
        from kuroko.worklist import format_total_count
        if not results:
            click.echo("No worklist items found (ensure 'repo' is set in kuroko.config.yaml).")
            return

        for res in results:
            pr_total_str = format_total_count(res.get("total_pull_requests", -1))
            issue_total_str = format_total_count(res.get("total_issues", -1))
            
            click.echo(f"## Project: {res['project']} ({res['repo']})")
            click.echo(f"Summary: {pr_total_str} Open PRs, {issue_total_str} Open Issues\n")
            
            click.echo("### Open Pull Requests")
            if not res["pull_requests"]:
                click.echo("No open PRs.")
            else:
                for pr in res["pull_requests"]:
                    click.echo(f"- #{pr['id']} {pr['title']} ({pr['url']})")
            
            click.echo("\n### Open Issues")
            if not res["issues"]:
                click.echo("No open issues.")
            else:
                for issue in res["issues"]:
                    click.echo(f"- #{issue['id']} {issue['title']} ({issue['url']})")
            click.echo("\n" + "-" * 40 + "\n")

def extract_project_contexts(report_text: str) -> dict:
    """Extracts project-specific sections from the report text (Fallback)."""
    contexts = {}
    
    # Extract status table rows
    status_match = re.search(r'## Status\n(.*?)(?:\n##|$)', report_text, re.DOTALL)
    status_rows = []
    if status_match:
        table_text = status_match.group(1).strip()
        rows = table_text.split('\n')
        if len(rows) > 2: # Skip header and separator
            status_rows = rows[2:]

    # Extract worklist sections
    worklist_match = re.search(r'## Worklist\n(.*?)(?:\n##|$)', report_text, re.DOTALL)
    worklist_sections = {}
    if worklist_match:
        wl_text = worklist_match.group(1).strip()
        # Split by ### headers
        sections = re.split(r'\n### ', '\n' + wl_text)
        for section in sections:
            section = section.strip()
            if not section: continue
            lines = section.split('\n')
            header = lines[0]
            # Extract project name from "ProjectName (repo)"
            proj_name = header.split(' ')[0].strip()
            worklist_sections[proj_name] = section

    # Combine them
    all_projects = set(list(worklist_sections.keys()))
    for row in status_rows:
        cells = [c.strip() for c in row.split('|')]
        if len(cells) >= 5:
            proj = cells[4] 
            if proj and proj != '-' and proj != 'project':
                all_projects.add(proj)

    for proj in all_projects:
        proj_status = [row for row in status_rows if f'| {proj} |' in row]
        proj_wl = worklist_sections.get(proj, "(No worklist info)")
        contexts[proj] = {
            "status": "\n".join(proj_status),
            "worklist": proj_wl
        }
    
    return contexts

@main.command()
@click.option('--input-file', default=None, help='Markdown report file for insight context (fallback).')
@click.option('--json-output', is_flag=True, help='Output in JSON format.')
@click.option('--mode', type=click.Choice(['normal', 'rescue', 'deep']), default='normal', help='Suggestion mode (temperature).')
@click.option('--project', default=None, help='Target project to focus on.')
@click.option('--lang', default=None, help='Language for the LLM response.')
@click.pass_context
def insight(ctx, input_file, json_output, mode, project, lang):
    """Generate prioritized insights using live project data or report file."""
    cfg = ctx.obj['config']
    lang = lang or cfg.llm.language
    
    contexts = {}
    if input_file:
        report_path = Path(input_file)
        if report_path.exists():
            with open(report_path, 'r', encoding='utf-8') as f:
                report_text = f.read()
            contexts = extract_project_contexts(report_text)
    
    # If no contexts or no input file, collect live data
    if not contexts:
        all_entries = collect_checkpoints(cfg)
        for proj_cfg in cfg.projects:
            if project and proj_cfg.name != project:
                continue
            
            # Latest status for this project
            proj_entries = [e for e in all_entries if e['project'] == proj_cfg.name]
            status_summary = "\n".join([f"{e['date']} [{e['phase']}] {e['act']}" for e in proj_entries[:3]])
            
            # Worklist from GitHub
            worklist_data = "(No worklist info)"
            if proj_cfg.repo:
                try:
                    wl = fetch_worklist(proj_cfg.repo, limit=5)
                    pr_list = [f"PR #{p['id']}: {p['title']}" for p in wl['pull_requests']]
                    issue_list = [f"ISSUE #{i['id']}: {i['title']}" for i in wl['issues']]
                    worklist_data = f"Open PRs: {', '.join(pr_list)}\nOpen Issues: {', '.join(issue_list)}"
                except Exception:
                    pass
            
            contexts[proj_cfg.name] = {
                "status": status_summary or "(No recent activity)",
                "worklist": worklist_data
            }

    target_projects = [project] if project else list(contexts.keys())
    results = []

    # System Prompt for scoring
    if lang.lower() == "japanese":
        system_prompt = (
            "あなたはシニアエンジニアです。提供されたプロジェクトの進捗と未完了タスクに基づき、"
            "「次の一手」を具体的に提案し、その重要度を0から100のスコアで評価してください。\n\n"
            "出力形式 (JSONのみ):\n"
            '{"suggestion": "具体的な提案内容", "score": 85}\n\n'
            "制約:\n"
            "- 挨拶や要約は不要です。JSONオブジェクトのみを返してください。\n"
            "- 日本語で回答してください。"
        )
    else:
        system_prompt = (
            "You are a senior engineer. Based on the provided project progress and worklist, "
            "specifically suggest the 'next step' and score its importance from 0 to 100.\n\n"
            "Output Format (JSON only):\n"
            '{"suggestion": "specific suggestion content", "score": 85}\n\n'
            "Constraints:\n"
            "- No greetings or summaries. Return ONLY the JSON object.\n"
            f"- Answer in {lang}."
        )

    # Secretary Insight (History context)
    summarizer = HistorySummarizer(cfg.history_path)
    secretary_insight = summarizer.get_summary(get_repo_root(None))
    if secretary_insight:
        system_prompt += f"\n\n参考（過去の作業傾向）:\n{secretary_insight}"

    client = LLMClient(cfg.llm)

    def analyze_project(proj):
        ctx_data = contexts[proj]
        user_content = f"Project: {proj}\n\nStatus (Recent):\n{ctx_data['status']}\n\nWorklist:\n{ctx_data['worklist']}"
        try:
            response = client.chat_completion([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ])
            clean_res = re.sub(r'^```json\s*|\s*```$', '', response.strip(), flags=re.MULTILINE)
            data = json.loads(clean_res)
            return {
                "project": proj,
                "suggestion": data.get("suggestion", "No suggestion"),
                "score": data.get("score", 0)
            }
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            return {"project": proj, "suggestion": f"Error: {e}", "score": 0}

    # Parallel execution
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(analyze_project, proj) for proj in sorted(target_projects) if proj in contexts]
        results = [f.result() for f in futures]

    results.sort(key=lambda x: x['score'], reverse=True)

    if json_output:
        click.echo(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    else:
        output = ["### 推奨される次の一手 (優先順位順)\n" if lang.lower() == "japanese" else "### Recommended Next Steps\n"]
        for r in results:
            output.append(f"#### {r['project']} (Score: {r['score']})\n{r['suggestion']}\n")
        click.echo("\n".join(output))

def print_json(entries):
    output = {
        "generated_at": datetime.now().isoformat(),
        "items": entries
    }
    click.echo(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
