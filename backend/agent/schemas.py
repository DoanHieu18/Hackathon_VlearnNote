"""Schema structured-output — ép LLM trả đúng field, tránh parse chuỗi tự do."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SegmentClassification(BaseModel):
    is_note_worthy: bool = Field(description="Đoạn này có đáng ghi thành note không")
    label: Literal["definition", "example", "exam_warning", "action_item", "ambiguous", "none", "key_point", "insight", "student_insight"]
    summary: str = Field(description="Tóm tắt ngắn bám sát nguyên văn, rỗng nếu không note")
    speaker: str = Field(default="Unknown", description="Người nói chính trong đoạn (ví dụ: Giảng viên, Học viên, Hệ thống, v.v...)")


DEFAULT_WINDOW_MINUTES = 10.0


class IntentRoute(BaseModel):
    intent: Literal["catch_up", "session_recap", "out_of_scope", "unclear"]
    keyword: str = Field(default="", description="Từ khoá chính nếu học viên nhắc tới")
    # Prompt cho phép model trả `null` khi học viên không nói rõ khoảng thời gian,
    # nên schema PHẢI nhận None rồi tự quy về mặc định. Trước đây khai `float`
    # cứng khiến pydantic raise và làm sập cả lượt hỏi của học viên (case Q03).
    window_minutes: float | None = Field(
        default=DEFAULT_WINDOW_MINUTES, description="Khoảng phút muốn xem lại, null nếu không rõ"
    )

    @field_validator("window_minutes", mode="after")
    @classmethod
    def _default_window(cls, value: float | None) -> float:
        if value is None or value <= 0:
            return DEFAULT_WINDOW_MINUTES
        return value
