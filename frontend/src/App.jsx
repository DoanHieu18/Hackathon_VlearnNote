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
  const [activeTab, setActiveTab] = useState('live');
  const [activeNoteFilter, setActiveNoteFilter] = useState('all');
  const [theme, setTheme] = useState(() => localStorage.getItem('vln-theme') || 'light');

  const wsRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const transcriptEndRef = useRef(null);

  // Apply theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('vln-theme', theme);
  }, [theme]);

  // Auto-scroll transcripts
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcripts]);

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
        const msg = JSON.parse(event.data);
        console.log('Message:', msg);

        if (msg.event === 'transcript') {
          setTranscripts((prev) => [...prev, msg]);
        } else if (msg.event === 'agent_analysis') {
          if (msg.type === 'summary' || msg.type === 'question') {
            const newNote = {
              id: Date.now() + Math.random(),
              type: msg.type === 'summary' ? 'definition' : 'example',
              content: msg.content,
              source: msg.source || null,
              timestamp_s: msg.timestamp_s,
            };
            setAgentNotes((prev) => [...prev, newNote]);
          }
        } else if (msg.event === 'qa_response') {
          setQaResponse(msg);
        }
      };

      ws.onerror = (err) => console.error('WebSocket error:', err);
      ws.onclose = () => {
        console.log('WebSocket closed');
        setIsConnected(false);
      };
    } catch (err) {
      console.error('Error connecting:', err);
      alert('Không thể kết nối microphone');
    }
  };

  const disconnect = () => {
    if (mediaRecorderRef.current) mediaRecorderRef.current.stop();
    if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop());
    if (wsRef.current) wsRef.current.close();
    setIsConnected(false);
  };

  const handleToggleConnect = () => (isConnected ? disconnect() : connect());

  const handleAskQuestion = async () => {
    if (!question.trim()) return;
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ event: 'question', text: question }));
      setQuestion('');
    }
  };

  const handleDeleteNote = (id) => setAgentNotes((prev) => prev.filter((n) => n.id !== id));

  const handleStartEdit = (note) => {
    setEditingNoteId(note.id);
    setEditContent(note.content);
  };

  const handleSaveEdit = (id) => {
    setAgentNotes((prev) => prev.map((n) => (n.id === id ? { ...n, content: editContent } : n)));
    setEditingNoteId(null);
    setEditContent('');
  };

  const handleCancelEdit = () => {
    setEditingNoteId(null);
    setEditContent('');
  };

  const filteredNotes =
    activeNoteFilter === 'all' ? agentNotes : agentNotes.filter((n) => n.type === activeNoteFilter);

  const stats = {
    transcripts: transcripts.length,
    notes: agentNotes.length,
    definitions: agentNotes.filter((n) => n.type === 'definition').length,
    examples: agentNotes.filter((n) => n.type === 'example').length,
    warnings: agentNotes.filter((n) => n.type === 'exam_warning').length,
  };

  const noteTypeLabel = {
    definition: '📚 Định nghĩa',
    example: '💡 Ví dụ',
    exam_warning: '⚠️ Cảnh báo thi',
    action_item: '✅ Hành động',
  };

  const fmtTime = (s) =>
    `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

  return (
    <div className="app-container">
      {/* ── Header ── */}
      <header className="app-header">
        <div className="header-left">
          <h1 className="app-logo">
            <span className="logo-dot" />
            VlearnNote
          </h1>

          <nav className="tab-nav" role="tablist">
            <button
              role="tab"
              className={`tab-btn ${activeTab === 'live' ? 'active' : ''}`}
              onClick={() => setActiveTab('live')}
            >
              🎙️ Live
            </button>
            <button
              role="tab"
              className={`tab-btn ${activeTab === 'notes' ? 'active' : ''}`}
              onClick={() => setActiveTab('notes')}
            >
              📝 Notes{agentNotes.length > 0 && ` (${agentNotes.length})`}
            </button>
            <button
              role="tab"
              className={`tab-btn ${activeTab === 'analytics' ? 'active' : ''}`}
              onClick={() => setActiveTab('analytics')}
            >
              📊 Analytics
            </button>
          </nav>
        </div>

        <div className="header-right">
          <button
            className="btn-theme"
            onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
            title={theme === 'dark' ? 'Chuyển sang sáng' : 'Chuyển sang tối'}
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>

          <button
            id="btn-record"
            className={`btn-record ${isConnected ? 'recording' : ''}`}
            onClick={handleToggleConnect}
          >
            <span className="rec-dot" />
            {isConnected ? 'Dừng lại' : 'Bắt đầu'}
          </button>
        </div>
      </header>

      {/* ── Main ── */}
      <main className="app-main">
        {/* ── Live Tab ── */}
        {activeTab === 'live' && (
          <div className="tab-content live-tab">
            <div className="live-grid">
              {/* Transcript */}
              <div className="live-panel transcript-panel">
                <div className="panel-header">
                  <h2>Transcript Live</h2>
                  {isConnected && (
                    <span className="status-badge pulse">🔴 Recording</span>
                  )}
                </div>
                <div className="panel-body">
                  {transcripts.length === 0 ? (
                    <div className="empty-state">
                      <div className="empty-icon">🎙️</div>
                      <h3>Chưa có transcript</h3>
                      <p>Bấm "Bắt đầu" để kết nối và nhận transcript realtime từ AI</p>
                    </div>
                  ) : (
                    <div className="transcript-list">
                      {transcripts.map((t, idx) => (
                        <div key={idx} className="transcript-item">
                          <span className="speaker">{t.speaker}</span>
                          <span className="text">{t.text}</span>
                        </div>
                      ))}
                      <div ref={transcriptEndRef} />
                    </div>
                  )}
                </div>
              </div>

              {/* Notes Preview */}
              <div className="live-panel notes-preview-panel">
                <div className="panel-header">
                  <h2>Notes Preview</h2>
                  <button className="link-btn" onClick={() => setActiveTab('notes')}>
                    Xem tất cả →
                  </button>
                </div>
                <div className="panel-body">
                  {agentNotes.length === 0 ? (
                    <div className="empty-state">
                      <div className="empty-icon">📝</div>
                      <h3>Chưa có ghi chú</h3>
                      <p>AI sẽ tạo note tự động khi phát hiện nội dung quan trọng</p>
                    </div>
                  ) : (
                    <div className="notes-list">
                      {agentNotes
                        .slice(-5)
                        .reverse()
                        .map((note) => (
                          <div key={note.id} className={`note-card mini note-${note.type}`}>
                            <span className="note-type-badge">
                              {noteTypeLabel[note.type] || note.type}
                            </span>
                            <p className="note-content">{note.content}</p>
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Q&A */}
            <div className="qa-panel">
              <div className="qa-header">
                <h3>💬 Hỏi Catch-up</h3>
              </div>
              <div className="qa-input-group">
                <input
                  id="qa-input"
                  type="text"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAskQuestion()}
                  placeholder="Vừa nãy thầy nói gì về Agent?"
                  className="qa-input"
                  disabled={!isConnected}
                />
                <button
                  id="btn-ask"
                  className="btn-ask"
                  onClick={handleAskQuestion}
                  disabled={!isConnected || !question.trim()}
                >
                  Hỏi
                </button>
              </div>
              {qaResponse && (
                <div className="qa-response">
                  <div className="qa-label">✨ Câu trả lời</div>
                  <p className="qa-answer">{qaResponse.answer}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Notes Tab ── */}
        {activeTab === 'notes' && (
          <div className="tab-content notes-tab">
            <div className="notes-header">
              <h2>Tất cả ghi chú</h2>
              <div className="subtab-nav">
                <button
                  className={`subtab-btn ${activeNoteFilter === 'all' ? 'active' : ''}`}
                  onClick={() => setActiveNoteFilter('all')}
                >
                  Tất cả ({agentNotes.length})
                </button>
                <button
                  className={`subtab-btn ${activeNoteFilter === 'definition' ? 'active' : ''}`}
                  onClick={() => setActiveNoteFilter('definition')}
                >
                  📚 Định nghĩa ({stats.definitions})
                </button>
                <button
                  className={`subtab-btn ${activeNoteFilter === 'example' ? 'active' : ''}`}
                  onClick={() => setActiveNoteFilter('example')}
                >
                  💡 Ví dụ ({stats.examples})
                </button>
                <button
                  className={`subtab-btn ${activeNoteFilter === 'exam_warning' ? 'active' : ''}`}
                  onClick={() => setActiveNoteFilter('exam_warning')}
                >
                  ⚠️ Cảnh báo ({stats.warnings})
                </button>
                <button
                  className={`subtab-btn ${activeNoteFilter === 'action_item' ? 'active' : ''}`}
                  onClick={() => setActiveNoteFilter('action_item')}
                >
                  ✅ Hành động
                </button>
              </div>
            </div>

            <div className="notes-grid">
              {filteredNotes.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">📝</div>
                  <h3>
                    Chưa có ghi chú
                    {activeNoteFilter !== 'all' ? ` loại "${activeNoteFilter}"` : ''}
                  </h3>
                  <p>AI sẽ tự động tạo note khi phát hiện nội dung quan trọng</p>
                </div>
              ) : (
                filteredNotes.map((note) => (
                  <div key={note.id} className={`note-card full note-${note.type}`}>
                    <div className="note-header">
                      <span className="note-type-badge">
                        {noteTypeLabel[note.type] || note.type}
                      </span>
                      {note.timestamp_s !== undefined && (
                        <span className="note-timestamp">⏱️ {fmtTime(note.timestamp_s)}</span>
                      )}
                    </div>

                    {editingNoteId === note.id ? (
                      <div className="note-edit">
                        <textarea
                          value={editContent}
                          onChange={(e) => setEditContent(e.target.value)}
                          className="note-edit-input"
                          autoFocus
                        />
                        <div className="note-edit-actions">
                          <button className="btn-save" onClick={() => handleSaveEdit(note.id)}>
                            ✓ Lưu
                          </button>
                          <button className="btn-cancel" onClick={handleCancelEdit}>
                            ✕ Huỷ
                          </button>
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
                          <button className="btn-icon" onClick={() => handleStartEdit(note)}>
                            ✏️ Sửa
                          </button>
                          <button
                            className="btn-icon btn-delete"
                            onClick={() => handleDeleteNote(note.id)}
                          >
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
        )}

        {/* ── Analytics Tab ── */}
        {activeTab === 'analytics' && (
          <div className="tab-content analytics-tab">
            <h2>📊 Thống kê buổi học</h2>
            <div className="stats-grid">
              {[
                { icon: '🎙️', value: stats.transcripts, label: 'Transcript segments' },
                { icon: '📝', value: stats.notes,        label: 'Tổng số notes' },
                { icon: '📚', value: stats.definitions,  label: 'Định nghĩa' },
                { icon: '💡', value: stats.examples,     label: 'Ví dụ' },
                { icon: '⚠️', value: stats.warnings,    label: 'Cảnh báo thi' },
              ].map(({ icon, value, label }) => (
                <div key={label} className="stat-card">
                  <div className="stat-icon">{icon}</div>
                  <div className="stat-value">{value}</div>
                  <div className="stat-label">{label}</div>
                </div>
              ))}
            </div>

            <div className="chart-section">
              <h3>Note distribution</h3>
              <div className="chart-placeholder">
                <p>📊 Chart placeholder — thêm chart library sau</p>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
