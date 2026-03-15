import yaml
import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

class ProjectConfig(BaseModel):
    name: str
    root: str
    repo: Optional[str] = None

class DefaultsConfig(BaseModel):
    per_project_files: int = 5
    checkpoint_dir: str = "checkpoint"
    filename_glob: str = "*.md"
    max_depth: Optional[int] = None  # None は無制限

class LLMConfig(BaseModel):
    url: str = "http://localhost:11434/v1"
    model: str = "llama3"
    api_key: Optional[str] = None
    timeout: int = 30

class KurokoConfig(BaseModel):
    version: int = 1
    projects: List[ProjectConfig] = []
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    history_path: str = "~/.config/kuroko/history.jsonl"

def find_config() -> Optional[Path]:
    search_paths = [
        Path("kuroko.config.yaml"),
        Path.home() / ".config" / "kuroko" / "config.yaml",
        Path.home() / ".kuroko.config.yaml",
    ]
    for path in search_paths:
        if path.exists():
            return path
    return None

def load_config(config_path: Optional[str] = None) -> KurokoConfig:
    if config_path:
        path = Path(config_path)
    else:
        path = find_config()
        
    if path is None or not path.exists():
        return KurokoConfig()
        
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        if data is None:
            return KurokoConfig()
        return KurokoConfig(**data)
