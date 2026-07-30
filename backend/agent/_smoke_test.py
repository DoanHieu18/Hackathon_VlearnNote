"""Smoke test nội bộ: giả lập LLM để kiểm tra routing của graph đúng, không cần API key.

Chạy: .venv/Scripts/python.exe -m agent._smoke_test
KHÔNG dùng để tính vào eval/ (đó phải là lời gọi AI thật) — đây chỉ kiểm tra
kiến trúc graph (node nối đúng nhau) trước khi tốn quota API thật.
"""

from __future__ import annotations

from unittest.mock import patch

from agent.schemas import IntentRoute, SegmentClassification
from agent.state import TranscriptSegment


def fake_invoke(messages, *, response_format=None):
    user_content = messages[-1]["content"]
    if response_format is SegmentClassification:
        if "quan trọng đấy" in user_content:
            return SegmentClassification(is_note_worthy=False, label="ambiguous", summary="")
        return SegmentClassification(
            is_note_worthy=True, label="definition", summary="Machine learning là tập con của AI."
        )
    if response_format is IntentRoute:
        if "giải hộ" in user_content or "deadline" in user_content:
            return IntentRoute(intent="out_of_scope")
        if "tổng hợp" in user_content:
            return IntentRoute(intent="session_recap")
        return IntentRoute(intent="catch_up", keyword="machine learning", window_minutes=10)

    class FakeMsg:
        content = "Đây là câu trả lời giả lập để test routing."

    return FakeMsg()


def main() -> None:
    with patch("agent.graph.invoke_with_timeout", side_effect=fake_invoke):
        from agent.graph import ingest_graph, question_graph

        segment = TranscriptSegment(
            speaker="Teacher", text="Machine learning là tập con của AI.", timestamp_s=120.0
        )
        state = ingest_graph.invoke({"incoming_segment": segment, "rolling_transcript": [segment]})
        assert len(state["session_notes"]) == 1, state
        print("[OK] ingest_graph note-worthy path:", state["session_notes"][0].summary)

        ambiguous_segment = TranscriptSegment(
            speaker="Teacher", text="Cái này quan trọng đấy.", timestamp_s=130.0
        )
        state2 = ingest_graph.invoke(
            {"incoming_segment": ambiguous_segment, "rolling_transcript": [ambiguous_segment]}
        )
        assert len(state2.get("session_notes") or []) == 0, state2
        print("[OK] ingest_graph ambiguous path: khong tao note")

        q_state = question_graph.invoke(
            {
                "student_question": "Vừa nãy thầy nói gì về machine learning?",
                "rolling_transcript": [segment],
                "session_notes": [],
            }
        )
        assert q_state["route_decision"]["intent"] == "catch_up", q_state
        print("[OK] question_graph catch_up route:", q_state["qa_answer"]["text"])

        q_state2 = question_graph.invoke(
            {
                "student_question": "AI ơi giải hộ em bài tập này",
                "rolling_transcript": [],
                "session_notes": [],
            }
        )
        assert q_state2["route_decision"]["intent"] == "out_of_scope", q_state2
        print("[OK] question_graph out_of_scope route:", q_state2["qa_answer"]["text"])

    print("\nAll smoke tests passed.")


if __name__ == "__main__":
    main()
