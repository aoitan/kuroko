import pytest
from datetime import datetime
from kuroko.inference import InferenceEngine

@pytest.fixture
def engine():
    return InferenceEngine()

def test_extract_todo(engine):
    text = "- [ ] レポートを作成する"
    inferences = engine.extract(text)
    assert any(inf.inference_type == "TODO" for inf in inferences)
    assert any("レポートを作成する" in inf.content for inf in inferences)

def test_extract_deadline_absolute(engine):
    text = "4/10までに提出する"
    inferences = engine.extract(text)
    assert any(inf.inference_type == "DEADLINE" for inf in inferences)

def test_extract_deadline_relative(engine):
    # base_date を 2024-04-01 に設定
    base_date = datetime(2024, 4, 1)
    
    # 明日
    text1 = "明日まで"
    inf1 = engine.extract(text1, base_date=base_date)
    deadline1 = next(inf for inf in inf1 if inf.inference_type == "DEADLINE")
    assert "2024-04-02" in deadline1.metadata
    
    # 明後日
    text2 = "明後日まで"
    inf2 = engine.extract(text2, base_date=base_date)
    deadline2 = next(inf for inf in inf2 if inf.inference_type == "DEADLINE")
    assert "2024-04-03" in deadline2.metadata

    # 明々後日
    text3 = "明々後日まで"
    inf3 = engine.extract(text3, base_date=base_date)
    deadline3 = next(inf for inf in inf3 if inf.inference_type == "DEADLINE")
    assert "2024-04-04" in deadline3.metadata

def test_extract_pending(engine):
    text = "クライアントからの返信待ち"
    inferences = engine.extract(text)
    assert any(inf.inference_type == "PENDING" for inf in inferences)

def test_extract_meeting(engine):
    text = "来週の会議について調整"
    inferences = engine.extract(text)
    assert any(inf.inference_type == "MEETING" for inf in inferences)

def test_extract_todo_false_positive(engine):
    # 過去形は TODO にしない
    text1 = "昨日確認した"
    inferences1 = engine.extract(text1)
    assert not any(inf.inference_type == "TODO" for inf in inferences1)

    # 名詞的な使用（文末でない）は TODO にしない
    text2 = "確認事項の一覧"
    inferences2 = engine.extract(text2)
    assert not any(inf.inference_type == "TODO" for inf in inferences2)

def test_extract_todo_extended(engine):
    # 拡充した動詞
    text1 = "レポートを提出すること"
    inferences1 = engine.extract(text1)
    assert any(inf.inference_type == "TODO" for inf in inferences1)

    text2 = "修正をお願いします"
    inferences2 = engine.extract(text2)
    assert not any(inf.inference_type == "TODO" for inf in inferences2)

    text3 = "Aさんに共有"
    inferences3 = engine.extract(text3)
    assert any(inf.inference_type == "TODO" for inf in inferences3)

def test_extract_deadline_this_week(engine):
    # base_date が 2024-04-01 (月曜日)
    base_date = datetime(2024, 4, 1)
    text = "今週中に対応"
    inferences = engine.extract(text, base_date=base_date)
    deadline = next(inf for inf in inferences if inf.inference_type == "DEADLINE")
    # 2024-04-01 (Mon) -> Sunday is 2024-04-07
    assert "2024-04-07" in deadline.metadata

def test_extract_meeting_not_pending(engine):
    # 「調整中」は MEETING ではなく PENDING にのみヒットすべき
    text = "現在日程を調整中"
    inferences = engine.extract(text)
    types = [inf.inference_type for inf in inferences]
    assert "PENDING" in types
    assert "MEETING" not in types

    # 「日程を調整」は MEETING にヒットすべき
    text2 = "来週の日程を調整する"
    inferences2 = engine.extract(text2)
    assert any(inf.inference_type == "MEETING" for inf in inferences2)
