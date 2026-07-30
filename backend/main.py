import asyncio
import json
import logging
import time

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from agent.graph import ingest_graph, question_graph
from agent.state import AgentState, TranscriptSegment
from mock_stt import stream_transcript_from_file

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

# Sử dụng stream từ file mock thay vì hardcode.


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
        file_path = r"c:\Users\doanh\OneDrive\Documents\SE\VinUni\Week 1\day5\Hackathon_VlearnNote\data\vlearn-pack\transcript\transcript-06-clean.md"
        
        buffer_segments = []
        try:
            logger.info("Bắt đầu ingest_worker từ file...")
            async for item in stream_transcript_from_file(file_path, delay_seconds=4.0):
                segment = TranscriptSegment(
                    speaker=item["speaker"],
                    text=item["text"],
                    timestamp_s=time.monotonic() - start_time,
                )
                
                # 1. Trả ngay lên giao diện cho người dùng đọc (phụ đề realtime)
                await websocket.send_json(
                    {"event": "transcript", "speaker": segment.speaker, "text": segment.text, "is_final": True}
                )
                
                # 2. Lưu vào state tổng
                session_state["rolling_transcript"].append(segment)
                buffer_segments.append(segment)
                
                # 3. Gom thành một đoạn văn trước khi đưa vào LLM (ở đây cấu hình gom 3 câu)
                if len(buffer_segments) >= 3:
                    combined_text = " ".join([f"[{s.speaker}]: {s.text}" for s in buffer_segments])
                    
                    # Tạo segment tổng hợp
                    combined_segment = TranscriptSegment(
                        speaker="Mixed",
                        text=combined_text,
                        timestamp_s=buffer_segments[0].timestamp_s
                    )
                    
                    try:
                        result = await asyncio.to_thread(
                            ingest_graph.invoke,
                            {"incoming_segment": combined_segment, "rolling_transcript": session_state["rolling_transcript"]},
                        )
                        logger.info(f"=== KẾT QUẢ PHÂN LOẠI LLM ===\nText: {combined_text}\nClassification: {result.get('classification')}")
                    except Exception as exc:
                        logger.error("classify_segment loi: %s", exc)
                        buffer_segments = []
                        continue

                    new_notes = result.get("session_notes") or []
                    if new_notes:
                        session_state["session_notes"].extend(new_notes)
                        await websocket.send_json(_note_to_event(new_notes[0]))
                        
                    buffer_segments = [] # Xoá buffer để gom đoạn tiếp theo
        except Exception as e:
            logger.error("ingest_worker crashed: %s", e)

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
                asyncio.create_task(question_worker(message["text"]))
    except WebSocketDisconnect:
        logger.info("Client disconnected")
        ingest_task.cancel()
    except Exception as e:
        logger.error(f"Error: {e}")
        ingest_task.cancel()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
