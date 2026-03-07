import json
import urllib.request
from typing import List, Dict, Any
from kuroko.config import LLMConfig

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
                return body["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error connecting to LLM API: {str(e)}"
