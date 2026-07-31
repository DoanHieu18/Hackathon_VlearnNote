"""StateGraph LangGraph cho VlearnNote.

Hai graph tách biệt nhưng dùng chung `AgentState`:
  - `ingest_graph`  : mỗi segment transcript mới -> classify -> note_writer (có điều kiện)
  - `question_graph`: câu hỏi học viên -> route_intent -> catch_up_qa / session_recap / out_of_scope

Quyết định AI thật nằm ở `classify_segment_node` và `route_intent_node` — cả
hai đều gọi `invoke_with_timeout` (agent/llm.py), không hardcode câu trả lời.
"""

from __future__ import annotations

import logging

from langgraph.graph import END, StateGraph
from pydantic import ValidationError

from agent.llm import invoke_with_timeout
from agent.prompts import (
    ASK_CLARIFY_PROMPT,
    CATCH_UP_ANSWER_PROMPT,
    CLASSIFY_SEGMENT_PROMPT,
    OUT_OF_SCOPE_REFUSAL_PROMPT,
    ROUTE_INTENT_PROMPT,
)
from agent.schemas import DEFAULT_WINDOW_MINUTES, IntentRoute, SegmentClassification
from agent.state import AgentState, SessionNote
from agent.tools import get_session_notes, search_transcript

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Luồng 1 — ingest transcript liên tục
# ---------------------------------------------------------------------------


def classify_segment_node(state: AgentState) -> dict:
    segment = state["incoming_segment"]
    if segment is None:
        return {}

    result: SegmentClassification = invoke_with_timeout(
        [
            {"role": "system", "content": CLASSIFY_SEGMENT_PROMPT},
            {
                "role": "user",
                "content": f'[{segment.speaker} @ {segment.timestamp_s:.0f}s]: "{segment.text}"',
            },
        ],
        response_format=SegmentClassification,
    )
    return {"classification": result.model_dump()}


def note_writer_node(state: AgentState) -> dict:
    classification = state["classification"]
    segment = state["incoming_segment"]
    if not classification or not classification["is_note_worthy"] or segment is None:
        return {}

    note = SessionNote(
        segment_text=segment.text,
        timestamp_s=segment.timestamp_s,
        label=classification["label"],
        summary=classification["summary"],
        source_speaker=classification.get("speaker", segment.speaker),
    )
    return {"session_notes": [note]}


def route_after_classification(state: AgentState) -> str:
    classification = state["classification"]
    if classification and classification["is_note_worthy"]:
        return "note_writer"
    return END


def build_ingest_graph():
    graph = StateGraph(AgentState)
    graph.add_node("classify_segment", classify_segment_node)
    graph.add_node("note_writer", note_writer_node)
    graph.set_entry_point("classify_segment")
    graph.add_conditional_edges(
        "classify_segment",
        route_after_classification,
        {"note_writer": "note_writer", END: END},
    )
    graph.add_edge("note_writer", END)
    return graph.compile()


# ---------------------------------------------------------------------------
# Luồng 2 — câu hỏi catch-up của học viên
# ---------------------------------------------------------------------------


def route_intent_node(state: AgentState) -> dict:
    question = state["student_question"]
    try:
        route: IntentRoute = invoke_with_timeout(
            [
                {"role": "system", "content": ROUTE_INTENT_PROMPT},
                {"role": "user", "content": question or ""},
            ],
            response_format=IntentRoute,
        )
    except ValidationError as exc:
        # Model trả structured output không khớp schema. Không được để sập cả lượt
        # hỏi của học viên (đúng lỗi đã gặp ở case Q03) — rơi về `unclear` để hỏi
        # lại, là đường an toàn nhất: không đoán nội dung, không bịa nguồn.
        logger.warning("route_intent tra ve output khong hop le, rot ve 'unclear': %s", exc)
        return {
            "route_decision": {
                "intent": "unclear",
                "keyword": "",
                "window_minutes": DEFAULT_WINDOW_MINUTES,
                "fallback_reason": "invalid_structured_output",
            }
        }
    return {"route_decision": route.model_dump()}


def catch_up_qa_node(state: AgentState) -> dict:
    decision = state["route_decision"]
    keyword = decision.get("keyword") or ""
    window = decision.get("window_minutes") or 10.0

    observation = (
        search_transcript(state, keyword, window)
        if keyword
        else get_session_notes(state)
    )

    answer = invoke_with_timeout(
        [
            {"role": "system", "content": CATCH_UP_ANSWER_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Câu hỏi học viên: {state['student_question']}\n"
                    f"Observation (nguồn sự thật duy nhất): {observation}"
                ),
            },
        ]
    )
    return {"qa_answer": {"text": answer.content, "observation": observation}}


def session_recap_node(state: AgentState) -> dict:
    observation = get_session_notes(state)
    answer = invoke_with_timeout(
        [
            {"role": "system", "content": CATCH_UP_ANSWER_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Học viên muốn tổng hợp lại cả buổi.\n"
                    f"Observation (nguồn sự thật duy nhất): {observation}"
                ),
            },
        ]
    )
    return {"qa_answer": {"text": answer.content, "observation": observation}}


def ask_clarify_node(state: AgentState) -> dict:
    """Lớp ② — tin nhắn không rõ nội dung: hỏi lại thay vì đoán (HAX G10)."""
    answer = invoke_with_timeout(
        [
            {"role": "system", "content": ASK_CLARIFY_PROMPT},
            {"role": "user", "content": state["student_question"] or ""},
        ]
    )
    return {"qa_answer": {"text": answer.content, "observation": None}}


def out_of_scope_node(state: AgentState) -> dict:
    answer = invoke_with_timeout(
        [
            {"role": "system", "content": OUT_OF_SCOPE_REFUSAL_PROMPT},
            {"role": "user", "content": state["student_question"] or ""},
        ]
    )
    return {"qa_answer": {"text": answer.content, "observation": None}}


def route_after_intent(state: AgentState) -> str:
    return state["route_decision"]["intent"]


def build_question_graph():
    graph = StateGraph(AgentState)
    graph.add_node("route_intent", route_intent_node)
    graph.add_node("catch_up_qa", catch_up_qa_node)
    graph.add_node("session_recap", session_recap_node)
    graph.add_node("out_of_scope", out_of_scope_node)
    graph.add_node("ask_clarify", ask_clarify_node)
    graph.set_entry_point("route_intent")
    graph.add_conditional_edges(
        "route_intent",
        route_after_intent,
        {
            "catch_up": "catch_up_qa",
            "session_recap": "session_recap",
            "out_of_scope": "out_of_scope",
            "unclear": "ask_clarify",
        },
    )
    graph.add_edge("catch_up_qa", END)
    graph.add_edge("session_recap", END)
    graph.add_edge("out_of_scope", END)
    graph.add_edge("ask_clarify", END)
    return graph.compile()


ingest_graph = build_ingest_graph()
question_graph = build_question_graph()
