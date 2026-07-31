"""Tool tất định trên transcript/notes đã tích luỹ trong buổi.

Nguyên tắc (theo mục 5 của tài liệu tham khảo Cupid Agent — "đẩy guardrail
xuống tầng dữ liệu"): các tool này KHÔNG gọi LLM và luôn trả status rõ ràng
khi không tìm thấy, để node gọi LLM không có cơ hội tự bịa nội dung.
"""

from __future__ import annotations

import re
import unicodedata

from agent.state import AgentState

# Từ chức năng tiếng Việt — bỏ khi so khớp để "chạy server" vẫn khớp được đoạn
# "Chạy bằng lệnh: uvicorn main:app". Giữ danh sách ngắn, chỉ những từ thực sự
# không mang nội dung.
_STOPWORDS = frozenset(
    """
    của là và ở trong cho với thì mà nào gì đó này kia các những một cái
    có được bị người bạn em thầy cô mình nói vừa nãy nhất rất lại về từ
    khi lúc trên dưới sau trước hay hoặc như để đã sẽ đang bằng theo
    """.split()
)

# Điểm khớp tối thiểu để coi là liên quan: phải trùng ≥50% token nội dung của
# keyword. Ngưỡng này là guardrail — thấp hơn thì trả về "chưa xác nhận khớp"
# thay vì im lặng coi như tìm thấy.
_MIN_TOKEN_OVERLAP = 0.5


def _content_tokens(text: str) -> set[str]:
    """Tách token nội dung, bỏ dấu + stopword, để so khớp chịu được diễn giải lại."""
    folded = "".join(
        ch
        for ch in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(ch) != "Mn"
    )
    return {t for t in re.findall(r"[a-z0-9_:.\-]+", folded) if t not in _STOPWORDS and len(t) > 1}


def _in_window(transcript: list, window_minutes: float) -> list:
    latest_ts = transcript[-1].timestamp_s
    cutoff = latest_ts - window_minutes * 60
    return [seg for seg in transcript if seg.timestamp_s >= cutoff]


def _as_dict(seg) -> dict:
    return {"speaker": seg.speaker, "text": seg.text, "timestamp_s": seg.timestamp_s}


def search_transcript(state: AgentState, keyword: str, window_minutes: float = 15.0) -> dict:
    """Tìm đoạn transcript liên quan tới keyword trong N phút gần nhất.

    Ba tầng, tất định (không gọi LLM):
      1. Khớp chuỗi nguyên văn — chắc chắn nhất.
      2. Khớp theo token nội dung (bỏ dấu, bỏ stopword) — bắt được trường hợp
         học viên diễn giải lại khác cách giảng viên nói. Đây là fix cho lỗi
         false-negative ở lượt đo 001 (case C1_08, C4_04).
      3. Không tầng nào khớp → trả `unconfirmed` KÈM các đoạn gần nhất, và ghi
         rõ là CHƯA xác nhận khớp, để node trả lời tự phán xét. Không tự nhận
         là "found" — giữ nguyên guardrail chống bịa nguồn của lớp ①.
    """
    transcript = state.get("rolling_transcript") or []
    if not transcript:
        return {"status": "not_found", "reason": "chưa có transcript nào trong buổi"}

    in_window = _in_window(transcript, window_minutes)
    if not in_window:
        return {"status": "not_found", "reason": "không có transcript trong khoảng thời gian này"}

    keyword_lower = keyword.strip().lower()
    if keyword_lower:
        exact = [seg for seg in in_window if keyword_lower in seg.text.lower()]
        if exact:
            return {"status": "found", "match_type": "exact", "matches": [_as_dict(s) for s in exact]}

        key_tokens = _content_tokens(keyword)
        if key_tokens:
            scored = []
            for seg in in_window:
                overlap = len(key_tokens & _content_tokens(seg.text)) / len(key_tokens)
                if overlap >= _MIN_TOKEN_OVERLAP:
                    scored.append((overlap, seg))
            if scored:
                scored.sort(key=lambda pair: pair[0], reverse=True)
                return {
                    "status": "found",
                    "match_type": "token_overlap",
                    "matches": [_as_dict(seg) for _, seg in scored],
                }

    return {
        "status": "unconfirmed",
        "reason": (
            f"không có đoạn nào khớp rõ với '{keyword}' — dưới đây là các đoạn gần nhất, "
            "CHƯA được xác nhận là có chứa câu trả lời"
        ),
        "recent_segments": [_as_dict(seg) for seg in in_window[-5:]],
    }


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
