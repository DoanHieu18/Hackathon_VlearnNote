import { useState, useEffect, useRef } from 'react';
import {
  AlertTriangle,
  BarChart3,
  BookOpen,
  Bot,
  CheckCircle2,
  Clock3,
  Download,
  ExternalLink,
  FileCode2,
  FileJson2,
  FolderOpen,
  KeyRound,
  LineChart,
  Lightbulb,
  LockKeyhole,
  LogOut,
  Mail,
  MessageCircle,
  Mic,
  Moon,
  Pencil,
  Pin,
  PieChart,
  RefreshCw,
  Send,
  Sparkles,
  StickyNote,
  Sun,
  Trash2,
  X,
} from 'lucide-react';
import './App.css';

// Logo VinUni - sử dụng ảnh thật từ /brand/user-v-logo.png
const VinUniLogo = ({ size = 36 }) => (
  <img
    src="/brand/user-v-logo.png"
    alt="VinUni Logo"
    style={{ width: size, height: size, objectFit: 'contain' }}
  />
);

const LABEL_TEXT = {
  definition: 'ĐỊNH NGHĨA',
  example: 'VÍ DỤ',
  exam_warning: 'LƯU Ý THI',
  action_item: 'VIỆC CẦN LÀM',
  key_point: 'Ý CHÍNH',
  insight: 'KIẾN THỨC',
  student_insight: 'Ý KIẾN HỌC VIÊN',
};

const NOTE_ICONS = {
  definition: BookOpen,
  example: Lightbulb,
  exam_warning: AlertTriangle,
  action_item: CheckCircle2,
  key_point: Pin,
  insight: Sparkles,
  student_insight: MessageCircle,
};

const API_BASE_URL = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8001`;
const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');

const UiIcon = ({ icon: Icon, size = 18, ...props }) => (
  <Icon className="ui-icon" size={size} strokeWidth={1.8} aria-hidden="true" {...props} />
);

const NoteIcon = ({ type, size = 16 }) => {
  const Icon = NOTE_ICONS[type] || Pin;
  return <UiIcon icon={Icon} size={size} />;
};

function App() {
  console.log('[VLearnNote] App component rendering...');

  // Theme state (Light mode / Dark mode)
  const [theme, setTheme] = useState(() => localStorage.getItem('vlearn_theme') || 'light');

  // Auth state (VinUni Student Login)
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('vlearn_user');
    if (!saved) return null;

    try {
      const parsedUser = JSON.parse(saved);
      return parsedUser?.email && parsedUser?.studentId ? parsedUser : null;
    } catch {
      localStorage.removeItem('vlearn_user');
      return null;
    }
  });
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState('');

  // App core state
  const [isConnected, setIsConnected] = useState(false);
  const [transcripts, setTranscripts] = useState([]);
  const [agentNotes, setAgentNotes] = useState([]);
  const [qaHistoryCount, setQaHistoryCount] = useState(0);
  const [editingNoteId, setEditingNoteId] = useState(null);
  const [editContent, setEditContent] = useState('');
  const [activeTab, setActiveTab] = useState('live');
  const [activeNoteFilter, setActiveNoteFilter] = useState('all');
  const [selectedFile, setSelectedFile] = useState('transcript-01-clean.md');
  const [transcriptFiles, setTranscriptFiles] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [streamStatus, setStreamStatus] = useState('idle');
  const [streamError, setStreamError] = useState('');
  const [dailyStats, setDailyStats] = useState([]);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [sessionTitle, setSessionTitle] = useState('');
  const [isSavingSession, setIsSavingSession] = useState(false);
  const [viewingSavedSessionId, setViewingSavedSessionId] = useState(null);
  const [saveError, setSaveError] = useState('');
  const [activeSessionTitle, setActiveSessionTitle] = useState('Chưa có buổi học đang mở');
  const [noteSyncStatus, setNoteSyncStatus] = useState('idle');
  const [sessionAudioUrl, setSessionAudioUrl] = useState('');
  const [appNotice, setAppNotice] = useState(null);

  // AI Chat floating widget state
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);

  const wsRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const transcriptEndRef = useRef(null);
  const sessionStartTime = useRef(null);
  const currentSessionIdRef = useRef(null);
  const transcriptsRef = useRef([]);
  const agentNotesRef = useRef([]);
  const pendingQuestionRef = useRef('');
  const lastAutoNoteSegmentRef = useRef(-6);
  const speechRecognitionRef = useRef(null);
  const isNewRecordingRef = useRef(false);
  const audioChunksRef = useRef([]);
  const audioBlobRef = useRef(null);
  const audioStopPromiseRef = useRef(Promise.resolve());

  // Sync theme to root element
  useEffect(() => {
    localStorage.setItem('vlearn_theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // Auto scroll transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    transcriptsRef.current = transcripts;
  }, [transcripts]);

  useEffect(() => {
    agentNotesRef.current = agentNotes;
  }, [agentNotes]);

  useEffect(() => {
    if (!appNotice) return undefined;
    const timer = window.setTimeout(() => setAppNotice(null), 3500);
    return () => window.clearTimeout(timer);
  }, [appNotice]);

  // Load sessions from Backend
  useEffect(() => {
    if (!user) return;
    console.log('[VLearnNote] Loading sessions from backend...');
    fetch(`${API_BASE_URL}/api/sessions/list?user_email=${encodeURIComponent(user.email || '')}`)
      .then(res => res.json())
      .then(data => {
        if (data && Array.isArray(data.sessions)) {
          setSessions(data.sessions);
        }
      })
      .catch(err => {
        console.warn('[VLearnNote] Sessions endpoint offline:', err);
        setSessions([]);
      });
  }, [user]);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/transcript-files`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        const files = Array.isArray(data.files) ? data.files : [];
        setTranscriptFiles(files);
        setActiveSessionTitle((currentTitle) => (
          currentTitle === 'Chưa có buổi học đang mở' && files.length > 0
            ? (files[0].title || files[0].display_name)
            : currentTitle
        ));
        setSelectedFile((currentFile) => (
          currentFile && files.length > 0 && !files.some((file) => file.filename === currentFile)
            ? files[0].filename
            : currentFile
        ));
      })
      .catch((err) => console.warn('Transcript files endpoint offline:', err));
  }, []);

  useEffect(() => {
    if (!user) return;
    const email = user.email || 'guest';
    fetch(`${API_BASE_URL}/api/chat/history?user_email=${encodeURIComponent(email)}`)
      .then((res) => res.json())
      .then((data) => {
        const messages = Array.isArray(data.messages) ? data.messages : [];
        setChatMessages(messages.map(({ role, content }) => ({ role, content })));
        setQaHistoryCount(messages.filter((message) => message.role === 'user').length);
      })
      .catch((err) => console.warn('Chat history endpoint offline:', err));

    fetch(`${API_BASE_URL}/api/analytics/daily?user_email=${encodeURIComponent(email)}`)
      .then((res) => res.json())
      .then((data) => setDailyStats(Array.isArray(data.days) ? data.days : []))
      .catch((err) => console.warn('Daily analytics endpoint offline:', err));
  }, [user]);

  // Handle Login submission
  const handleLogin = (e) => {
    e.preventDefault();
    if (!loginEmail.trim() || !loginPassword.trim()) {
      setLoginError('Vui lòng nhập đầy đủ Email sinh viên và Mã học viên!');
      return;
    }
    const studentUser = {
      email: loginEmail.trim(),
      studentId: loginPassword.trim(),
      name: loginEmail.split('@')[0].toUpperCase(),
      loginTime: new Date().toISOString(),
    };
    setUser(studentUser);
    localStorage.setItem('vlearn_user', JSON.stringify(studentUser));
    setLoginError('');
  };

  const handleLogout = () => {
    if (isConnected) disconnect();
    setUser(null);
    setLoginEmail('');
    setLoginPassword('');
    setLoginError('');
    localStorage.removeItem('vlearn_user');
  };

  const buildOfflineAnswer = (questionText) => {
    const normalizedQuestion = questionText.toLowerCase().trim();
    const plainQuestion = normalizedQuestion.normalize('NFD').replace(/[\u0300-\u036f]/g, '');

    if (/^(hi|hello|hey|alo|chao|xin chao)(\s+(ban|ai|vlearn|vlearnnote))?[!.?]*$/.test(plainQuestion)) {
      return 'Chào bạn! Mình là trợ lý học tập của VLearnNote. Bạn muốn mình giải thích khái niệm nào hay tóm tắt phần bài giảng vừa học?';
    }
    if (/^(cam on|thank you|thanks|thank|ok cam on|cảm ơn)/.test(plainQuestion)) {
      return 'Không có gì! Khi cần, bạn có thể bảo mình tóm tắt bài học, tìm ý chính hoặc giải thích một khái niệm trong transcript.';
    }
    if (/ban la ai|may la ai|tro ly gi|lam duoc gi/.test(plainQuestion)) {
      return 'Mình là trợ lý học tập VLearnNote. Mình có thể tìm thông tin trong transcript, tóm tắt ý chính, giải thích khái niệm và hỗ trợ bạn xem lại ghi chú của buổi học.';
    }

    const offlineKnowledge = [
      {
        matches: ['vibe code', 'vibecode', 'vibe coding', 'vibecodes'],
        answer: 'Vibe coding là cách bạn mô tả tính năng hoặc vấn đề bằng ngôn ngữ tự nhiên để AI hỗ trợ viết và sửa code. Bạn vẫn cần chạy thử, kiểm tra lỗi và hiểu phần code quan trọng trước khi sử dụng.',
      },
      {
        matches: ['llm là gì', 'llm la gi'],
        answer: 'LLM là mô hình ngôn ngữ lớn, được huấn luyện trên lượng văn bản lớn để hiểu và tạo nội dung như trả lời câu hỏi, tóm tắt hoặc phân tích văn bản.',
      },
      {
        matches: ['agent là gì', 'agent la gi', 'ai agent'],
        answer: 'AI Agent là hệ thống dùng AI để nhận mục tiêu, lựa chọn công cụ và thực hiện nhiều bước nhằm hoàn thành nhiệm vụ thay vì chỉ trả lời một câu hỏi đơn lẻ.',
      },
      {
        matches: ['transcript là gì', 'transcript la gi', 'phiên âm là gì'],
        answer: 'Transcript là bản văn bản hóa nội dung lời nói trong buổi học. VLearnNote dùng transcript làm nguồn để tạo ghi chú và trả lời câu hỏi về bài giảng.',
      },
      {
        matches: ['ghi chú tự động', 'take note', 'take notes'],
        answer: 'Ghi chú tự động là việc hệ thống đọc transcript, nhận diện định nghĩa, ví dụ, cảnh báo và việc cần làm rồi lưu chúng thành các ý ngắn gọn để ôn tập.',
      },
    ];
    const knownAnswer = offlineKnowledge.find(({ matches }) => (
      matches.some((phrase) => normalizedQuestion.includes(phrase))
    ));
    if (knownAnswer) return knownAnswer.answer;

    const wantsSummary = /tóm tắt|tom tat|ý chính|y chinh|ghi chú|ghi chu|tổng hợp|tong hop/.test(plainQuestion);
    const asksRecentContent = /vừa nãy|vua nay|mới nói|moi noi|gần nhất|gan nhat/.test(plainQuestion);

    if (wantsSummary && agentNotesRef.current.length > 0) {
      const notes = agentNotesRef.current.slice(-3).map((note, index) => `${index + 1}. ${note.content}`);
      return `Các ý chính gần nhất của buổi học:\n${notes.join('\n')}`;
    }
    if (asksRecentContent && transcriptsRef.current.length > 0) {
      const recent = transcriptsRef.current.slice(-3).map((segment) => segment.text).join(' ');
      return `Phần nội dung gần nhất là: ${recent}`;
    }

    const stopWords = new Set(['mình', 'minh', 'bạn', 'ban', 'thầy', 'thay', 'cô', 'giảng', 'giang', 'nói', 'noi', 'được', 'duoc', 'không', 'khong', 'những', 'nhung', 'trong', 'phần', 'phan', 'về', 'cho', 'với', 'của', 'này', 'nào', 'sao', 'vậy']);
    const keywords = questionText
      .toLowerCase()
      .replace(/[^a-zA-ZÀ-ỹ0-9\s]/g, ' ')
      .split(/\s+/)
      .filter((word) => word.length >= 4 && !stopWords.has(word))
      .slice(0, 6);
    const matchingSegments = transcriptsRef.current
      .filter((segment) => keywords.some((keyword) => String(segment.text || '').toLowerCase().includes(keyword)))
      .slice(-3);

    if (matchingSegments.length > 0) {
      return `Theo nội dung buổi học: ${matchingSegments.map((segment) => segment.text).join(' ')}`;
    }
    return 'Mình chưa hiểu rõ bạn muốn hỏi phần nào. Bạn có thể hỏi cụ thể hơn, ví dụ: “Tóm tắt ý chính”, “Vừa nãy giảng viên nói gì?” hoặc “AI Agent là gì?”.';
  };

  const normalizeAiAnswer = (answer, questionText) => {
    const text = String(answer || '');
    if (!text || /connection error|openai_api_key|kiểm tra.*logs|lỗi kết nối ai/i.test(text)) {
      return buildOfflineAnswer(questionText);
    }
    return text;
  };

  const createTranscriptNote = (segments, segmentCount) => {
    const source = segments.map((segment) => segment.text || '').join(' ').trim();
    const clean = source.replace(/\*\*\[T\d+-\d+\]\*\*\s*/g, '').trim();
    const lowered = clean.toLowerCase();
    let type = 'key_point';
    if (/ví dụ|chẳng hạn|minh họa/.test(lowered)) type = 'example';
    else if (/lưu ý|quan trọng|cần nhớ|bắt buộc|tránh/.test(lowered)) type = 'exam_warning';
    else if (/định nghĩa|được hiểu là|có nghĩa là/.test(lowered)) type = 'definition';
    else if (/cần làm|hãy |nhiệm vụ|bước tiếp theo/.test(lowered)) type = 'action_item';

    const sentences = clean
      .split(/(?<=[.!?])\s+/)
      .map((sentence) => sentence.trim())
      .filter((sentence) => sentence.length >= 25);
    const highImportanceTerms = ['quan trọng', 'cần nhớ', 'lưu ý', 'bắt buộc', 'mấu chốt', 'nguyên tắc', 'kết luận', 'tóm lại', 'không nên', 'phải hiểu'];
    const learningTerms = ['định nghĩa', 'nghĩa là', 'được hiểu là', 'ví dụ', 'cần làm', 'bước tiếp theo', 'thứ nhất', 'thứ hai', 'giải pháp', 'rủi ro'];
    const aiPracticeTerms = [
      'ai', 'machine learning', 'deep learning', 'llm', 'agent', 'transformer', 'attention',
      'prompt', 'rag', 'embedding', 'vector', 'model', 'mô hình', 'dữ liệu', 'data',
      'automation', 'tự động hóa', 'workflow', 'use case', 'bài toán', 'evaluation',
      'đánh giá', 'metric', 'chỉ số', 'api', 'triển khai', 'deployment', 'hallucination',
      'token', 'fine-tune', 'fine tune', 'ràng buộc', 'constraint', 'technical debt',
    ];
    const contextScore = highImportanceTerms.reduce(
      (total, term) => total + (lowered.includes(term) ? 6 : 0),
      0,
    ) + learningTerms.reduce(
      (total, term) => total + (lowered.includes(term) ? 3 : 0),
      0,
    ) + (/vì vậy|do đó|suy ra|dẫn đến|điều này cho thấy/.test(lowered) ? 2 : 0);
    const containsAiTerm = (text, term) => (
      term === 'ai'
        ? /(^|[\s,.;:()])ai($|[\s,.;:()])/.test(text)
        : text.includes(term)
    );
    const aiPracticeScore = aiPracticeTerms.reduce(
      (total, term) => total + (containsAiTerm(lowered, term) ? 1 : 0),
      0,
    );

    if (contextScore < 6 || aiPracticeScore < 1) return null;

    const importanceTerms = [...highImportanceTerms, ...learningTerms, ...aiPracticeTerms, 'vì vậy', 'do đó', 'dẫn đến'];
    const ranked = sentences
      .map((sentence, index) => ({
        sentence,
        score: importanceTerms.reduce(
          (total, term) => total + (containsAiTerm(sentence.toLowerCase(), term) ? 3 : 0),
          index === 0 ? 1 : 0,
        ),
      }))
      .sort((a, b) => b.score - a.score);
    const selectedSentence = ranked[0]?.sentence || clean;
    const conciseSentence = selectedSentence
      .replace(/^(thì|đấy là|cái này là|như vậy là|ở đây thì)\s+/i, '')
      .replace(/\s+/g, ' ')
      .trim();
    const content = conciseSentence.length > 180
      ? `${conciseSentence.slice(0, 177).replace(/\s+\S*$/, '')}...`
      : conciseSentence;
    return {
      id: `local-note-${segmentCount}`,
      type,
      content,
      source,
      timestamp_s: segments[0]?.timestamp_s || 0,
      isFallback: true,
      reviewStatus: 'pending',
    };
  };

  const sourceExcerpt = (source) => {
    const clean = String(source || '').replace(/\*\*\[T\d+-\d+\]\*\*\s*/g, '').replace(/\s+/g, ' ').trim();
    return clean.length > 150 ? `${clean.slice(0, 147).replace(/\s+\S*$/, '')}...` : clean;
  };

  // AI Chat handler - gửi câu hỏi và nhận trả lời
  const handleChatSend = async () => {
    if (!chatInput.trim() || isChatLoading) return;

    const userMessage = { role: 'user', content: chatInput.trim() };
    pendingQuestionRef.current = userMessage.content;
    setChatMessages(prev => [...prev, userMessage]);
    setChatInput('');
    setIsChatLoading(true);
    setQaHistoryCount((prev) => prev + 1);

    try {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ question: userMessage.content }));
        return;
      }

      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: userMessage.content,
          user_email: user.email || 'guest',
          session_id: currentSessionIdRef.current || '',
        }),
      });
      const data = await response.json();
      setChatMessages((prev) => [...prev, {
        role: 'assistant',
        content: normalizeAiAnswer(data.answer, userMessage.content),
      }]);
    } catch (err) {
      console.error('Chat error:', err);
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: buildOfflineAnswer(userMessage.content),
      }]);
    } finally {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        setIsChatLoading(false);
      }
    }
  };

  const connect = async () => {
    try {
      setViewingSavedSessionId(null);
      setSessionAudioUrl('');
      setActiveSessionTitle(selectedFile ? (selectedTranscript?.title || selectedTranscript?.display_name || 'Bài học có sẵn') : 'Buổi học mới');
      setChatMessages([]);
      setQaHistoryCount(0);
      isNewRecordingRef.current = !selectedFile;
      setStreamError('');
      setStreamStatus('connecting');
      setTranscripts([]);
      setAgentNotes([]);
      lastAutoNoteSegmentRef.current = -6;
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      if (isNewRecordingRef.current) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
          stream.getTracks().forEach((track) => track.stop());
          throw new Error('Trình duyệt chưa hỗ trợ nhận dạng giọng nói. Hãy dùng Chrome hoặc Edge.');
        }

        sessionStartTime.current = Date.now();
        const sessionId = `session_${Date.now()}`;
        setCurrentSessionId(sessionId);
        currentSessionIdRef.current = sessionId;
        setIsConnected(true);
        setStreamStatus('streaming');

        const recognition = new SpeechRecognition();
        recognition.lang = 'vi-VN';
        recognition.continuous = true;
        recognition.interimResults = false;
        recognition.onresult = (event) => {
          for (let index = event.resultIndex; index < event.results.length; index += 1) {
            if (!event.results[index].isFinal) continue;
            const text = event.results[index][0].transcript.trim();
            if (!text) continue;
            const transcriptMessage = {
              event: 'transcript',
              speaker: 'Giảng viên',
              text,
              timestamp_s: (Date.now() - sessionStartTime.current) / 1000,
              is_final: true,
            };
            setTranscripts((prev) => {
              const next = [...prev, transcriptMessage];
              if (next.length % 3 === 0 && next.length - lastAutoNoteSegmentRef.current >= 9) {
                const fallbackNote = createTranscriptNote(next.slice(-3), next.length);
                if (fallbackNote) {
                  lastAutoNoteSegmentRef.current = next.length;
                  setAgentNotes((notes) => [...notes, fallbackNote]);
                }
              }
              return next;
            });
          }
        };
        recognition.onerror = (event) => {
          if (event.error !== 'no-speech') {
            setStreamError(`Nhận dạng giọng nói gặp lỗi: ${event.error}`);
          }
        };
        recognition.onend = () => {
          if (speechRecognitionRef.current === recognition) {
            try {
              recognition.start();
            } catch (error) {
              console.warn('Không thể tiếp tục nhận dạng giọng nói:', error);
            }
          }
        };
        recognition.start();
        speechRecognitionRef.current = recognition;
        const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        audioChunksRef.current = [];
        audioBlobRef.current = null;
        audioStopPromiseRef.current = new Promise((resolve) => {
          recorder.onstop = () => {
            audioBlobRef.current = new Blob(audioChunksRef.current, { type: 'audio/webm' });
            resolve(audioBlobRef.current);
          };
        });
        recorder.ondataavailable = (event) => {
          if (event.data.size > 0) audioChunksRef.current.push(event.data);
        };
        recorder.start(500);
        mediaRecorderRef.current = recorder;
        return;
      }

      const ws = new WebSocket(`${WS_BASE_URL}/ws/stream`);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setStreamStatus('loading');
        sessionStartTime.current = Date.now();
        const sessionId = `session_${Date.now()}`;
        setCurrentSessionId(sessionId);
        currentSessionIdRef.current = sessionId;
        console.log('Connected to WebSocket server');

        ws.send(JSON.stringify({
          transcript_file: selectedFile,
          user_email: user.email || 'guest',
          session_id: sessionId,
        }));

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
        try {
          const msg = JSON.parse(event.data);
          if (msg.event === 'transcript') {
            setStreamStatus('streaming');
            setTranscripts((prev) => {
              const next = [...prev, msg];
              if (next.length % 3 === 0 && next.length - lastAutoNoteSegmentRef.current >= 9) {
                const fallbackNote = createTranscriptNote(next.slice(-3), next.length);
                if (fallbackNote) {
                  lastAutoNoteSegmentRef.current = next.length;
                  setAgentNotes((currentNotes) => (
                    currentNotes.some((note) => note.id === fallbackNote.id)
                      ? currentNotes
                      : [...currentNotes, fallbackNote]
                  ));
                }
              }
              return next;
            });
          } else if (msg.event === 'agent_analysis') {
            const newNote = {
              id: Date.now() + Math.random(),
              type: msg.type || 'definition',
              content: msg.content || msg.summary,
              source: msg.source || null,
              timestamp_s: msg.timestamp_s,
              reviewStatus: 'pending',
            };
            setAgentNotes((prev) => {
              const fallbackIndex = prev.findLastIndex((note) => note.isFallback);
              if (fallbackIndex < 0) return [...prev, newNote];
              return prev.map((note, index) => index === fallbackIndex ? newNote : note);
            });
          } else if (msg.event === 'qa_answer') {
            // Thêm câu trả lời vào chat messages
            setChatMessages(prev => [...prev, {
              role: 'assistant',
              content: normalizeAiAnswer(msg.answer, pendingQuestionRef.current)
            }]);
            setIsChatLoading(false);
          } else if (msg.event === 'stream_complete') {
            setStreamStatus('complete');
            if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
              mediaRecorderRef.current.stop();
            }
            if (streamRef.current) streamRef.current.getTracks().forEach((track) => track.stop());
            if (ws.readyState === WebSocket.OPEN) ws.close();
            setIsConnected(false);
          } else if (msg.event === 'error') {
            setStreamStatus('error');
            setStreamError(msg.message || 'Không thể đọc script đã chọn.');
          }
        } catch (err) {
          console.error('Error parsing WS message:', err);
        }
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        setStreamStatus('error');
        setStreamError(`Không kết nối được backend tại ${API_BASE_URL}.`);
      };
      ws.onclose = () => {
        console.log('WebSocket closed');
        setIsConnected(false);
        setStreamStatus((current) => current === 'error' || current === 'complete' ? current : 'idle');
      };
    } catch (err) {
      console.error('Error connecting:', err);
      setStreamStatus('error');
      setStreamError(err.message || 'Không thể truy cập microphone. Hãy cấp quyền microphone rồi thử lại.');
    }
  };

  const disconnect = () => {
    if (speechRecognitionRef.current) {
      speechRecognitionRef.current.stop();
      speechRecognitionRef.current = null;
    }
    if (mediaRecorderRef.current) mediaRecorderRef.current.stop();
    if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop());
    if (wsRef.current) wsRef.current.close();
    setIsConnected(false);
    setStreamStatus('complete');
    if (isNewRecordingRef.current && transcriptsRef.current.length > 0) {
      setSessionTitle('');
      setShowSaveDialog(true);
    }
  };

  const saveCurrentSession = async (title = '') => {
    const sessionId = currentSessionIdRef.current || currentSessionId;
    const currentTranscripts = transcriptsRef.current;
    const currentNotes = agentNotesRef.current;
    if (!sessionId || currentTranscripts.length === 0) {
      throw new Error('Buổi học chưa có transcript để lưu.');
    }

    const sessionData = {
      session_id: sessionId,
      title: title.trim() || `Buổi học ${new Date().toLocaleDateString('vi-VN')}`,
      transcript_file: selectedFile || null,
      start_time: sessionStartTime.current,
      end_time: Date.now(),
      duration_seconds: Math.floor((Date.now() - sessionStartTime.current) / 1000),
      transcripts: currentTranscripts,
      notes: currentNotes,
      user_email: user.email || '',
      total_segments: currentTranscripts.length,
      total_notes: currentNotes.length,
      approved_notes: currentNotes.filter((note) => note.reviewStatus === 'approved').length,
      pending_notes: currentNotes.filter((note) => note.reviewStatus === 'pending').length,
    };

    const saveResponse = await fetch(`${API_BASE_URL}/api/sessions/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sessionData),
    });
    const saveResult = await saveResponse.json();
    if (!saveResponse.ok || !saveResult.success) {
      throw new Error(saveResult.error || `Không thể lưu buổi học (HTTP ${saveResponse.status}).`);
    }

    const res = await fetch(`${API_BASE_URL}/api/sessions/list?user_email=${encodeURIComponent(user.email || '')}`);
    if (!res.ok) throw new Error('Đã lưu nhưng không thể tải lại lịch sử buổi học.');
    const data = await res.json();
    if (data && Array.isArray(data.sessions)) setSessions(data.sessions);
    const analyticsRes = await fetch(`${API_BASE_URL}/api/analytics/daily?user_email=${encodeURIComponent(user.email || '')}`);
    if (analyticsRes.ok) {
      const analyticsData = await analyticsRes.json();
      setDailyStats(Array.isArray(analyticsData.days) ? analyticsData.days : []);
    }
    return sessionData;
  };

  const handleSaveSession = async () => {
    setIsSavingSession(true);
    setSaveError('');
    try {
      const savedSession = await saveCurrentSession(sessionTitle);
      if (audioBlobRef.current || mediaRecorderRef.current) {
        await audioStopPromiseRef.current;
        if (audioBlobRef.current?.size > 0) {
          const audioBase64 = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onloadend = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(audioBlobRef.current);
          });
          const audioResponse = await fetch(`${API_BASE_URL}/api/sessions/${encodeURIComponent(savedSession.session_id)}/audio`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ audio_base64: audioBase64, user_email: user.email || '' }),
          });
          const audioResult = await audioResponse.json();
          if (!audioResponse.ok || !audioResult.success) throw new Error(audioResult.error || 'Không thể lưu audio.');
        }
      }
      setViewingSavedSessionId(savedSession.session_id);
      setActiveSessionTitle(savedSession.title);
      setSessionAudioUrl(`${API_BASE_URL}/api/sessions/${encodeURIComponent(savedSession.session_id)}/audio`);
      setShowSaveDialog(false);
      setStreamStatus('idle');
      setAppNotice({ type: 'success', message: 'Đã lưu buổi học, transcript, ghi chú và audio.' });
    } catch (error) {
      setSaveError(error.message || 'Không thể lưu buổi học. Vui lòng thử lại.');
      setAppNotice({ type: 'error', message: error.message || 'Không thể lưu buổi học.' });
    } finally {
      setIsSavingSession(false);
    }
  };

  const handleDiscardSession = () => {
    setShowSaveDialog(false);
    setStreamStatus('idle');
    setTranscripts([]);
    setAgentNotes([]);
  };

  const loadSession = (session) => {
    const loadedTranscripts = Array.isArray(session.transcripts) ? session.transcripts : [];
    const loadedNotes = Array.isArray(session.notes) ? session.notes : [];
    setTranscripts(loadedTranscripts);
    setAgentNotes(loadedNotes.map((note, index) => ({
      ...note,
      id: note.id || `${session.session_id}-${index}`,
      reviewStatus: note.reviewStatus || 'approved',
    })));
    transcriptsRef.current = loadedTranscripts;
    agentNotesRef.current = loadedNotes;
    currentSessionIdRef.current = session.session_id;
    setCurrentSessionId(session.session_id);
    setViewingSavedSessionId(session.session_id);
    setActiveSessionTitle(session.title || 'Buổi học đã lưu');
    setSessionAudioUrl(session.audio_url ? `${API_BASE_URL}${session.audio_url}` : '');
    if (session.transcript_file) setSelectedFile(session.transcript_file);
    setStreamStatus('complete');
    setActiveTab('live');
    const email = user.email || 'guest';
    fetch(`${API_BASE_URL}/api/chat/history?user_email=${encodeURIComponent(email)}&session_id=${encodeURIComponent(session.session_id)}`)
      .then((response) => response.ok ? response.json() : Promise.reject(new Error(`HTTP ${response.status}`)))
      .then((data) => {
        const messages = Array.isArray(data.messages) ? data.messages : [];
        setChatMessages(messages.map(({ role, content }) => ({ role, content })));
        setQaHistoryCount(messages.filter((message) => message.role === 'user').length);
      })
      .catch((error) => console.warn('Không thể tải chat của session:', error));
  };

  const handleToggleConnect = () => (isConnected ? disconnect() : connect());

  const persistSessionNotes = async (nextNotes) => {
    const sessionId = viewingSavedSessionId;
    if (!sessionId) return;
    setNoteSyncStatus('saving');
    try {
      const response = await fetch(`${API_BASE_URL}/api/sessions/${encodeURIComponent(sessionId)}/notes`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes: nextNotes, user_email: user.email || '' }),
      });
      const result = await response.json();
      if (!response.ok || !result.success) throw new Error(result.error || `HTTP ${response.status}`);
      setSessions((currentSessions) => currentSessions.map((session) => (
        session.session_id === sessionId
          ? {
              ...session,
              notes: nextNotes,
              total_notes: nextNotes.length,
              approved_notes: nextNotes.filter((note) => note.reviewStatus === 'approved').length,
              pending_notes: nextNotes.filter((note) => note.reviewStatus === 'pending').length,
            }
          : session
      )));
      const analyticsResponse = await fetch(`${API_BASE_URL}/api/analytics/daily?user_email=${encodeURIComponent(user.email || '')}`);
      if (analyticsResponse.ok) {
        const analyticsData = await analyticsResponse.json();
        setDailyStats(Array.isArray(analyticsData.days) ? analyticsData.days : []);
      }
      setNoteSyncStatus('saved');
      setAppNotice({ type: 'success', message: 'Ghi chú đã được đồng bộ.' });
    } catch (error) {
      console.error('Không thể đồng bộ ghi chú:', error);
      setNoteSyncStatus('error');
      setAppNotice({ type: 'error', message: 'Không thể đồng bộ thay đổi ghi chú.' });
    }
  };

  const handleRenameSession = async (session) => {
    const title = window.prompt('Tên mới của buổi học:', session.title || 'Buổi học');
    if (!title?.trim() || title.trim() === session.title) return;
    try {
      const response = await fetch(`${API_BASE_URL}/api/sessions/${encodeURIComponent(session.session_id)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title.trim(), user_email: user.email || '' }),
      });
      const result = await response.json();
      if (!response.ok || !result.success) throw new Error(result.error || `HTTP ${response.status}`);
      setSessions((items) => items.map((item) => item.session_id === session.session_id ? { ...item, title: title.trim() } : item));
      if (viewingSavedSessionId === session.session_id) setActiveSessionTitle(title.trim());
      setAppNotice({ type: 'success', message: 'Đã đổi tên buổi học.' });
    } catch (error) {
      setAppNotice({ type: 'error', message: error.message || 'Không thể đổi tên buổi học.' });
    }
  };

  const handleDeleteSession = async (session) => {
    if (!window.confirm(`Xóa buổi học “${session.title || 'Buổi học'}” và toàn bộ dữ liệu liên quan?`)) return;
    try {
      const response = await fetch(`${API_BASE_URL}/api/sessions/${encodeURIComponent(session.session_id)}?user_email=${encodeURIComponent(user.email || '')}`, { method: 'DELETE' });
      const result = await response.json();
      if (!response.ok || !result.success) throw new Error(result.error || `HTTP ${response.status}`);
      setSessions((items) => items.filter((item) => item.session_id !== session.session_id));
      if (viewingSavedSessionId === session.session_id) {
        setViewingSavedSessionId(null);
        setSessionAudioUrl('');
        setTranscripts([]);
        setAgentNotes([]);
        setActiveSessionTitle('Chưa có buổi học đang mở');
      }
      setAppNotice({ type: 'success', message: 'Đã xóa buổi học.' });
    } catch (error) {
      setAppNotice({ type: 'error', message: error.message || 'Không thể xóa buổi học.' });
    }
  };

  const updateNotes = (updater) => {
    const nextNotes = updater(agentNotesRef.current);
    agentNotesRef.current = nextNotes;
    setAgentNotes(nextNotes);
    void persistSessionNotes(nextNotes);
  };

  const handleDeleteNote = (id) => updateNotes((notes) => notes.filter((note) => note.id !== id));

  const handleConfirmNote = (id) => {
    updateNotes((prev) => prev.map((note) => (
      note.id === id ? { ...note, reviewStatus: 'approved' } : note
    )));
  };

  const handleStartEdit = (note) => {
    setEditingNoteId(note.id);
    setEditContent(note.content);
  };

  const handleSaveEdit = (id) => {
    updateNotes((prev) => prev.map((n) => (
      n.id === id ? { ...n, content: editContent, reviewStatus: 'approved' } : n
    )));
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
    approvedNotes: agentNotes.filter((n) => n.reviewStatus === 'approved').length,
    pendingNotes: agentNotes.filter((n) => n.reviewStatus === 'pending').length,
    definitions: agentNotes.filter((n) => n.type === 'definition').length,
    examples: agentNotes.filter((n) => n.type === 'example').length,
    warnings: agentNotes.filter((n) => n.type === 'exam_warning').length,
  };

  const fmtTime = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

  const selectedTranscript = transcriptFiles.find((file) => file.filename === selectedFile);

  const noteCategoryData = [
    { label: 'Định nghĩa', value: stats.definitions, color: '#2563EB' },
    { label: 'Ví dụ', value: stats.examples, color: '#10B981' },
    { label: 'Lưu ý', value: stats.warnings, color: '#F59E0B' },
    { label: 'Ý chính', value: agentNotes.filter((note) => ['key_point', 'insight'].includes(note.type)).length, color: '#7C3AED' },
    { label: 'Việc cần làm', value: agentNotes.filter((note) => note.type === 'action_item').length, color: '#DC2626' },
  ];
  const noteCategoryMax = Math.max(...noteCategoryData.map((item) => item.value), 1);
  const reviewTotal = Math.max(stats.notes, 1);
  const approvedPercent = Math.round((stats.approvedNotes / reviewTotal) * 100);
  const pendingPercent = Math.round((stats.pendingNotes / reviewTotal) * 100);
  const unreviewedPercent = Math.max(0, 100 - approvedPercent - pendingPercent);
  const donutStyle = {
    background: stats.notes === 0
      ? 'conic-gradient(#E2E8F0 0deg 360deg)'
      : `conic-gradient(#10B981 0deg ${approvedPercent * 3.6}deg, #F59E0B ${approvedPercent * 3.6}deg ${(approvedPercent + pendingPercent) * 3.6}deg, #CBD5E1 ${(approvedPercent + pendingPercent) * 3.6}deg 360deg)`,
  };
  const activitySeries = transcripts.map((segment, index) => ({
    words: String(segment.text || '').trim().split(/\s+/).filter(Boolean).length,
    timestamp: Number.isFinite(segment.timestamp_s) ? segment.timestamp_s : index * 2,
  }));
  const maxWordsPerSegment = Math.max(...activitySeries.map((point) => point.words), 1);
  const linePointCoords = activitySeries.length > 0
    ? activitySeries.map((point, index) => {
        const x = activitySeries.length === 1 ? 260 : 16 + (index / (activitySeries.length - 1)) * 488;
        const y = 164 - (point.words / maxWordsPerSegment) * 138;
        return { x, y, label: fmtTime(point.timestamp), value: point.words };
      })
    : [];
  const linePoints = linePointCoords.map((point) => `${point.x},${point.y}`).join(' ');

  // ═══════════════════════════════════════════════════════════
  // LOGIN SCREEN (If not logged in)
  // ═══════════════════════════════════════════════════════════
  if (!user) {
    return (
      <div className={`login-page-container ${theme === 'dark' ? 'dark-theme' : 'light-theme'}`}>
        {/* Theme Toggle - góc trên phải */}
        <button
          className="theme-toggle-floating"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          title={theme === 'dark' ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối'}
        >
          <UiIcon icon={theme === 'dark' ? Sun : Moon} />
        </button>

        <div className="login-card">
          <div className="login-header">
            <VinUniLogo size={64} />
            <h1 className="login-title">VinUniversity Portal</h1>
            <p className="login-subtitle">Hệ thống Trợ lý Học tập AI Realtime — VLearnNote</p>
          </div>

          <form onSubmit={handleLogin} className="login-form">
            {loginError && <div className="login-error-alert"><UiIcon icon={AlertTriangle} /> {loginError}</div>}

            <div className="form-group">
              <label htmlFor="login-email"><UiIcon icon={Mail} /> Email Sinh viên VinUni</label>
              <input
                id="login-email"
                type="email"
                className="form-input"
                placeholder="Nhập email sinh viên (ví dụ: student@vinuni.edu.vn)"
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="login-pass"><UiIcon icon={KeyRound} /> Mã học viên VinUni</label>
              <input
                id="login-pass"
                type="password"
                className="form-input"
                placeholder="Nhập mã học viên (ví dụ: VIN2026888)"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="btn-login">
              <UiIcon icon={LockKeyhole} /> Đăng nhập VinUni Account
            </button>
          </form>

          <div className="login-footer">
            <a href="#" className="forgot-password-link">
              <UiIcon icon={RefreshCw} /> Quên mật khẩu? Liên hệ IT VinUni
            </a>
            <p className="login-hint">Hỗ trợ sinh viên & Giảng viên VinUniversity • Hackathon 2026</p>
          </div>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════
  // MAIN DASHBOARD UI (Exact Match to VLearn Screenshot)
  // ═══════════════════════════════════════════════════════════
  return (
    <div className={`app-container ${theme === 'dark' ? 'dark-theme' : 'light-theme'}`}>
      {/* ── Top Navigation Header ── */}
      <header className="app-header">
        <div className="header-left">
          <div className="app-logo">
            <VinUniLogo size={38} />
            <span className="logo-title">
              <span className="vlearn-v">V</span><span className="vlearn-text">LearnNote</span>
            </span>
          </div>

          <nav className="tab-nav" role="tablist">
            <button
              role="tab"
              className={`tab-btn ${activeTab === 'live' ? 'active' : ''}`}
              onClick={() => setActiveTab('live')}
            >
              <UiIcon icon={Mic} size={17} /> Live Bài Giảng
            </button>
            <button
              role="tab"
              className={`tab-btn ${activeTab === 'notes' ? 'active' : ''}`}
              onClick={() => setActiveTab('notes')}
            >
              <UiIcon icon={StickyNote} size={17} /> Ghi chú
            </button>
            <button
              role="tab"
              className={`tab-btn ${activeTab === 'analytics' ? 'active' : ''}`}
              onClick={() => setActiveTab('analytics')}
            >
              <UiIcon icon={BarChart3} size={17} /> Thống kê
            </button>
          </nav>
        </div>

        <div className="header-right">
          {/* Codelabs button matching Image 1 */}
          <button
            className="btn-codelabs"
            onClick={() => {
              const codelabsUrl = new URL('https://codelabs.vlearn.dev/tips');
              codelabsUrl.searchParams.set('student_name', user.name || '');
              codelabsUrl.searchParams.set('student_email', user.email || '');
              codelabsUrl.searchParams.set('student_id', user.studentId || '');
              window.open(codelabsUrl.toString(), '_blank', 'noopener,noreferrer');
            }}
          >
            <UiIcon icon={ExternalLink} size={15} /> Mở Codelabs
          </button>

          {/* Language selector button */}
          <button className="btn-lang">VI</button>

          {/* Record Button */}
          <button
            className={`btn-record ${isConnected ? 'recording' : ''}`}
            onClick={handleToggleConnect}
          >
            <span className="rec-dot" />
            {isConnected ? 'Dừng ghi âm' : 'Bắt đầu ghi âm'}
          </button>

          {/* Theme Toggle Button */}
          <button
            className="btn-theme"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            title="Đổi Giao diện Sáng/Tối"
          >
            <UiIcon icon={theme === 'dark' ? Sun : Moon} />
          </button>

          {/* User Profile Pill matching Image 1 */}
          <div className="user-profile-pill">
            <span className="user-badge">2</span>
            <span className="user-email-text">{user.email || '26ai.phuongdlq@vinuni.edu.vn'}</span>
            <button className="btn-logout" onClick={handleLogout} title="Đăng xuất">
              <UiIcon icon={LogOut} size={16} />
            </button>
          </div>
        </div>
      </header>

      {/* ── Main Content Area ── */}
      <main className="app-main">
        {/* ── Live Tab (Matching VLearn Screenshot UI) ── */}
        {activeTab === 'live' && (
          <div className="tab-content live-tab">
            {/* Hero Banner (Blue gradient with red diagonal cut) */}
            <div className="hero-banner">
              <div className="hero-content">
                <div className="hero-eyebrow">VLEARN · VINUNI AI THỰC CHIẾN</div>
                <h1 className="hero-title">Chào mừng bạn đến với VLearnNote!</h1>
                <p className="hero-subtitle">
                  Bấm "Bắt đầu ghi âm" để kết nối và nhận transcript realtime, ghi chú tự động từ AI.
                </p>
              </div>
            </div>

            <div className="session-select-card">
              <label className="card-title" htmlFor="session-select">
                <UiIcon icon={FolderOpen} size={17} /> Chọn buổi học
              </label>
              <select
                id="session-select"
                className="session-select-input"
                value={selectedFile}
                onChange={(event) => {
                  const nextFile = event.target.value;
                  setSelectedFile(nextFile);
                  setViewingSavedSessionId(null);
                  const file = transcriptFiles.find((item) => item.filename === nextFile);
                  setActiveSessionTitle(nextFile ? (file?.title || file?.display_name || 'Bài học có sẵn') : 'Buổi học mới chưa lưu');
                }}
                disabled={isConnected}
              >
                <option value="">Ghi buổi học mới bằng microphone</option>
                {transcriptFiles.length === 0 && <option>Đang tải danh sách buổi học...</option>}
                {transcriptFiles.map((file) => (
                  <option key={file.filename} value={file.filename}>
                    {file.display_name}: {file.title === 'Unknown' ? 'Nội dung bài giảng' : file.title}
                  </option>
                ))}
              </select>
              <span className={`session-select-status ${isConnected ? 'is-live' : ''}`}>
                {isConnected ? 'Đang phát' : viewingSavedSessionId ? 'Đang xem lại' : 'Sẵn sàng'}
                {selectedTranscript ? ` · ${selectedTranscript.display_name}` : ' · Buổi học mới'}
              </span>
            </div>

            <div className="session-context-bar">
              <span>Đang xem</span>
              <strong>{activeSessionTitle}</strong>
              {viewingSavedSessionId && <span className="context-saved">ĐÃ LƯU</span>}
              {sessionAudioUrl && <audio className="session-audio-player" controls src={sessionAudioUrl} preload="metadata" />}
            </div>

            {/* Stats Row (3 Cards: GHI CHÚ, TRANSCRIPT, CÂU HỎI) */}
            <div className="stats-row">
              <div className="stat-card">
                <div className="stat-icon-box note-icon-box"><UiIcon icon={Pencil} size={22} /></div>
                <div className="stat-info">
                  <span className="stat-label">GHI CHÚ</span>
                  <span className="stat-value">{agentNotes.length}</span>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon-box mic-icon-box"><UiIcon icon={Mic} size={22} /></div>
                <div className="stat-info">
                  <span className="stat-label">TRANSCRIPT</span>
                  <span className="stat-value">{transcripts.length}</span>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon-box chat-icon-box"><UiIcon icon={MessageCircle} size={22} /></div>
                <div className="stat-info">
                  <span className="stat-label">CÂU HỎI</span>
                  <span className="stat-value">{qaHistoryCount}</span>
                </div>
              </div>
            </div>

            {/* Main 2-Column Panels */}
            <div className="live-grid">
              {/* Left Panel: Phiên âm trực tiếp */}
              <div className="live-panel transcript-panel">
                <div className="panel-header">
                  <h2>Phiên âm trực tiếp</h2>
                  <span className={`status-badge ${isConnected ? 'pulse' : ''}`}>
                    {isConnected ? 'LIVE STREAMING' : 'OFFLINE'}
                  </span>
                </div>
                <div className="panel-body transcript-body">
                  {transcripts.length === 0 ? (
                    <div className={`panel-empty-state ${streamStatus === 'error' ? 'has-error' : ''}`}>
                      <div className="empty-icon">
                        <UiIcon
                          icon={streamStatus === 'error' ? AlertTriangle : Mic}
                          size={34}
                        />
                      </div>
                      <p className="empty-text">
                        {streamStatus === 'connecting' && 'Đang kết nối với bài giảng...'}
                        {streamStatus === 'loading' && `Đang tải nội dung ${selectedFile.replace('transcript-', 'Buổi ').replace('-clean.md', '')}...`}
                        {streamStatus === 'error' && streamError}
                        {(streamStatus === 'idle' || streamStatus === 'complete') && 'Chưa có transcript'}
                      </p>
                      {streamStatus === 'error' && (
                        <button className="btn-retry" onClick={handleToggleConnect}>
                          <UiIcon icon={RefreshCw} size={16} /> Thử lại
                        </button>
                      )}
                    </div>
                  ) : (
                    <div className="transcript-list">
                      {transcripts.map((t, idx) => (
                        <div key={idx} className="transcript-item">
                          <span className="speaker-tag">{t.speaker || 'Giảng viên'}:</span>
                          <span className="transcript-text">{t.text}</span>
                        </div>
                      ))}
                      <div ref={transcriptEndRef} />
                    </div>
                  )}
                </div>
              </div>

              {/* Right Panel: Ghi chú tự động */}
              <div className="live-panel notes-panel">
                <div className="panel-header">
                  <h2>Ghi chú tự động</h2>
                  <button className="view-all-link" onClick={() => setActiveTab('notes')}>
                    Xem tất cả →
                  </button>
                </div>
                <div className="panel-body notes-body">
                  {agentNotes.length === 0 ? (
                    <div className="panel-empty-state">
                      <div className="empty-icon"><UiIcon icon={StickyNote} size={34} /></div>
                      <p className="empty-text">Chưa có ghi chú</p>
                    </div>
                  ) : (
                    <div className="notes-list">
                      {agentNotes.map((note) => (
                        <div key={note.id} className={`note-card note-${note.type}`}>
                          <div className="note-card-header">
                            <span className="note-type">
                              <NoteIcon type={note.type} /> {LABEL_TEXT[note.type] || note.type.toUpperCase()}
                            </span>
                            <div className="note-meta">
                              {note.reviewStatus === 'pending' && <span className="review-badge">CHỜ DUYỆT</span>}
                              {note.timestamp_s > 0 && <span className="note-time">{fmtTime(note.timestamp_s)}</span>}
                            </div>
                          </div>
                          <div className="note-card-body">
                            {editingNoteId === note.id ? (
                              <div className="edit-box">
                                <textarea
                                  className="edit-textarea"
                                  value={editContent}
                                  onChange={(e) => setEditContent(e.target.value)}
                                />
                                <div className="edit-actions">
                                  <button className="btn-sm btn-save" onClick={() => handleSaveEdit(note.id)}>
                                    Lưu
                                  </button>
                                  <button className="btn-sm btn-cancel" onClick={handleCancelEdit}>
                                    Hủy
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <p className="note-content">{note.content}</p>
                            )}
                            {note.source && <p className="note-source"><UiIcon icon={Pin} size={14} /> Nguồn: "{sourceExcerpt(note.source)}"</p>}
                          </div>
                          <div className="note-card-footer">
                            {note.reviewStatus === 'pending' && (
                              <button className="btn-icon btn-approve" onClick={() => handleConfirmNote(note.id)} title="Duyệt ghi chú">
                                <UiIcon icon={CheckCircle2} size={16} /> Duyệt
                              </button>
                            )}
                            <button className="btn-icon" onClick={() => handleStartEdit(note)} title="Chỉnh sửa">
                              <UiIcon icon={Pencil} size={16} />
                            </button>
                            <button className="btn-icon" onClick={() => handleDeleteNote(note.id)} title="Xóa">
                              <UiIcon icon={X} size={16} />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

          </div>
        )}

        {/* ── Notes Tab ── */}
        {activeTab === 'notes' && (
          <div className="tab-content notes-tab">
            <div className="session-context-bar">
              <span>Ghi chú của</span>
              <strong>{activeSessionTitle}</strong>
              <span className={`note-sync-status ${noteSyncStatus}`}>
                {noteSyncStatus === 'saving' && 'Đang đồng bộ...'}
                {noteSyncStatus === 'saved' && 'Đã đồng bộ'}
                {noteSyncStatus === 'error' && 'Lỗi đồng bộ'}
              </span>
            </div>
            <div className="notes-header">
              <div className="notes-header-copy">
                <h2>Ghi Chú Bài Học</h2>
                <p>{stats.approvedNotes} đã duyệt · {stats.pendingNotes} chờ duyệt · {stats.notes} tổng cộng</p>
              </div>
              <div className="note-filters">
                <button
                  className={`filter-btn ${activeNoteFilter === 'all' ? 'active' : ''}`}
                  onClick={() => setActiveNoteFilter('all')}
                >
                  Tất cả ({agentNotes.length})
                </button>
                <button
                  className={`filter-btn ${activeNoteFilter === 'definition' ? 'active' : ''}`}
                  onClick={() => setActiveNoteFilter('definition')}
                >
                  <UiIcon icon={BookOpen} size={16} /> Định nghĩa ({stats.definitions})
                </button>
                <button
                  className={`filter-btn ${activeNoteFilter === 'example' ? 'active' : ''}`}
                  onClick={() => setActiveNoteFilter('example')}
                >
                  <UiIcon icon={Lightbulb} size={16} /> Ví dụ ({stats.examples})
                </button>
                <button
                  className={`filter-btn ${activeNoteFilter === 'exam_warning' ? 'active' : ''}`}
                  onClick={() => setActiveNoteFilter('exam_warning')}
                >
                  <UiIcon icon={AlertTriangle} size={16} /> Lưu ý thi ({stats.warnings})
                </button>
              </div>
            </div>

            <div className="notes-grid-full">
              {filteredNotes.length === 0 ? (
                <div className="empty-state">
                  <p>Chưa có ghi chú nào cho bộ lọc này.</p>
                </div>
              ) : (
                filteredNotes.map((note) => (
                  <div key={note.id} className={`note-card note-${note.type}`}>
                    <div className="note-card-header">
                      <span className="note-type">
                        <NoteIcon type={note.type} /> {LABEL_TEXT[note.type] || note.type.toUpperCase()}
                      </span>
                      <div className="note-meta">
                        {note.reviewStatus === 'pending' && <span className="review-badge">CHỜ DUYỆT</span>}
                        {note.timestamp_s > 0 && <span className="note-time">{fmtTime(note.timestamp_s)}</span>}
                      </div>
                    </div>
                    <div className="note-card-body">
                      {editingNoteId === note.id ? (
                        <div className="edit-box">
                          <textarea className="edit-textarea" value={editContent} onChange={(event) => setEditContent(event.target.value)} />
                          <div className="edit-actions">
                            <button className="btn-sm btn-save" onClick={() => handleSaveEdit(note.id)}>Lưu</button>
                            <button className="btn-sm btn-cancel" onClick={handleCancelEdit}>Hủy</button>
                          </div>
                        </div>
                      ) : (
                        <p className="note-content">{note.content}</p>
                      )}
                      {note.source && <p className="note-source"><UiIcon icon={Pin} size={14} /> Nguồn: "{sourceExcerpt(note.source)}"</p>}
                    </div>
                    <div className="note-card-footer">
                      {note.reviewStatus === 'pending' && (
                        <button className="btn-icon btn-approve" onClick={() => handleConfirmNote(note.id)}>
                          <UiIcon icon={CheckCircle2} size={16} /> Duyệt
                        </button>
                      )}
                      <button className="btn-icon" onClick={() => handleStartEdit(note)} title="Chỉnh sửa">
                        <UiIcon icon={Pencil} size={16} /> Sửa
                      </button>
                      <button className="btn-icon btn-delete" onClick={() => handleDeleteNote(note.id)} title="Xóa">
                        <UiIcon icon={X} size={16} /> Xóa
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* ── Analytics Tab ── */}
        {activeTab === 'analytics' && (
          <div className="tab-content analytics-tab">
            <h2>Thống Kê & Lịch Sử Bài Học</h2>
            <div className="session-context-bar">
              <span>Thống kê của</span>
              <strong>{activeSessionTitle}</strong>
            </div>

            <div className="stats-cards-grid">
              <div className="stat-card">
                <div className="stat-icon-box"><UiIcon icon={Mic} size={22} /></div>
                <div className="stat-info">
                  <span className="stat-label">Tổng Phụ Đề</span>
                  <span className="stat-value">{stats.transcripts}</span>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon-box"><UiIcon icon={StickyNote} size={22} /></div>
                <div className="stat-info">
                  <span className="stat-label">Đã Duyệt</span>
                  <span className="stat-value">{stats.approvedNotes}</span>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon-box"><UiIcon icon={Clock3} size={22} /></div>
                <div className="stat-info">
                  <span className="stat-label">Chờ Duyệt</span>
                  <span className="stat-value">{stats.pendingNotes}</span>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon-box"><UiIcon icon={BookOpen} size={22} /></div>
                <div className="stat-info">
                  <span className="stat-label">Định Nghĩa</span>
                  <span className="stat-value">{stats.definitions}</span>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon-box"><UiIcon icon={AlertTriangle} size={22} /></div>
                <div className="stat-info">
                  <span className="stat-label">Cảnh Báo Thi</span>
                  <span className="stat-value">{stats.warnings}</span>
                </div>
              </div>
            </div>

            <div className="daily-dashboard">
              <div className="daily-dashboard-header">
                <h3><UiIcon icon={BarChart3} /> Hoạt Động Theo Ngày</h3>
                <span>Tự động cập nhật từ database</span>
              </div>
              {dailyStats.length > 0 ? (
                <div className="daily-stats-list">
                  {[...dailyStats].reverse().slice(0, 7).map((day) => (
                    <div className="daily-stat-row" key={day.date}>
                      <strong>{new Date(`${day.date}T00:00:00`).toLocaleDateString('vi-VN')}</strong>
                      <span>{day.sessions} buổi học</span>
                      <span>{day.transcripts} transcript</span>
                      <span>{day.approved_notes || 0} duyệt · {day.pending_notes || 0} chờ</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state compact"><p>Chưa có dữ liệu theo ngày.</p></div>
              )}
            </div>

            <div className="analytics-charts-grid">
              <section className="chart-card">
                <div className="chart-card-header">
                  <div>
                    <h3><UiIcon icon={BarChart3} size={17} /> Phân bố ghi chú</h3>
                    <p>Những dạng kiến thức AI được phát hiện trong buổi này</p>
                  </div>
                </div>
                <div className="bar-chart-area">
                  {noteCategoryData.map((item) => (
                    <div className="bar-chart-row" key={item.label}>
                      <span>{item.label}</span>
                      <div className="bar-track"><div className="bar-fill" style={{ width: `${(item.value / noteCategoryMax) * 100}%`, background: item.color }} /></div>
                      <strong>{item.value}</strong>
                    </div>
                  ))}
                </div>
              </section>

              <section className="chart-card review-chart-card">
                <div className="chart-card-header">
                  <div>
                    <h3><UiIcon icon={PieChart} size={17} /> Trạng thái ghi chú</h3>
                    <p>Mức độ hoàn tất quy trình HITL</p>
                  </div>
                </div>
                <div className="donut-layout">
                  <div className="donut-chart" style={donutStyle}><div className="donut-hole"><strong>{stats.notes}</strong><span>tổng note</span></div></div>
                  <div className="chart-legend">
                    <span><i className="legend-dot approved" /> Đã duyệt <strong>{stats.approvedNotes}</strong></span>
                    <span><i className="legend-dot pending" /> Chờ duyệt <strong>{stats.pendingNotes}</strong></span>
                    <span><i className="legend-dot unreviewed" /> Chưa phân loại <strong>{unreviewedPercent > 0 ? Math.round((unreviewedPercent / 100) * stats.notes) : 0}</strong></span>
                  </div>
                </div>
              </section>

              <section className="chart-card line-chart-card">
                  <div className="chart-card-header">
                  <div>
                    <h3><UiIcon icon={LineChart} size={17} /> Hoạt động phiên âm {isConnected && <span className="live-chart-badge">LIVE</span>}</h3>
                    <p>Mật độ nội dung theo thời gian (số từ mỗi đoạn)</p>
                  </div>
                  <strong className="chart-total">{stats.transcripts} đoạn</strong>
                </div>
                <div className="line-chart-wrap">
                  <svg viewBox="0 0 520 180" role="img" aria-label="Biểu đồ tiến độ phiên âm">
                    <line x1="16" y1="164" x2="504" y2="164" className="chart-axis" />
                    <line x1="16" y1="26" x2="16" y2="164" className="chart-axis" />
                    <line x1="16" y1="95" x2="504" y2="95" className="chart-grid-line" />
                    <polyline key={transcripts.length} points={linePoints} className={`line-chart-line ${isConnected ? 'is-live' : ''}`} />
                    {transcripts.length > 0 && linePointCoords.map((point, index) => (
                      <circle key={`${transcripts.length}-${index}`} cx={point.x} cy={point.y} r={index === linePointCoords.length - 1 ? 5 : 2.5} className={`line-chart-point ${index === linePointCoords.length - 1 && isConnected ? 'current' : ''}`}>
                        <title>{point.label} · {point.value} từ</title>
                      </circle>
                    ))}
                  </svg>
                  {stats.transcripts === 0 && <span className="chart-empty-label">Bắt đầu buổi học để xem tiến độ</span>}
                </div>
              </section>
            </div>

            {/* Sessions History */}
            <div className="sessions-section">
              <h3><UiIcon icon={Clock3} /> Lịch Sử Các Buổi Học</h3>
              {sessions.length > 0 ? (
                <div className="sessions-list">
                  {[...sessions].sort((a, b) => b.start_time - a.start_time).map((session) => (
                    <div
                      key={session.session_id}
                      className="session-card"
                      role="button"
                      tabIndex={0}
                      onClick={() => loadSession(session)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') loadSession(session);
                      }}
                    >
                      <div className="session-header">
                        <h4><UiIcon icon={FolderOpen} size={16} /> {session.title || (session.transcript_file ? session.transcript_file.replace('.md', '').replace('transcript-', 'Buổi ') : 'Buổi Học')}</h4>
                        <span className="session-time">
                          {new Date(session.start_time).toLocaleString('vi-VN')}
                        </span>
                        <div className="session-card-actions">
                          <button className="session-action-button" title="Đổi tên buổi học" aria-label="Đổi tên buổi học" onClick={(event) => { event.stopPropagation(); handleRenameSession(session); }}>
                            <UiIcon icon={Pencil} size={15} />
                          </button>
                          <button className="session-action-button danger" title="Xóa buổi học" aria-label="Xóa buổi học" onClick={(event) => { event.stopPropagation(); handleDeleteSession(session); }}>
                            <UiIcon icon={Trash2} size={15} />
                          </button>
                        </div>
                      </div>
                      <div className="session-stats">
                        <span><UiIcon icon={Clock3} size={15} /> {Math.floor((session.duration_seconds || 0) / 60)} phút</span>
                        <span><UiIcon icon={StickyNote} size={15} /> {session.approved_notes || 0} duyệt · {session.pending_notes || 0} chờ</span>
                        <span><UiIcon icon={Mic} size={15} /> {session.total_segments || 0} segments</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  <p>Chưa có lịch sử buổi học được lưu.</p>
                </div>
              )}
            </div>

            {/* Export Section */}
            <div className="export-section">
              <h3><UiIcon icon={Download} /> Xuất Dữ Liệu Bài Học</h3>
              <div className="export-buttons">
                <button
                  className="btn-export"
                  onClick={() => {
                    const markdown = `# VLearnNote - Ghi Chú Bài Học VinUni\n\n` +
                      `## Thống Kê Buổi Học\n` +
                      `- Phụ đề: ${stats.transcripts} segments\n` +
                      `- Ghi chú AI: ${stats.notes} notes\n\n` +
                      `## Danh Sách Ghi Chú\n\n` +
                      agentNotes.map(note =>
                        `### ${(LABEL_TEXT[note.type] || note.type).toUpperCase()}\n${note.content}\n${note.source ? `> Trích nguồn: "${note.source}"` : ''}\n`
                      ).join('\n');

                    const blob = new Blob([markdown], { type: 'text/markdown' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `VLearnNote_VinUni_${Date.now()}.md`;
                    a.click();
                  }}
                >
                  <UiIcon icon={FileCode2} size={17} /> Xuất Markdown (.md)
                </button>
                <button
                  className="btn-export"
                  onClick={() => {
                    const json = JSON.stringify({
                      user: user,
                      session: {
                        transcript_file: selectedFile,
                        timestamp: Date.now(),
                        stats: stats,
                      },
                      transcripts: transcripts,
                      notes: agentNotes,
                    }, null, 2);

                    const blob = new Blob([json], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `VLearnNote_VinUni_${Date.now()}.json`;
                    a.click();
                  }}
                >
                  <UiIcon icon={FileJson2} size={17} /> Xuất JSON (.json)
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {showSaveDialog && (
        <div className="save-session-overlay" role="dialog" aria-modal="true" aria-labelledby="save-session-title">
          <div className="save-session-dialog">
            <div className="save-session-dialog-header">
              <div>
                <span className="dialog-eyebrow">BUỔI HỌC ĐÃ KẾT THÚC</span>
                <h2 id="save-session-title">Lưu buổi học</h2>
              </div>
              <button className="dialog-close" onClick={handleDiscardSession} title="Đóng"><UiIcon icon={X} /></button>
            </div>
            <p>Đặt tên để lần sau mở lại đúng transcript, ghi chú và thống kê của buổi này.</p>
            <label htmlFor="session-title-input">Tên buổi học</label>
            <input
              id="session-title-input"
              className="session-title-input"
              value={sessionTitle}
              onChange={(event) => setSessionTitle(event.target.value)}
              placeholder="Ví dụ: Agent và cách xác định bài toán"
              autoFocus
              onKeyDown={(event) => event.key === 'Enter' && handleSaveSession()}
            />
            {saveError && <div className="save-session-error"><UiIcon icon={AlertTriangle} size={16} /> {saveError}</div>}
            <div className="save-session-actions">
              <button className="btn-dialog-secondary" onClick={handleDiscardSession}>Bỏ qua</button>
              <button className="btn-dialog-primary" onClick={handleSaveSession} disabled={isSavingSession || transcripts.length === 0}>
                <UiIcon icon={CheckCircle2} size={17} /> {isSavingSession ? 'Đang lưu...' : 'Lưu buổi học'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════
          AI CHAT FLOATING WIDGET (Facebook Messenger style)
      ═══════════════════════════════════════════════════════════ */}
      {user && (
        <>
          {appNotice && (
            <div className={`app-notice ${appNotice.type || 'info'}`} role="status">
              <UiIcon icon={appNotice.type === 'error' ? AlertTriangle : CheckCircle2} size={16} />
              <span>{appNotice.message}</span>
            </div>
          )}
          {/* Floating chat button */}
          <button
            className={`ai-chat-fab ${isChatOpen ? 'open' : ''}`}
            onClick={() => setIsChatOpen(!isChatOpen)}
            title="AI Trợ lý VLearn"
          >
            <UiIcon icon={isChatOpen ? X : MessageCircle} size={22} />
          </button>

          {/* Chat popup window */}
          {isChatOpen && (
            <div className="ai-chat-popup">
              <div className="chat-header">
                <div className="chat-header-info">
                  <div className="chat-avatar"><UiIcon icon={Bot} size={22} /></div>
                  <div>
                    <h4>AI Trợ lý VLearn</h4>
                    <span className="chat-status"><span className="chat-status-dot" /> Sẵn sàng hỗ trợ</span>
                  </div>
                </div>
                <button className="chat-close" onClick={() => setIsChatOpen(false)} title="Đóng"><UiIcon icon={X} /></button>
              </div>

              <div className="chat-messages">
                {chatMessages.length === 0 && (
                  <div className="chat-welcome">
                    <p>Xin chào! Tôi là AI trợ lý của VLearnNote.</p>
                    <p>Hãy hỏi tôi bất cứ điều gì về bài giảng nhé!</p>
                  </div>
                )}
                {chatMessages.map((msg, idx) => (
                  <div key={idx} className={`chat-message ${msg.role}`}>
                    <div className="chat-bubble">{msg.content}</div>
                  </div>
                ))}
                {isChatLoading && (
                  <div className="chat-message assistant">
                    <div className="chat-bubble typing">
                      <span></span><span></span><span></span>
                    </div>
                  </div>
                )}
              </div>

              <div className="chat-input-box">
                <input
                  type="text"
                  className="chat-input"
                  placeholder="Nhập câu hỏi của bạn..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleChatSend()}
                />
                <button
                  className="chat-send-btn"
                  onClick={handleChatSend}
                  disabled={!chatInput.trim() || isChatLoading}
                >
                  <UiIcon icon={Send} size={18} />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default App;
