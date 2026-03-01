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

def fetch_worklist(repo: str, limit: int = 5) -> Dict[str, Any]:
    return {
        "repo": repo,
        "pull_requests": _run_gh_list(repo, "pr", limit),
        "issues": _run_gh_list(repo, "issue", limit)
    }
