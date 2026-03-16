import re
import hashlib
from typing import List, Dict

def calculate_chunk_hash(text: str) -> str:
    """Calculates the SHA-256 hash of the content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def extract_timestamp(text: str) -> str:
    """Attempts to extract a timestamp (YYYY-MM-DD HH:MM or YYYY-MM-DD) from the text."""
    # Pattern for YYYY-MM-DD HH:MM or YYYY-MM-DD
    match = re.search(r'(\d{4}-\d{2}-\d{2}(?:\s\d{2}:\d{2})?)', text)
    if match:
        return match.group(1)
    return None

def chunk_text(text: str) -> List[Dict]:
    """
    Chunks the text into blocks based on empty lines and headings.
    
    Each chunk is a dictionary containing:
    - chunk_index: int
    - chunk_text: str
    - heading: str (the most recent heading)
    - block_timestamp: str (extracted timestamp, if any)
    - chunk_hash: str
    """
    lines = text.splitlines()
    chunks = []
    current_chunk_lines = []
    current_heading = None
    chunk_index = 0
    
    def add_chunk(lines_list, heading, index):
        if not lines_list:
            return None
        
        chunk_content = "\n".join(lines_list).strip()
        if not chunk_content:
            return None
            
        timestamp = extract_timestamp(chunk_content)
        # If not in content, maybe it was in the heading but not in the block?
        # For now, extract_timestamp already checks the content which includes headings if they are part of the block.
        
        return {
            "chunk_index": index,
            "chunk_text": chunk_content,
            "heading": heading,
            "block_timestamp": timestamp,
            "chunk_hash": calculate_chunk_hash(chunk_content)
        }

    for line in lines:
        # Check if it's a heading
        heading_match = re.match(r'^(#+)\s+(.*)', line)
        
        # If it's a heading OR if it's an empty line (and we have content)
        if heading_match:
            # New heading found. Finish current chunk.
            new_chunk = add_chunk(current_chunk_lines, current_heading, chunk_index)
            if new_chunk:
                chunks.append(new_chunk)
                chunk_index += 1
            
            # Reset for new block
            current_heading = heading_match.group(2).strip()
            current_chunk_lines = [line]
        elif not line.strip():
            # Empty line. Finish current chunk.
            new_chunk = add_chunk(current_chunk_lines, current_heading, chunk_index)
            if new_chunk:
                chunks.append(new_chunk)
                chunk_index += 1
            current_chunk_lines = []
        else:
            current_chunk_lines.append(line)
            
    # Add the last chunk
    last_chunk = add_chunk(current_chunk_lines, current_heading, chunk_index)
    if last_chunk:
        chunks.append(last_chunk)
        
    return chunks
