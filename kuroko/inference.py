import re
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from dataclasses import dataclass, asdict

@dataclass
class InferenceResult:
    inference_type: str
    content: str
    metadata: Optional[str] = None

class InferenceEngine:
    def __init__(self):
        # メンテナンス性を考慮し、カテゴリごとに正規表現パターンを定義
        # Note: 複雑な後方参照を避け、ReDoS対策とする
        self.patterns = {
            "TODO": [
                (r"\[ \].*", "checkbox"),
                (r"(?:TODO|todo)[:：].*", "prefix_todo"),
                (r".*?(?:する|送る|作成|実装|検討|準備|連絡|確認|報告|相談|提出|共有|修正)(?:こと|必要がある|ください|しよう|したい|予定|目標|ください)(?:。|\s|$)", "verb_todo_strong"),
                (r".*?(?:する|送る|作成|実装|検討|準備|連絡|確認|報告|相談|提出|共有|修正)(?:。|\s|$)", "verb_todo_weak"),
            ],
            "DEADLINE": [
                (r".*?(?:明日|本日|今日|今週|来週|さ来週|再来週|来月|明後日|明々後日)(?:まで|までに|中|中に)", "relative_deadline"),
                (r"\d{1,2}/\d{1,2}.*?(?:まで|までに|中|中に)", "absolute_date_deadline"),
                (r"(?:期限|締切|〆切)[:：].*", "prefix_deadline"),
            ],
            "PENDING": [
                (r".*?(?:待ち|保留|pending|ペンディング|確認中|調整中).*", "status_pending"),
                (r"(?:PENDING|pending)[:：].*", "prefix_pending"),
            ],
            "MEETING": [
                (r".*?(?:会議|ミーティング|MTG|打ち合わせ|打合せ|面談).*", "keyword_meeting"),
                (r".*?日程を?調整(?!中).*", "keyword_meeting_adjust"),
            ],
            "COMPARE": [
                (r".*?(?:案[1-9]|比較|検討|メリット|デメリット|代案).*", "keyword_compare"),
            ]
        }
        
        # 相対日付表現の解決用
        self.relative_days = {
            "今日": 0, "本日": 0,
            "明日": 1,
            "明後日": 2,
            "明々後日": 3,
            "来週": 7,
            "再来週": 14,
            "さ来週": 14,
            "来月": 30, # 簡易的に30日後とする
        }

    def _resolve_relative_date(self, text: str, base_date: datetime) -> Optional[str]:
        """相対的な日付表現を絶対日時に変換する（簡易実装）"""
        if "今週" in text:
            # 今週の日曜日を期限とする
            days_until_sunday = (6 - base_date.weekday())
            target_date = base_date + timedelta(days=days_until_sunday)
            return target_date.strftime("%Y-%m-%d")

        for word, days in self.relative_days.items():
            if word in text:
                target_date = base_date + timedelta(days=days)
                return target_date.strftime("%Y-%m-%d")
        
        # 日付形式の抽出 (M/D)
        date_match = re.search(r"(\d{1,2})/(\d{1,2})", text)
        if date_match:
            month = int(date_match.group(1))
            day = int(date_match.group(2))
            # 年は基準日の年を補完
            try:
                target_date = base_date.replace(month=month, day=day)
                # もし過去の日付なら翌年とみなす（簡易ロジック）
                if target_date < base_date - timedelta(days=30):
                    target_date = target_date.replace(year=target_date.year + 1)
                return target_date.strftime("%Y-%m-%d")
            except ValueError:
                pass
                
        return None

    def extract(self, text: str, base_date: Optional[datetime] = None) -> List[InferenceResult]:
        if not base_date:
            base_date = datetime.now()
            
        results = []
        # テキストを改行で分割して行ごとに処理する（ノイズ削減のため）
        lines = text.splitlines()
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            for inf_type, patterns in self.patterns.items():
                for pattern, pattern_name in patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        content = match.group(0).strip()
                        metadata = {"pattern": pattern_name, "base_date": base_date.isoformat()}
                        
                        # DEADLINE の場合は日付解決を試みる
                        if inf_type == "DEADLINE":
                            resolved = self._resolve_relative_date(line, base_date)
                            if resolved:
                                metadata["resolved_date"] = resolved
                        
                        results.append(InferenceResult(
                            inference_type=inf_type,
                            content=content,
                            metadata=json.dumps(metadata, ensure_ascii=False)
                        ))
                        # 1つの行から同じタイプを複数回抽出しない
                        break
                        
        return results
