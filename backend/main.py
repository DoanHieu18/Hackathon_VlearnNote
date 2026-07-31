import asyncio
import base64
import json
import logging
import time
import shutil
import os
import re
import sqlite3
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

try:
    src_icon = r'C:\Users\dinhl\.gemini\antigravity-ide\brain\d5665087-bb5a-4323-81d5-f3dc40349744\media__1785433212588.png'
    src_full = r'C:\Users\dinhl\.gemini\antigravity-ide\brain\d5665087-bb5a-4323-81d5-f3dc40349744\media__1785433345999.jpg'
    dst_dir = r'd:\Hackathon_VlearnNote\frontend\public\brand'
    os.makedirs(dst_dir, exist_ok=True)
    if os.path.exists(src_icon):
        shutil.copy(src_icon, os.path.join(dst_dir, 'user-v-logo.png'))
    if os.path.exists(src_full):
        shutil.copy(src_full, os.path.join(dst_dir, 'vlearn-logo-full.jpg'))
except Exception as _e:
    pass

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from agent.graph import ingest_graph, question_graph
from agent.state import AgentState, SessionNote, TranscriptSegment
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


# API lấy danh sách transcript files
@app.get("/api/transcript-files")
async def get_transcript_files():
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    transcript_dir = os.path.join(base_dir, "..", "data", "vlearn-pack", "transcript")

    files = []
    for f in os.listdir(transcript_dir):
        if f.startswith("transcript-") and f.endswith("-clean.md"):
            file_path = os.path.join(transcript_dir, f)
            # Đọc metadata từ file
            with open(file_path, 'r', encoding='utf-8') as fp:
                lines = fp.readlines()
                title = "Unknown"
                for line in lines[:10]:
                    if line.startswith("# Transcript"):
                        title = line.replace("# Transcript bài giảng (bản sạch) — ", "").strip()
                        break

            files.append({
                "filename": f,
                "title": title,
                "display_name": f.replace("transcript-", "Buổi ").replace("-clean.md", "")
            })

    files.sort(key=lambda x: x["filename"])
    return {"files": files}


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vlearnnote.db")
AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session_audio")
APP_TIMEZONE = ZoneInfo("Asia/Bangkok")
os.makedirs(AUDIO_DIR, exist_ok=True)


def _db_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _init_db():
    with _db_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_email TEXT NOT NULL DEFAULT '',
                start_time INTEGER NOT NULL,
                session_date TEXT NOT NULL,
                data_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        chat_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(chat_messages)").fetchall()
        }
        if "session_id" not in chat_columns:
            connection.execute(
                "ALTER TABLE chat_messages ADD COLUMN session_id TEXT NOT NULL DEFAULT ''"
            )


_init_db()


@app.post("/api/sessions/save")
async def save_session(data: dict):
    session_id = data.get("session_id")
    if not session_id:
        return {"success": False, "error": "session_id is required"}
    start_time = int(data.get("start_time") or time.time() * 1000)
    session_date = datetime.fromtimestamp(start_time / 1000, tz=APP_TIMEZONE).date().isoformat()
    user_email = data.get("user_email") or ""
    notes = data.get("notes") or []
    data["total_notes"] = len(notes)
    data["approved_notes"] = sum(
        1 for note in notes if note.get("reviewStatus", "approved") == "approved"
    )
    data["pending_notes"] = sum(
        1 for note in notes if note.get("reviewStatus") == "pending"
    )
    with _db_connection() as connection:
        connection.execute(
            """
            INSERT INTO sessions(session_id, user_email, start_time, session_date, data_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                user_email=excluded.user_email,
                start_time=excluded.start_time,
                session_date=excluded.session_date,
                data_json=excluded.data_json
            """,
            (session_id, user_email, start_time, session_date, json.dumps(data, ensure_ascii=False)),
        )
    logger.info(f"💾 Saved session: {session_id}")
    return {"success": True, "session_id": session_id}


@app.get("/api/sessions/list")
async def list_sessions(user_email: str = ""):
    with _db_connection() as connection:
        if user_email:
            rows = connection.execute(
                "SELECT data_json FROM sessions WHERE user_email = ? ORDER BY start_time DESC",
                (user_email,),
            ).fetchall()
        else:
            rows = connection.execute("SELECT data_json FROM sessions ORDER BY start_time DESC").fetchall()
    sessions = []
    for row in rows:
        session = json.loads(row["data_json"])
        session_id = session.get("session_id")
        if session_id and os.path.exists(os.path.join(AUDIO_DIR, f"{session_id}.webm")):
            session["audio_url"] = f"/api/sessions/{session_id}/audio"
        sessions.append(session)
    return {"sessions": sessions}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    with _db_connection() as connection:
        row = connection.execute(
            "SELECT data_json FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
    if row:
        session = json.loads(row["data_json"])
        if os.path.exists(os.path.join(AUDIO_DIR, f"{session_id}.webm")):
            session["audio_url"] = f"/api/sessions/{session_id}/audio"
        return session
    return {"error": "Session not found"}, 404


@app.put("/api/sessions/{session_id}/notes")
async def update_session_notes(session_id: str, data: dict):
    user_email = str(data.get("user_email") or "")
    notes = data.get("notes")
    if not isinstance(notes, list):
        return {"success": False, "error": "notes must be a list"}

    with _db_connection() as connection:
        row = connection.execute(
            "SELECT user_email, data_json FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if not row:
            return {"success": False, "error": "Session not found"}
        if row["user_email"] and user_email and row["user_email"] != user_email:
            return {"success": False, "error": "Session ownership mismatch"}

        session_data = json.loads(row["data_json"])
        session_data["notes"] = notes
        session_data["total_notes"] = len(notes)
        session_data["approved_notes"] = sum(
            1 for note in notes if note.get("reviewStatus", "approved") == "approved"
        )
        session_data["pending_notes"] = sum(
            1 for note in notes if note.get("reviewStatus") == "pending"
        )
        connection.execute(
            "UPDATE sessions SET data_json = ? WHERE session_id = ?",
            (json.dumps(session_data, ensure_ascii=False), session_id),
        )
    return {"success": True, "session_id": session_id, "total_notes": len(notes)}


@app.patch("/api/sessions/{session_id}")
async def update_session_metadata(session_id: str, data: dict):
    title = str(data.get("title") or "").strip()
    user_email = str(data.get("user_email") or "")
    if not title:
        return {"success": False, "error": "title is required"}
    with _db_connection() as connection:
        row = connection.execute(
            "SELECT user_email, data_json FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if not row:
            return {"success": False, "error": "Session not found"}
        if row["user_email"] and row["user_email"] != user_email:
            return {"success": False, "error": "Session ownership mismatch"}
        session_data = json.loads(row["data_json"])
        session_data["title"] = title
        connection.execute(
            "UPDATE sessions SET data_json = ? WHERE session_id = ?",
            (json.dumps(session_data, ensure_ascii=False), session_id),
        )
    return {"success": True, "session_id": session_id, "title": title}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str, user_email: str = ""):
    with _db_connection() as connection:
        row = connection.execute(
            "SELECT user_email FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if not row:
            return {"success": False, "error": "Session not found"}
        if row["user_email"] and row["user_email"] != user_email:
            return {"success": False, "error": "Session ownership mismatch"}
        connection.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        connection.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
    audio_path = os.path.join(AUDIO_DIR, f"{session_id}.webm")
    if os.path.exists(audio_path):
        os.remove(audio_path)
    return {"success": True, "session_id": session_id}


@app.post("/api/sessions/{session_id}/audio")
async def save_session_audio(session_id: str, data: dict):
    audio_data = str(data.get("audio_base64") or "")
    user_email = str(data.get("user_email") or "")
    if not audio_data:
        return {"success": False, "error": "audio_base64 is required"}
    with _db_connection() as connection:
        row = connection.execute(
            "SELECT user_email FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
    if not row:
        return {"success": False, "error": "Session not found"}
    if row["user_email"] and row["user_email"] != user_email:
        return {"success": False, "error": "Session ownership mismatch"}
    try:
        raw_audio = base64.b64decode(audio_data.split(",", 1)[-1])
        audio_path = os.path.join(AUDIO_DIR, f"{session_id}.webm")
        with open(audio_path, "wb") as audio_file:
            audio_file.write(raw_audio)
    except (ValueError, OSError) as exc:
        return {"success": False, "error": f"Could not save audio: {exc}"}
    return {"success": True, "audio_url": f"/api/sessions/{session_id}/audio"}


@app.get("/api/sessions/{session_id}/audio")
async def get_session_audio(session_id: str):
    audio_path = os.path.join(AUDIO_DIR, f"{session_id}.webm")
    if not os.path.exists(audio_path):
        return {"error": "Audio not found"}, 404
    return FileResponse(audio_path, media_type="audio/webm", filename=f"{session_id}.webm")


def _save_chat_message(user_email: str, role: str, content: str, session_id: str = ""):
    with _db_connection() as connection:
        connection.execute(
            "INSERT INTO chat_messages(user_email, role, content, created_at, session_id) VALUES (?, ?, ?, ?, ?)",
            (user_email or "guest", role, content, datetime.now(timezone.utc).isoformat(), session_id or ""),
        )


@app.get("/api/chat/history")
async def chat_history(user_email: str = "guest", session_id: str = ""):
    with _db_connection() as connection:
        if session_id:
            rows = connection.execute(
                "SELECT role, content, created_at FROM chat_messages WHERE user_email = ? AND session_id = ? ORDER BY id ASC LIMIT 200",
                (user_email or "guest", session_id),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT role, content, created_at FROM chat_messages WHERE user_email = ? AND session_id = '' ORDER BY id ASC LIMIT 200",
                (user_email or "guest",),
            ).fetchall()
    return {"messages": [dict(row) for row in rows]}


@app.get("/api/analytics/daily")
async def daily_analytics(user_email: str = ""):
    with _db_connection() as connection:
        params = ()
        where = ""
        if user_email:
            where = "WHERE user_email = ?"
            params = (user_email,)
        rows = connection.execute(
            f"SELECT session_date, data_json FROM sessions {where} ORDER BY session_date ASC", params
        ).fetchall()

    totals = {}
    for row in rows:
        data = json.loads(row["data_json"])
        day = totals.setdefault(row["session_date"], {"date": row["session_date"], "sessions": 0, "transcripts": 0, "notes": 0, "approved_notes": 0, "pending_notes": 0})
        day["sessions"] += 1
        day["transcripts"] += int(data.get("total_segments") or len(data.get("transcripts") or []))
        day["notes"] += int(data.get("total_notes") or len(data.get("notes") or []))
        notes = data.get("notes") or []
        day["approved_notes"] += int(data.get("approved_notes") or sum(1 for note in notes if note.get("reviewStatus", "approved") == "approved"))
        day["pending_notes"] += int(data.get("pending_notes") or sum(1 for note in notes if note.get("reviewStatus") == "pending"))
    return {"days": list(totals.values())}


def _fallback_note(segments: list[TranscriptSegment]) -> SessionNote | None:
    source = " ".join(segment.text for segment in segments)
    clean = re.sub(r"\*\*\[T\d+-\d+\]\*\*\s*", "", source).strip()
    lowered = clean.lower()
    high_importance_terms = ("quan trọng", "cần nhớ", "lưu ý", "bắt buộc", "mấu chốt", "nguyên tắc", "kết luận", "tóm lại", "không nên", "phải hiểu")
    learning_terms = ("định nghĩa", "nghĩa là", "được hiểu là", "ví dụ", "cần làm", "bước tiếp theo", "thứ nhất", "thứ hai", "giải pháp", "rủi ro")
    ai_practice_terms = (
        "ai", "machine learning", "deep learning", "llm", "agent", "transformer", "attention",
        "prompt", "rag", "embedding", "vector", "model", "mô hình", "dữ liệu", "data",
        "automation", "tự động hóa", "workflow", "use case", "bài toán", "evaluation", "đánh giá",
        "metric", "chỉ số", "api", "triển khai", "deployment", "hallucination", "token", "fine-tune",
        "ràng buộc", "constraint", "technical debt",
    )
    importance_score = sum(6 for term in high_importance_terms if term in lowered)
    importance_score += sum(3 for term in learning_terms if term in lowered)
    importance_score += 2 if any(term in lowered for term in ("vì vậy", "do đó", "suy ra", "dẫn đến", "điều này cho thấy")) else 0
    ai_practice_score = sum(
        1
        for term in ai_practice_terms
        if (re.search(r"\bai\b", lowered) if term == "ai" else term in lowered)
    )
    if importance_score < 6 or ai_practice_score < 1:
        return None
    if any(word in lowered for word in ("ví dụ", "chẳng hạn", "minh họa")):
        label = "example"
    elif any(word in lowered for word in ("lưu ý", "quan trọng", "cần nhớ", "bắt buộc", "tránh")):
        label = "exam_warning"
    elif any(word in lowered for word in ("cần làm", "hãy", "nhiệm vụ", "bước tiếp theo")):
        label = "action_item"
    else:
        label = "definition"
    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", clean) if len(sentence.strip()) >= 25]
    importance_terms = ("quan trọng", "cần nhớ", "lưu ý", "định nghĩa", "nghĩa là", "ví dụ", "cần làm", "bắt buộc", "mấu chốt")
    ranked = sorted(
        sentences or [clean],
        key=lambda sentence: sum(3 for term in importance_terms if term in sentence.lower()) + sum(
            1
            for term in ai_practice_terms
            if (re.search(r"\bai\b", sentence.lower()) if term == "ai" else term in sentence.lower())
        ),
        reverse=True,
    )
    summary = re.sub(r"^(thì|đấy là|cái này là|như vậy là|ở đây thì)\s+", "", ranked[0], flags=re.IGNORECASE)
    if len(summary) > 180:
        summary = summary[:177].rsplit(" ", 1)[0] + "..."
    return SessionNote(
        segment_text=source,
        timestamp_s=segments[0].timestamp_s,
        label=label,
        summary=summary,
        source_speaker=segments[0].speaker,
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

    # Nhận tham số transcript file từ client
    init_message = await websocket.receive_json()
    transcript_file = init_message.get("transcript_file", "transcript-06-clean.md")
    user_email = init_message.get("user_email") or "guest"
    session_id = init_message.get("session_id") or ""
    logger.info(f"Client chọn file: {transcript_file}")

    session_state: AgentState = {"rolling_transcript": [], "session_notes": []}
    start_time = time.monotonic()

    async def ingest_worker():
        nonlocal session_state
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, "..", "data", "vlearn-pack", "transcript", transcript_file)

        if not os.path.exists(file_path):
            logger.error(f"File không tồn tại: {file_path}")
            await websocket.send_json({"event": "error", "message": f"File {transcript_file} không tồn tại"})
            return

        buffer_segments = []
        last_fallback_note_at = -6
        try:
            logger.info(f"Bắt đầu ingest_worker từ file: {transcript_file}")
            async for item in stream_transcript_from_file(file_path, delay_seconds=2.0):
                segment = TranscriptSegment(
                    speaker=item["speaker"],
                    text=item["text"],
                    timestamp_s=time.monotonic() - start_time,
                )

                # 1. Trả ngay lên giao diện cho người dùng đọc (phụ đề realtime)
                await websocket.send_json(
                    {
                        "event": "transcript",
                        "speaker": segment.speaker,
                        "text": segment.text,
                        "timestamp_s": segment.timestamp_s,
                        "is_final": True,
                    }
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
                        logger.info(f"=== KẾT QUẢ PHÂN LOẠI LLM ===\nText: {combined_text[:100]}...\nClassification: {result.get('classification')}")
                    except Exception as exc:
                        logger.error("classify_segment loi: %s", exc)
                        fallback_note = (
                            _fallback_note(buffer_segments)
                            if len(session_state["rolling_transcript"]) - last_fallback_note_at >= 9
                            else None
                        )
                        if fallback_note:
                            session_state["session_notes"].append(fallback_note)
                            await websocket.send_json(_note_to_event(fallback_note))
                            last_fallback_note_at = len(session_state["rolling_transcript"])
                        buffer_segments = []
                        continue

                    new_notes = result.get("session_notes") or []
                    if new_notes:
                        session_state["session_notes"].extend(new_notes)
                        await websocket.send_json(_note_to_event(new_notes[0]))
                    else:
                        fallback_note = (
                            _fallback_note(buffer_segments)
                            if len(session_state["rolling_transcript"]) - last_fallback_note_at >= 9
                            else None
                        )
                        if fallback_note:
                            session_state["session_notes"].append(fallback_note)
                            await websocket.send_json(_note_to_event(fallback_note))
                            last_fallback_note_at = len(session_state["rolling_transcript"])

                    buffer_segments = [] # Xoá buffer để gom đoạn tiếp theo

            # Khi stream kết thúc, gửi event complete
            await websocket.send_json({
                "event": "stream_complete",
                "total_segments": len(session_state["rolling_transcript"]),
                "total_notes": len(session_state["session_notes"])
            })
            logger.info(f"✅ Stream hoàn tất: {len(session_state['rolling_transcript'])} segments, {len(session_state['session_notes'])} notes")
        except Exception as e:
            logger.error("ingest_worker crashed: %s", e, exc_info=True)

    async def question_worker(raw_text: str):
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.error("Invalid JSON from client: %s", raw_text)
            return
        question = payload.get("question")
        if not question:
            logger.warning("No question in payload")
            return

        logger.info(f"📝 Received question: {question}")
        _save_chat_message(user_email, "user", question, session_id)
        logger.info(f"📊 Current state - Transcript: {len(session_state['rolling_transcript'])} segments, Notes: {len(session_state['session_notes'])} notes")

        try:
            result = await asyncio.to_thread(
                question_graph.invoke,
                {
                    "student_question": question,
                    "rolling_transcript": session_state["rolling_transcript"],
                    "session_notes": session_state["session_notes"],
                },
            )
            logger.info(f"✅ Q&A Success - Intent: {result['route_decision']['intent']}")
        except Exception as exc:  # noqa: BLE001 — guardrail, không để câu hỏi lỗi làm sập kết nối
            logger.error(f"❌ Q&A Error: {type(exc).__name__}: {exc}", exc_info=True)
            fallback_answer = "Mình chưa thể gọi mô hình AI lúc này. Câu hỏi đã được lưu và bạn vẫn có thể tra cứu bằng transcript cùng ghi chú của buổi học."
            _save_chat_message(user_email, "assistant", fallback_answer, session_id)
            await websocket.send_json(
                {
                    "event": "qa_answer",
                    "answer": fallback_answer,
                    "intent": "error",
                }
            )
            return

        answer_text = result["qa_answer"]["text"]
        _save_chat_message(user_email, "assistant", answer_text, session_id)
        await websocket.send_json(
            {
                "event": "qa_answer",
                "answer": answer_text,
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


@app.post("/api/chat")
async def chat_without_stream(data: dict):
    question = str(data.get("question") or "").strip()
    user_email = str(data.get("user_email") or "guest")
    session_id = str(data.get("session_id") or "")
    if not question:
        return {"error": "question is required"}

    _save_chat_message(user_email, "user", question, session_id)
    try:
        result = await asyncio.to_thread(
            question_graph.invoke,
            {"student_question": question, "rolling_transcript": [], "session_notes": []},
        )
        answer = result["qa_answer"]["text"]
        intent = result["route_decision"]["intent"]
    except Exception as exc:
        logger.error("Standalone chat error: %s", exc)
        answer = "Mình chưa tìm thấy câu trả lời trong dữ liệu bài học hiện tại. Hãy bắt đầu một buổi học hoặc hỏi về nội dung đã được phiên âm."
        intent = "error"
    _save_chat_message(user_email, "assistant", answer, session_id)
    return {"answer": answer, "intent": intent}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
