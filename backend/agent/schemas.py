"""Schema structured-output — ép LLM trả đúng field, tránh parse chuỗi tự do."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SegmentClassification(BaseModel):
    is_note_worthy: bool = Field(description="Đoạn này có đáng ghi thành note không")
    label: Literal["definition", "example", "exam_warning", "action_item", "ambiguous", "none"]
    summary: str = Field(description="Tóm tắt ngắn bám sát nguyên văn, rỗng nếu không note")


class IntentRoute(BaseModel):
    intent: Literal["catch_up", "session_recap", "out_of_scope", "unclear"]
    keyword: str = Field(default="", description="Từ khoá chính nếu học viên nhắc tới")
    window_minutes: float = Field(default=10.0, description="Khoảng phút muốn xem lại")
