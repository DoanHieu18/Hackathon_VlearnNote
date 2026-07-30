"""Tool tất định trên transcript/notes đã tích luỹ trong buổi.

Nguyên tắc (theo mục 5 của tài liệu tham khảo Cupid Agent — "đẩy guardrail
xuống tầng dữ liệu"): các tool này KHÔNG gọi LLM và luôn trả status rõ ràng
khi không tìm thấy, để node gọi LLM không có cơ hội tự bịa nội dung.
"""

from __future__ import annotations

from agent.state import AgentState


def search_transcript(state: AgentState, keyword: str, window_minutes: float = 15.0) -> dict:
    """Tìm các đoạn transcript/note chứa keyword trong N phút gần nhất."""
    transcript = state.get("rolling_transcript") or []
    if not transcript:
        return {"status": "not_found", "reason": "chưa có transcript nào trong buổi"}

    latest_ts = transcript[-1].timestamp_s
    cutoff = latest_ts - window_minutes * 60
    keyword_lower = keyword.strip().lower()

    matches = [
        {"speaker": seg.speaker, "text": seg.text, "timestamp_s": seg.timestamp_s}
        for seg in transcript
        if seg.timestamp_s >= cutoff and keyword_lower in seg.text.lower()
    ]
    if not matches:
        return {
            "status": "not_found",
            "reason": f"không thấy '{keyword}' được nhắc trong {window_minutes} phút gần đây",
        }
    return {"status": "found", "matches": matches}


def get_recent_segment(state: AgentState, minutes_back: float) -> dict:
    """Lấy nguyên văn transcript trong N phút gần nhất, không diễn giải."""
    transcript = state.get("rolling_transcript") or []
    if not transcript:
        return {"status": "not_found", "reason": "chưa có transcript nào trong buổi"}

    latest_ts = transcript[-1].timestamp_s
    cutoff = latest_ts - minutes_back * 60
    segments = [seg for seg in transcript if seg.timestamp_s >= cutoff]
    if not segments:
        return {"status": "not_found", "reason": "không có transcript trong khoảng thời gian này"}
    return {
        "status": "found",
        "segments": [
            {"speaker": s.speaker, "text": s.text, "timestamp_s": s.timestamp_s} for s in segments
        ],
    }


def get_session_notes(state: AgentState) -> dict:
    """Trả toàn bộ note đã chốt trong buổi — dùng cho tổng hợp/catch-up."""
    notes = state.get("session_notes") or []
    if not notes:
        return {"status": "empty", "reason": "chưa có note nào được chốt trong buổi"}
    return {
        "status": "found",
        "notes": [
            {
                "label": n.label,
                "summary": n.summary,
                "timestamp_s": n.timestamp_s,
                "source": n.segment_text,
            }
            for n in notes
        ],
    }


AVAILABLE_TOOLS = {
    "search_transcript": search_transcript,
    "get_recent_segment": get_recent_segment,
    "get_session_notes": get_session_notes,
}
