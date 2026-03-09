import json
import urllib.request
from typing import List, Dict, Any
from kuroko_core.config import LLMConfig

class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config

    def chat_completion(self, messages: List[Dict[str, str]]) -> str:
        # url might be like http://localhost:11434/v1
        url = f"{self.config.url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
            
        data = {
            "model": self.config.model,
            "messages": messages,
        }
        
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode("utf-8"), 
            headers=headers, 
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as res:
                body = json.loads(res.read().decode("utf-8"))
                choices = body.get("choices")
                if not choices or not isinstance(choices, list):
                    raise RuntimeError("Invalid response format from LLM API: missing 'choices'")
                content = choices[0].get("message", {}).get("content")
                if content is None:
                    raise RuntimeError("Invalid response format from LLM API: missing 'content'")
                return content
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM API returned error {e.code}: {error_body}") from e
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"Error connecting to or parsing LLM API: {e}") from e
