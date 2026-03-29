import os
import sqlite3
from click.testing import CliRunner
from kuroko.cli import main
from kuroko_core.config import KurokoConfig, ProjectConfig
import yaml

def test_collect_memo_cli(tmp_path):
    # Setup mock project and config
    project_root = tmp_path / "project"
    project_root.mkdir()
    memo_file = project_root / "memo.md"
    memo_file.write_text("CLI test memo content", encoding="utf-8")
    
    db_file = tmp_path / "kuroko.db"
    
    config_data = {
        "version": 1,
        "projects": [
            {"name": "test_proj", "root": str(project_root)}
        ],
        "db_path": str(db_file)
    }
    
    config_path = tmp_path / "kuroko.config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)
        
    runner = CliRunner()
    result = runner.invoke(main, ["--config", str(config_path), "collect", "memo"])
    
    assert result.exit_code == 0
    assert "Imported 1 new memos" in result.output
    
    # Verify DB
    import sqlite3
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM source_texts")
    assert cursor.fetchone()[0] == 1
    conn.close()

def test_collect_memo_cli_twice(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    memo_file = project_root / "memo.md"
    memo_file.write_text("CLI test memo content", encoding="utf-8")
    
    db_file = tmp_path / "kuroko.db"
    config_data = {
        "version": 1,
        "projects": [{"name": "test_proj", "root": str(project_root)}],
        "db_path": str(db_file)
    }
    config_path = tmp_path / "kuroko.config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)
        
    runner = CliRunner()
    # First run
    runner.invoke(main, ["--config", str(config_path), "collect", "memo"])
    
    # Second run
    result = runner.invoke(main, ["--config", str(config_path), "collect", "memo"])
    assert result.exit_code == 0
    assert "Imported 0 new memos" in result.output
    assert "Updated 0 existing memos" in result.output


def test_collect_memo_cli_creates_embeddings(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    memo_file = project_root / "memo.md"
    memo_file.write_text("CLI embedding content", encoding="utf-8")

    db_file = tmp_path / "kuroko.db"
    config_data = {
        "version": 1,
        "projects": [{"name": "test_proj", "root": str(project_root)}],
        "db_path": str(db_file),
        "embedding": {"model": "cli-embedding-v1", "chunking_version": "phase3"},
    }
    config_path = tmp_path / "kuroko.config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)

    runner = CliRunner()
    result = runner.invoke(main, ["--config", str(config_path), "collect", "memo"])

    assert result.exit_code == 0

    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute("SELECT embedding_model, chunking_version FROM chunk_embeddings")
    row = cursor.fetchone()
    assert row == ("cli-embedding-v1", "phase3")
    conn.close()
