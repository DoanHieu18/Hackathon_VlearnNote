import asyncio
import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

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

MOCK_TRANSCRIPTS = [
    {"event": "transcript", "speaker": "Teacher", "text": "Chào các em. Hôm nay chúng ta sẽ bắt đầu học về Agent trong AI.", "is_final": True},
    {"event": "transcript", "speaker": "Teacher", "text": "Các em có hiểu Agent là gì không?", "is_final": True},
    {"event": "transcript", "speaker": "Student A", "text": "Thưa thầy, Agent có phải là một chương trình có khả năng tự động thực hiện các tác vụ không ạ?", "is_final": True},
    {"event": "transcript", "speaker": "Teacher", "text": "Đúng rồi. Nó có thể nhận thức môi trường và hành động để đạt được mục tiêu.", "is_final": True},
    {"event": "transcript", "speaker": "Teacher", "text": "Vậy thành phần quan trọng nhất của một Agent là gì?", "is_final": True},
    {"event": "transcript", "speaker": "Student B", "text": "Em nghĩ là bộ nhớ (memory) và công cụ (tools) ạ.", "is_final": True},
    {"event": "transcript", "speaker": "Teacher", "text": "Chính xác, thêm cả khả năng lập kế hoạch (planning) nữa.", "is_final": True},
]

MOCK_SUMMARIES = [
    {"event": "agent_analysis", "type": "summary", "content": "Mở đầu: Định nghĩa cơ bản về Agent trong AI."},
    {"event": "agent_analysis", "type": "question", "content": "Học viên hỏi: Agent có phải chương trình tự động? -> Đáp: Đúng, có nhận thức và hành động."},
    {"event": "agent_analysis", "type": "summary", "content": "Các thành phần cốt lõi của Agent: Memory (bộ nhớ), Tools (công cụ), Planning (lập kế hoạch)."},
]

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected to /ws/stream")
    
    # Run a background task to simulate AI emitting data
    async def mock_ai_worker():
        transcript_idx = 0
        summary_idx = 0
        
        while True:
            await asyncio.sleep(4) # Every 4 seconds emit a transcript
            if transcript_idx < len(MOCK_TRANSCRIPTS):
                await websocket.send_json(MOCK_TRANSCRIPTS[transcript_idx])
                transcript_idx += 1
                
                # Emit summary every 2-3 transcripts
                if transcript_idx % 2 == 0 and summary_idx < len(MOCK_SUMMARIES):
                    await asyncio.sleep(1) # wait a bit before summary
                    await websocket.send_json(MOCK_SUMMARIES[summary_idx])
                    summary_idx += 1
            else:
                break
                
    task = asyncio.create_task(mock_ai_worker())
    
    try:
        while True:
            # Receive audio chunks from client
            data = await websocket.receive_bytes()
            # In a real app, we would send this data to STT here
            # For mock, we just ignore the audio data and let the mock_ai_worker do the job
            pass
    except WebSocketDisconnect:
        logger.info("Client disconnected")
        task.cancel()
    except Exception as e:
        logger.error(f"Error: {e}")
        task.cancel()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
