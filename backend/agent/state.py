"""Domain models (bất biến) + schema state cho LangGraph.

`TranscriptSegment`/`SessionNote` là dữ liệu bất biến — node không sửa instance
cũ, chỉ tạo cái mới. `AgentState` là TypedDict theo đúng API của LangGraph
(`StateGraph` cần một state schema có reducer khai qua `Annotated`); mỗi node
vẫn phải trả về một dict MỚI mô tả phần state cần cập nhật — không mutate
state nhận vào — LangGraph sẽ tự gộp (reduce) vào state tổng.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass
from typing import Annotated, Literal, TypedDict


@dataclass(frozen=True)
class TranscriptSegment:
    speaker: str
    text: str
    timestamp_s: float


@dataclass(frozen=True)
class SessionNote:
    segment_text: str
    timestamp_s: float
    label: Literal["definition", "example", "exam_warning", "action_item"]
    summary: str
    source_speaker: str


class AgentState(TypedDict, total=False):
    """State dùng chung cho cả luồng ingest (note tự động) và luồng hỏi-đáp."""

    rolling_transcript: Annotated[list[TranscriptSegment], operator.add]
    session_notes: Annotated[list[SessionNote], operator.add]
    incoming_segment: TranscriptSegment | None
    classification: dict | None
    student_question: str | None
    route_decision: dict | None
    qa_answer: dict | None
