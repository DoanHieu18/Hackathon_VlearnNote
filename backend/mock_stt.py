import asyncio
import re
from pathlib import Path

async def stream_transcript_from_file(file_path: str, delay_seconds: float = 3.0):
    """
    Đọc file transcript (.md) và parse từng dòng thành các segment.
    Trả về (speaker, text) dạng async generator để giả lập luồng STT realtime.
    """
    # Regex để bắt các dòng bắt đầu bằng **[Txx-xxx]**
    pattern = re.compile(r'^\*\*\[T\d+-\d+\]\*\*\s*(.*)')
    
    path = Path(file_path)
    if not path.exists():
        print(f"[Mock STT] File not found: {file_path}")
        return

    print(f"[Mock STT] Start streaming from file: {path.name}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith(">"):
                speaker = "Unknown"
                text = line
                
                yield {"speaker": speaker, "text": text}
                await asyncio.sleep(delay_seconds)
