import { useState, useEffect, useRef } from 'react';
import './App.css';

function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [transcripts, setTranscripts] = useState([]);
  const [agentNotes, setAgentNotes] = useState([]);
  const [question, setQuestion] = useState('');
  const [qaResponse, setQaResponse] = useState(null);
  const [editingNoteId, setEditingNoteId] = useState(null);
  const [editContent, setEditContent] = useState('');
  const wsRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);

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

        // Send data every 250ms
        mediaRecorder.start(250);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Received:', data);

        if (data.event === 'transcript') {
          setTranscripts((prev) => [...prev, data]);
        } else if (data.event === 'agent_analysis') {
          setAgentNotes((prev) => [...prev, { ...data, id: Date.now() + Math.random() }]);
        } else if (data.event === 'qa_response') {
          setQaResponse(data);
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
      streamRef.current.getTracks().forEach(track => track.stop());
    }
  };

  const handleToggleConnect = () => {
    if (isConnected) {
      stopRecording();
    } else {
      connect();
    }
  };

  const handleAskQuestion = () => {
    if (!question.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }
    wsRef.current.send(JSON.stringify({ type: 'question', text: question }));
    setQuestion('');
  };

  const handleDeleteNote = (noteId) => {
    setAgentNotes((prev) => prev.filter(n => n.id !== noteId));
  };

  const handleStartEdit = (note) => {
    setEditingNoteId(note.id);
    setEditContent(note.content);
  };

  const handleSaveEdit = (noteId) => {
    setAgentNotes((prev) => prev.map(n =>
      n.id === noteId ? { ...n, content: editContent } : n
    ));
    setEditingNoteId(null);
    setEditContent('');
  };

  const handleCancelEdit = () => {
    setEditingNoteId(null);
    setEditContent('');
  };

  return (
    <div className="container">
      <header className="header">
        <h1>VlearnNote</h1>
        <button
          className={`btn ${isConnected ? 'btn-stop' : 'btn-start'}`}
          onClick={handleToggleConnect}
        >
          {isConnected ? 'Dừng ghi âm' : 'Bắt đầu ghi âm'}
        </button>
      </header>

      {/* Banner phạm vi (G2) */}
      <div className="scope-banner">
        <span className="banner-label">Phạm vi</span>
        <p>AI note tự động các đoạn có tín hiệu quan trọng trong buổi học. <strong>Không</strong> thay thế ghi chép, <strong>không</strong> giải bài tập, <strong>không</strong> xử lý logistics.</p>
      </div>

      <div className="main-content">
        <div className="panel transcripts-panel">
          <h2>Transcript Live</h2>
          <div className="list-container">
            {transcripts.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">🎙️</div>
                <h3>Chưa có transcript</h3>
                <p>Bấm "Bắt đầu ghi âm" để kết nối và nhận transcript realtime từ buổi học.</p>
              </div>
            ) : (
              transcripts.map((t, idx) => (
                <div key={idx} className="transcript-item">
                  <span className="speaker">[{t.speaker}]</span>
                  <span className="text">{t.text}</span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="panel notes-panel">
          <div className="panel-header">
            <h2>Agent Notes</h2>
            {isConnected && agentNotes.length === 0 && (
              <span className="status-badge status-listening">🎯 Đang lắng nghe...</span>
            )}
          </div>
          <div className="list-container">
            {agentNotes.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">📝</div>
                <h3>Chưa có ghi chú</h3>
                <p>AI sẽ tự động tạo note khi phát hiện nội dung quan trọng (định nghĩa, ví dụ, cảnh báo thi).</p>
              </div>
            ) : (
              agentNotes.map((note) => (
                <div key={note.id} className={`note-card note-${note.type}`}>
                  <div className="note-header">
                    <span className="note-label">{note.type}</span>
                    {note.timestamp_s !== undefined && (
                      <span className="note-timestamp">
                        ⏱️ {Math.floor(note.timestamp_s / 60)}:{String(Math.floor(note.timestamp_s % 60)).padStart(2, '0')}
                      </span>
                    )}
                  </div>

                  {editingNoteId === note.id ? (
                    <div className="note-edit">
                      <textarea
                        value={editContent}
                        onChange={(e) => setEditContent(e.target.value)}
                        className="note-edit-input"
                      />
                      <div className="note-edit-actions">
                        <button className="btn-save" onClick={() => handleSaveEdit(note.id)}>✓ Lưu</button>
                        <button className="btn-cancel" onClick={handleCancelEdit}>✕ Huỷ</button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <p className="note-content">{note.content}</p>
                      {note.source && (
                        <details className="note-source-details">
                          <summary>📄 Xem nguồn gốc</summary>
                          <p className="note-source">"{note.source}"</p>
                        </details>
                      )}
                      <div className="note-actions">
                        <button className="btn-icon" onClick={() => handleStartEdit(note)} title="Sửa nội dung">
                          ✏️ Sửa
                        </button>
                        <button className="btn-icon btn-delete" onClick={() => handleDeleteNote(note.id)} title="Xoá note">
                          🗑️ Xoá
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Q&A Panel */}
      <div className="qa-panel">
        <div className="qa-header">
          <h3>💬 Hỏi catch-up</h3>
          {!isConnected && (
            <span className="qa-hint">Kết nối trước để hỏi</span>
          )}
        </div>
        <div className="qa-input-group">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAskQuestion()}
            placeholder="Vừa nãy thầy nói gì về Agent? 🤔"
            className="qa-input"
            disabled={!isConnected}
          />
          <button
            className="btn-ask"
            onClick={handleAskQuestion}
            disabled={!isConnected || !question.trim()}
          >
            {isConnected ? '📤 Hỏi' : '🔒 Hỏi'}
          </button>
        </div>

        {qaResponse && (
          <div className="qa-response">
            <div className="qa-response-header">
              <span className="qa-response-icon">✨</span>
              <span className="qa-response-label">Câu trả lời</span>
            </div>
            <p className="qa-answer">{qaResponse.answer}</p>
            {qaResponse.observation && qaResponse.observation.status === 'found' && (
              <details className="qa-observation">
                <summary>🔍 Xem chi tiết nguồn</summary>
                <pre>{JSON.stringify(qaResponse.observation, null, 2)}</pre>
              </details>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
