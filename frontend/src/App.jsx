import { useState, useEffect, useRef } from 'react';
import './App.css';

const LABEL_TEXT = {
  definition: 'ĐỊNH NGHĨA',
  example: 'VÍ DỤ',
  exam_warning: 'LƯU Ý THI',
  action_item: 'VIỆC CẦN LÀM',
};

function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [transcripts, setTranscripts] = useState([]);
  const [agentNotes, setAgentNotes] = useState([]);
  const [qaHistory, setQaHistory] = useState([]);
  const [question, setQuestion] = useState('');
  const [asking, setAsking] = useState(false);
  const wsRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const noteIdRef = useRef(0);

  const connect = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const ws = new WebSocket('ws://localhost:8000/ws/stream');
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        console.log('Connected to backend');

        const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        mediaRecorderRef.current = mediaRecorder;

        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
            ws.send(event.data);
          }
        };

        mediaRecorder.start(250);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Received:', data);

        if (data.event === 'transcript') {
          setTranscripts((prev) => [...prev, data]);
        } else if (data.event === 'agent_analysis') {
          noteIdRef.current += 1;
          setAgentNotes((prev) => [
            ...prev,
            { ...data, id: noteIdRef.current, confirmed: false, editing: false },
          ]);
        } else if (data.event === 'qa_answer') {
          setAsking(false);
          setQaHistory((prev) => [...prev, { role: 'assistant', text: data.answer, intent: data.intent }]);
        }
      };

      ws.onclose = () => {
        console.log('Disconnected');
        stopRecording();
      };

      ws.onerror = (error) => {
        console.error('WebSocket Error:', error);
        stopRecording();
      };
    } catch (err) {
      console.error('Error accessing microphone:', err);
      alert('Could not access microphone. Ensure you are on localhost and grant permissions.');
    }
  };

  const stopRecording = () => {
    setIsConnected(false);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.close();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
    }
  };

  const handleToggleConnect = () => {
    if (isConnected) {
      stopRecording();
    } else {
      connect();
    }
  };

  // --- Note actions (HAX G9 — sửa/xoá dễ dàng ngay trên output) ---

  const confirmNote = (id) => {
    setAgentNotes((prev) => prev.map((n) => (n.id === id ? { ...n, confirmed: true } : n)));
  };

  const deleteNote = (id) => {
    setAgentNotes((prev) => prev.filter((n) => n.id !== id));
  };

  const startEditNote = (id) => {
    setAgentNotes((prev) => prev.map((n) => (n.id === id ? { ...n, editing: true } : n)));
  };

  const saveEditNote = (id, newContent) => {
    setAgentNotes((prev) =>
      prev.map((n) => (n.id === id ? { ...n, content: newContent, editing: false, confirmed: true } : n))
    );
  };

  // --- Catch-up Q&A (câu hỏi học viên gửi bất kỳ lúc nào, không cần đợi mic) ---

  const askQuestion = () => {
    const text = question.trim();
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    setQaHistory((prev) => [...prev, { role: 'student', text }]);
    setAsking(true);
    wsRef.current.send(JSON.stringify({ question: text }));
    setQuestion('');
  };

  return (
    <div className="container">
      <header className="header">
        <h1>VLearn - Realtime Note Agent</h1>
        <button
          className={`btn ${isConnected ? 'btn-stop' : 'btn-start'}`}
          onClick={handleToggleConnect}
        >
          {isConnected ? 'Stop Recording' : 'Start Recording'}
        </button>
      </header>

      <div className="scope-banner">
        AI tự động ghi chú các đoạn có tín hiệu quan trọng trong buổi học và trả lời câu hỏi
        &ldquo;bắt kịp&rdquo; dựa trên transcript của buổi này — không thay thế ghi chép của bạn,
        không giải bài tập hộ, không xử lý câu hỏi logistics (deadline/nộp bài).
      </div>

      <div className="main-content">
        <div className="panel transcripts-panel">
          <h2>Live Transcript</h2>
          <div className="list-container">
            {transcripts.map((t, idx) => (
              <div key={idx} className="transcript-item">
                <span className="speaker">[{t.speaker}]: </span>
                <span className="text">{t.text}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="panel notes-panel">
          <h2>Agent Notes</h2>
          <div className="list-container">
            {agentNotes.map((n) => (
              <NoteCard
                key={n.id}
                note={n}
                onConfirm={() => confirmNote(n.id)}
                onDelete={() => deleteNote(n.id)}
                onStartEdit={() => startEditNote(n.id)}
                onSaveEdit={(text) => saveEditNote(n.id, text)}
              />
            ))}
          </div>
        </div>

        <div className="panel qa-panel">
          <h2>Hỏi lại / Bắt kịp bài</h2>
          <div className="list-container">
            {qaHistory.length === 0 && (
              <p className="qa-empty">
                Bị lỡ mất một đoạn? Hỏi ví dụ: &ldquo;vừa nãy thầy nói gì về X&rdquo; hoặc
                &ldquo;tóm tắt lại giúp em&rdquo;.
              </p>
            )}
            {qaHistory.map((m, idx) => (
              <div key={idx} className={`qa-message qa-${m.role}`}>
                {m.role === 'assistant' && m.intent === 'out_of_scope' && (
                  <span className="qa-intent-tag">ngoài phạm vi</span>
                )}
                <p>{m.text}</p>
              </div>
            ))}
            {asking && <p className="qa-thinking">Đang tra lại transcript…</p>}
          </div>
          <div className="qa-composer">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && askQuestion()}
              placeholder="Hỏi AI về nội dung vừa qua..."
              disabled={!isConnected}
            />
            <button onClick={askQuestion} disabled={!isConnected || asking}>
              Hỏi
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function NoteCard({ note, onConfirm, onDelete, onStartEdit, onSaveEdit }) {
  const [draft, setDraft] = useState(note.content);
  const isDraftState = !note.confirmed && !note.editing;

  return (
    <div className={`note-item note-${note.type} ${isDraftState ? 'note-draft' : ''}`}>
      <div className="note-header">
        <span className="note-type">{LABEL_TEXT[note.type] || note.type.toUpperCase()}</span>
        {isDraftState && <span className="note-draft-tag">nháp — chờ xác nhận</span>}
      </div>

      {note.editing ? (
        <div className="note-edit">
          <textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={2} />
          <button onClick={() => onSaveEdit(draft)}>Lưu</button>
        </div>
      ) : (
        <p className="note-content">{note.content}</p>
      )}

      <div className="note-actions">
        {isDraftState && <button onClick={onConfirm}>Xác nhận</button>}
        {!note.editing && <button onClick={onStartEdit}>Sửa</button>}
        <button onClick={onDelete}>Xoá</button>
      </div>
    </div>
  );
}

export default App;
