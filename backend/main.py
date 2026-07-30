import asyncio
import json
import logging
import time

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from agent.graph import ingest_graph, question_graph
from agent.state import AgentState, TranscriptSegment

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sketch/Mock: nguồn transcript giả lập một buổi live thật (không có pipeline
# STT nối mic thật trong phạm vi hackathon) — ghi rõ trong spec §4 là phần mock.
# Nội dung transcript AI THẬT chạy qua `ingest_graph` (agent/graph.py), không
# hardcode kết quả note.
MOCK_TRANSCRIPTS = [
    {"speaker": "Teacher", "text": "Chào các em. Hôm nay chúng ta sẽ bắt đầu học về Agent trong AI."},
    {"speaker": "Teacher", "text": "Các em có hiểu Agent là gì không?"},
    {
        "speaker": "Student A",
        "text": "Thưa thầy, Agent có phải là một chương trình có khả năng tự động thực hiện các tác vụ không ạ?",
    },
    {"speaker": "Teacher", "text": "Đúng rồi. Nó có thể nhận thức môi trường và hành động để đạt được mục tiêu."},
    {"speaker": "Teacher", "text": "Cái này quan trọng đấy, mọi người nhớ kỹ nhé."},
    {"speaker": "Teacher", "text": "Vậy thành phần quan trọng nhất của một Agent là gì?"},
    {"speaker": "Student B", "text": "Em nghĩ là bộ nhớ (memory) và công cụ (tools) ạ."},
    {"speaker": "Teacher", "text": "Chính xác, thêm cả khả năng lập kế hoạch (planning) nữa."},
]


def _note_to_event(note) -> dict:
    return {
        "event": "agent_analysis",
        "type": note.label,
        "content": note.summary,
        "timestamp_s": note.timestamp_s,
        "source": note.segment_text,
    }


@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected to /ws/stream")

    session_state: AgentState = {"rolling_transcript": [], "session_notes": []}
    start_time = time.monotonic()

    async def ingest_worker():
        nonlocal session_state
        for item in MOCK_TRANSCRIPTS:
            await asyncio.sleep(4)
            segment = TranscriptSegment(
                speaker=item["speaker"],
                text=item["text"],
                timestamp_s=time.monotonic() - start_time,
            )
            await websocket.send_json(
                {"event": "transcript", "speaker": segment.speaker, "text": segment.text, "is_final": True}
            )

            try:
                result = await asyncio.to_thread(
                    ingest_graph.invoke,
                    {"incoming_segment": segment, "rolling_transcript": [segment]},
                )
            except Exception as exc:  # noqa: BLE001 — 1 segment lỗi không được làm sập cả stream
                logger.error("classify_segment loi: %s", exc)
                continue

            session_state["rolling_transcript"].append(segment)
            new_notes = result.get("session_notes") or []
            if new_notes:
                session_state["session_notes"].extend(new_notes)
                await websocket.send_json(_note_to_event(new_notes[0]))

    async def question_worker(raw_text: str):
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            return
        question = payload.get("question")
        if not question:
            return

        try:
            result = await asyncio.to_thread(
                question_graph.invoke,
                {
                    "student_question": question,
                    "rolling_transcript": session_state["rolling_transcript"],
                    "session_notes": session_state["session_notes"],
                },
            )
        except Exception as exc:  # noqa: BLE001 — guardrail, không để câu hỏi lỗi làm sập kết nối
            logger.error("route_intent loi: %s", exc)
            await websocket.send_json(
                {
                    "event": "qa_answer",
                    "answer": "Hệ thống đang bận, bạn hỏi lại sau vài giây nhé.",
                    "intent": "error",
                }
            )
            return

        await websocket.send_json(
            {
                "event": "qa_answer",
                "answer": result["qa_answer"]["text"],
                "intent": result["route_decision"]["intent"],
            }
        )

    ingest_task = asyncio.create_task(ingest_worker())

    try:
        while True:
            message = await websocket.receive()
            if message.get("bytes") is not None:
                # Audio thật (mic) — trong Sketch này bỏ qua vì chưa nối STT thật.
                continue
            if message.get("text") is not None:
                await question_worker(message["text"])
    except WebSocketDisconnect:
        logger.info("Client disconnected")
        ingest_task.cancel()
    except Exception as e:
        logger.error(f"Error: {e}")
        ingest_task.cancel()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
