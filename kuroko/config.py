import yaml
import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

class ProjectConfig(BaseModel):
    name: str
    root: str

class DefaultsConfig(BaseModel):
    per_project_files: int = 5
    checkpoint_dir: str = "checkpoint"
    filename_glob: str = "*.md"

class KurokoConfig(BaseModel):
    version: int = 1
    projects: List[ProjectConfig] = []
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)

def find_config() -> Optional[Path]:
    """設定ファイルを以下の優先順位で探す:
    1. カレントディレクトリの kuroko.config.yaml
    2. ~/.config/kuroko/config.yaml
    3. ~/.kuroko.config.yaml
    """
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
        # 設定ファイルが見つからない場合は空のプロジェクトリストを持つデフォルト設定を返す
        return KurokoConfig()
        
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        if data is None:
            return KurokoConfig()
        return KurokoConfig(**data)
