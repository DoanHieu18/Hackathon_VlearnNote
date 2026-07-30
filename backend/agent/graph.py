"""StateGraph LangGraph cho VlearnNote.

Hai graph tách biệt nhưng dùng chung `AgentState`:
  - `ingest_graph`  : mỗi segment transcript mới -> classify -> note_writer (có điều kiện)
  - `question_graph`: câu hỏi học viên -> route_intent -> catch_up_qa / session_recap / out_of_scope

Quyết định AI thật nằm ở `classify_segment_node` và `route_intent_node` — cả
hai đều gọi `invoke_with_timeout` (agent/llm.py), không hardcode câu trả lời.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from agent.llm import invoke_with_timeout
from agent.prompts import (
    CATCH_UP_ANSWER_PROMPT,
    CLASSIFY_SEGMENT_PROMPT,
    OUT_OF_SCOPE_REFUSAL_PROMPT,
    ROUTE_INTENT_PROMPT,
)
from agent.schemas import IntentRoute, SegmentClassification
from agent.state import AgentState, SessionNote
from agent.tools import get_session_notes, search_transcript

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
        source_speaker=segment.speaker,
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
    route: IntentRoute = invoke_with_timeout(
        [
            {"role": "system", "content": ROUTE_INTENT_PROMPT},
            {"role": "user", "content": question or ""},
        ],
        response_format=IntentRoute,
    )
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
    graph.set_entry_point("route_intent")
    graph.add_conditional_edges(
        "route_intent",
        route_after_intent,
        {
            "catch_up": "catch_up_qa",
            "session_recap": "session_recap",
            "out_of_scope": "out_of_scope",
        },
    )
    graph.add_edge("catch_up_qa", END)
    graph.add_edge("session_recap", END)
    graph.add_edge("out_of_scope", END)
    return graph.compile()


ingest_graph = build_ingest_graph()
question_graph = build_question_graph()
