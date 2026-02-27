import re
from typing import List, Dict, Optional

def parse_checkpoint_file(content: str) -> List[Dict]:
    entries = []
    
    # Timelineセクションを探す
    timeline_match = re.search(r'# Timeline\s*(.*)', content, re.DOTALL | re.IGNORECASE)
    if not timeline_match:
        return []
    
    timeline_content = timeline_match.group(1)
    
    # 各エントリを分割（"- HH:MM" で始まる行を区切りとする）
    # 先頭に改行を足して一貫性を持たせる
    raw_entries = re.split(r'\n(?=- \d{2}:\d{2})', "\n" + timeline_content.strip())
    
    for raw_entry in raw_entries:
        stripped_entry = raw_entry.strip()
        if not stripped_entry:
            continue
            
        entry = {}
        
        # 基本行のパース: - HH:MM [phase] act: ...
        header_match = re.search(r'- (\d{2}:\d{2}) \[(.*?)\] act: (.*)', stripped_entry)
        if header_match:
            entry["time"] = header_match.group(1)
            entry["phase"] = header_match.group(2)
            entry["act"] = header_match.group(3).strip()
        else:
            continue
            
        # evd: と block: を抽出するための正規表現
        # 複数行に対応するため、次のキーワードまたは末尾までをマッチさせる
        evd_match = re.search(r'^\s*evd:\s*(.*?)(?=\s*(?:block:|$))', stripped_entry, re.MULTILINE | re.DOTALL)
        entry["evd"] = evd_match.group(1).strip() if evd_match else None
        
        block_match = re.search(r'^\s*block:\s*(.*?)(?=\s*(?:evd:|$))', stripped_entry, re.MULTILINE | re.DOTALL)
        entry["block"] = block_match.group(1).strip() if block_match else None
        
        entries.append(entry)
        
    return entries
