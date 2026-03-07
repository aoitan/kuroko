import json
import subprocess
from typing import List, Dict, Any

def _run_gh_list(repo: str, item_type: str, limit: int) -> List[Dict[str, Any]]:
    # item_type is 'pr' or 'issue'
    cmd = [
        "gh", item_type, "list",
        "-R", repo,
        "--state", "open",
        "--limit", str(limit),
        "--json", "number,title,state,updatedAt,url,labels"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        # Clean up data to match our schema
        cleaned = []
        for item in data:
            cleaned.append({
                "id": item["number"],
                "title": item["title"],
                "state": item["state"],
                "updated_at": item["updatedAt"],
                "url": item["url"],
                "labels": [label["name"] for label in item.get("labels", [])]
            })
        return cleaned
    except FileNotFoundError:
        raise RuntimeError("gh command not found. Please install GitHub CLI.")
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        stderr = ""
        if isinstance(e, subprocess.CalledProcessError):
            stderr = e.stderr.strip() or "Unknown error"
        else:
            stderr = f"Invalid JSON response: {e}"
        raise RuntimeError(f"failed to fetch {item_type}s for {repo}: {stderr}")

def _run_gh_total_count(repo: str, item_type: str) -> int:
    # item_type is 'pr' or 'issue'
    query_type = "is:pr" if item_type == "pr" else "is:issue"
    # Use Search API via gh api to get total_count efficiently
    cmd = [
        "gh", "api",
        f"search/issues?q=repo:{repo}+is:open+{query_type}&per_page=1",
        "--jq", ".total_count"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return int(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError) as e:
        import sys
        stderr = getattr(e, "stderr", "")
        print(f"Warning: Failed to fetch total count for {item_type}s in {repo}: {e} {stderr}", file=sys.stderr)
        return -1
    except FileNotFoundError:
        # Re-raise FileNotFoundError as it's a critical configuration issue (gh not installed)
        raise RuntimeError("gh command not found. Please install GitHub CLI.")

def fetch_worklist(repo: str, limit: int = 5) -> Dict[str, Any]:
    prs = _run_gh_list(repo, "pr", limit)
    issues = _run_gh_list(repo, "issue", limit)
    
    total_prs = _run_gh_total_count(repo, "pr")
    total_issues = _run_gh_total_count(repo, "issue")
    
    # Fallback logic if count failed
    if total_prs < 0:
        total_prs = len(prs)
    if total_issues < 0:
        total_issues = len(issues)

    return {
        "repo": repo,
        "pull_requests": prs,
        "issues": issues,
        "total_pull_requests": total_prs,
        "total_issues": total_issues
    }
