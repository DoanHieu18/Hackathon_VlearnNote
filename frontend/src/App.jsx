import { useState, useEffect, useRef } from 'react';
import './App.css';

function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [transcripts, setTranscripts] = useState([]);
  const [agentNotes, setAgentNotes] = useState([]);
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
          setAgentNotes((prev) => [...prev, data]);
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

  return (
    <div className="container">
      <header className="header">
        <h1>VLearn - Realtime Agent</h1>
        <button 
          className={`btn ${isConnected ? 'btn-stop' : 'btn-start'}`}
          onClick={handleToggleConnect}
        >
          {isConnected ? 'Stop Recording' : 'Start Recording'}
        </button>
      </header>

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
            {agentNotes.map((n, idx) => (
              <div key={idx} className={`note-item note-${n.type}`}>
                <span className="note-type">{n.type.toUpperCase()}</span>
                <p className="note-content">{n.content}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
