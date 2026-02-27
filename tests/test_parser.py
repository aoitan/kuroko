import pytest
from kuroko.parser import parse_checkpoint_file

def test_parse_checkpoint_content():
    content = """# Timeline

- 03:12 [coding] act: checkpointスキル用のタイムラインテンプレを追加
  evd: git diff --stat
  block: なし

- 03:40 [fix] act: pytestが落ちる原因を調査して依存の競合を確認
  evd: ERROR: ImportError: ...
  block: 依存が壊れてる（version conflict）
"""
    entries = parse_checkpoint_file(content)
    
    assert len(entries) == 2
    
    assert entries[0]["time"] == "03:12"
    assert entries[0]["phase"] == "coding"
    assert entries[0]["act"] == "checkpointスキル用のタイムラインテンプレを追加"
    assert entries[0]["evd"] == "git diff --stat"
    assert entries[0]["block"] == "なし"
    
    assert entries[1]["time"] == "03:40"
    assert entries[1]["phase"] == "fix"
    assert entries[1]["act"] == "pytestが落ちる原因を調査して依存の競合を確認"
    assert entries[1]["evd"] == "ERROR: ImportError: ..."
    assert entries[1]["block"] == "依存が壊れてる（version conflict）"

def test_parse_incomplete_entry():
    content = """# Timeline

- 09:00 [planning] act: 雑なエントリ
  block: 詰まり中
"""
    entries = parse_checkpoint_file(content)
    assert len(entries) == 1
    assert entries[0]["evd"] is None
    assert entries[0]["block"] == "詰まり中"
