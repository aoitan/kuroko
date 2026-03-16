import pytest
import hashlib
from kuroko.chunker import chunk_text

def test_chunk_text_simple_split():
    text = """Block 1 line 1
Block 1 line 2

Block 2 line 1
"""
    chunks = chunk_text(text)
    assert len(chunks) == 2
    assert chunks[0]["chunk_text"] == "Block 1 line 1\nBlock 1 line 2"
    assert chunks[1]["chunk_text"] == "Block 2 line 1"
    assert chunks[0]["chunk_index"] == 0
    assert chunks[1]["chunk_index"] == 1

def test_chunk_text_with_headings():
    text = """# Heading 1
Intro text.

## Sub Heading 1.1
Content A.

Content B.

# Heading 2
Content C.
"""
    chunks = chunk_text(text)
    # 1: # Heading 1
    # 2: Intro text.
    # 3: ## Sub Heading 1.1
    # 4: Content A.
    # 5: Content B.
    # 6: # Heading 2
    # 7: Content C.
    # 空行で区切る場合、見出し自体も1つのチャンク（または次のブロックの開始）になるべきか？
    # 通常、見出しは新しいセクションの開始なので、見出しも含めてチャンクにするのが一般的。
    
    # 期待される挙動を定義：
    # 空行で区切りつつ、見出し（#）で始まる行も区切りとする。
    # 1: # Heading 1
    # 2: Intro text.
    # 3: ## Sub Heading 1.1
    # 4: Content A.
    # 5: Content B.
    # 6: # Heading 2
    # 7: Content C.
    # (見出し行も含めたブロックとして扱うか、見出しをメタデータとして持つか)
    # 計画には "heading" カラムがあるので、見出しはメタデータとして持ち、本文とは分けるか、
    # あるいは見出し行も含めて本文とするか。
    # 検索を考えると、見出しが含まれていた方が文脈がわかりやすい。
    
    assert any(c["heading"] == "Heading 1" for c in chunks)
    assert any(c["heading"] == "Sub Heading 1.1" for c in chunks)

def test_chunk_hash_consistency():
    text = "Hello World"
    chunks1 = chunk_text(text)
    chunks2 = chunk_text(text)
    assert chunks1[0]["chunk_hash"] == chunks2[0]["chunk_hash"]
    
    # Verify hash content
    expected_hash = hashlib.sha256("Hello World".encode("utf-8")).hexdigest()
    assert chunks1[0]["chunk_hash"] == expected_hash

def test_timestamp_extraction():
    text = """# 2026-03-16 10:00
Meeting started.

Update at 10:30:
Something happened.
"""
    chunks = chunk_text(text)
    # If we can extract timestamp from heading or text
    # This might be tricky without a clear spec, but let's try to detect YYYY-MM-DD
    assert any(c["block_timestamp"] == "2026-03-16 10:00" for c in chunks)
