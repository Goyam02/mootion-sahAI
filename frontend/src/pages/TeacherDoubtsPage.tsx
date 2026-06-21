import React, { useState, useEffect, useRef, useCallback } from 'react';
import { LogoutModal } from '../components/LogoutModal';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { motion, AnimatePresence } from 'motion/react';
import { 
  ArrowLeft, 
  MessageSquare, 
  Check, 
  Mic, 
  Send, 
  Sparkles, 
  User, 
  Volume2, 
  X,
  LayoutDashboard,
  BookOpen,
  BarChart2,
  HelpCircle,
  Clock,
  Play,
  Square,
  Sparkle,
  Menu
} from 'lucide-react';
import { NavItem } from '../components/NavItem';

const blobToBase64 = (blob: Blob): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64data = reader.result as string;
      const base64 = base64data.split(',')[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
};

const getGeminiApiKey = (): string => {
  const envKey = (import.meta as any).env.GEMINI_API_KEY;
  if (envKey && envKey !== 'MY_GEMINI_API_KEY' && envKey.trim() !== '') {
    return envKey;
  }
  return "";
};

const transcribeAudioWithGemini = async (blob: Blob): Promise<string> => {
  const base64 = await blobToBase64(blob);
  const apiKey = getGeminiApiKey();
  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`;
  
  const cleanMimeType = (blob.type || 'audio/webm').split(';')[0];
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      contents: [{
        parts: [
          {
            inlineData: {
              mimeType: cleanMimeType,
              data: base64
            }
          },
          {
            text: "Transcribe the spoken audio exactly. Do not add any extra commentary or conversational filler. Output only the transcribed text."
          }
        ]
      }]
    })
  });
  
  if (!response.ok) {
    throw new Error(`Gemini transcription error: ${response.statusText}`);
  }
  
  const data = await response.json();
  const text = data.candidates?.[0]?.content?.parts?.[0]?.text || '';
  return text.trim();
};

export function TeacherDoubtsPage() {
  const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);
  const navigate = useNavigate();
  
  // Real API doubt and class states
  const [classes, setClasses] = useState<any[]>([]);
  const [doubts, setDoubts] = useState<any[]>([]);
  const [selectedFilter, setSelectedFilter] = useState<string>('all'); // 'all' or class_id
  const [selectedDoubtId, setSelectedDoubtId] = useState<string | null>(null);
  const [responseInputs, setResponseInputs] = useState<Record<string, string>>({});
  const [submittingIds, setSubmittingIds] = useState<Record<string, boolean>>({});
  const [teacherName, setTeacherName] = useState<string>('Teacher');

  const handleClassroomNav = () => {
    const lastClassId = localStorage.getItem('mootion_last_class_id');
    if (lastClassId) {
      navigate(`/teacher/class/${lastClassId}`);
    } else if (classes && classes.length > 0) {
      const firstClass = classes[0];
      const g = firstClass.grade.toLowerCase().replace(/\s+/g, '-');
      const s = firstClass.subject.toLowerCase().replace(/\s+/g, '-');
      navigate(`/teacher/class/${g}-${s}`);
    } else {
      navigate('/teacher/class/class-8-science');
    }
  };
  
  // AI Suggestions & Speech-to-Text States
  const [aiSuggestions, setAiSuggestions] = useState<Record<string, string>>({});
  const [isGeneratingSuggestions, setIsGeneratingSuggestions] = useState<boolean>(false);
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isTranscribing, setIsTranscribing] = useState<boolean>(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recognitionRef = useRef<any>(null);
  const voiceStartTextRef = useRef<string>('');
  const chatInputRef = useRef<HTMLInputElement | null>(null);

  const focusAndMoveCursorToEnd = useCallback((newVal: string) => {
    setTimeout(() => {
      if (chatInputRef.current) {
        chatInputRef.current.focus();
        const len = newVal.length;
        chatInputRef.current.setSelectionRange(len, len);
        chatInputRef.current.scrollLeft = chatInputRef.current.scrollWidth;
      }
    }, 50);
  }, []);

  // Mobile filter list toggle
  const [isMobileListOpen, setIsMobileListOpen] = useState<boolean>(false);

  // New doubt ids for pulse animation highlight
  const [newDoubtIds, setNewDoubtIds] = useState<Set<string>>(new Set());

  // Audio Playback States
  const [playingAudioUrl, setPlayingAudioUrl] = useState<string | null>(null);
  const [currentAudio, setCurrentAudio] = useState<HTMLAudioElement | null>(null);

  const fetchAllDoubts = async (classList: any[]) => {
    try {
      const allFetchedDoubts: any[] = [];
      for (const cls of classList) {
        try {
          const classDoubts = await api.get(`/teachers/classes/${cls.class_id}/doubts`);
          classDoubts.forEach((d: any) => {
            d.subjectLabel = `${cls.grade} - ${cls.subject}`;
          });
          allFetchedDoubts.push(...classDoubts);
        } catch (err) {
          console.error(`Failed to fetch doubts for class ${cls.class_id}:`, err);
        }
      }
      
      allFetchedDoubts.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      
      setDoubts(prevDoubts => {
        if (prevDoubts.length > 0) {
          const prevIds = new Set(prevDoubts.map(d => d.doubt_id));
          const currentIds = allFetchedDoubts.map(d => d.doubt_id);
          const newlyArrived = currentIds.filter(id => !prevIds.has(id));
          
          if (newlyArrived.length > 0) {
            setNewDoubtIds(new Set(newlyArrived));
            setTimeout(() => {
              setNewDoubtIds(new Set());
            }, 5000);
          }
        }
        return allFetchedDoubts;
      });
    } catch (err) {
      console.error("Failed to fetch doubts for classes:", err);
    }
  };

  useEffect(() => {
    const fetchTeacherProfile = async () => {
      try {
        const user = await api.get('/teachers/me');
        if (user && user.full_name) {
          setTeacherName(user.full_name);
        }
      } catch (err) {
        console.error("Failed to fetch teacher profile:", err);
      }
    };
    fetchTeacherProfile();
  }, []);

  useEffect(() => {
    let intervalId: any;
    
    const loadInitialData = async () => {
      try {
        const classesData = await api.get('/teachers/classes');
        setClasses(classesData);
        await fetchAllDoubts(classesData);
        
        const poll = () => {
          if (document.visibilityState === 'visible') {
            fetchAllDoubts(classesData);
          }
        };
        
        intervalId = setInterval(poll, 30000);
        
        const handleVisibilityChange = () => {
          if (document.visibilityState === 'visible') {
            poll();
          }
        };
        document.addEventListener('visibilitychange', handleVisibilityChange);
        
        return () => {
          clearInterval(intervalId);
          document.removeEventListener('visibilitychange', handleVisibilityChange);
        };
      } catch (err) {
        console.error("Failed to load classes or doubts:", err);
      }
    };
    
    loadInitialData();
    
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, []);

  const handleRespondDirectly = async (doubtId: string, text: string) => {
    setSubmittingIds(prev => ({ ...prev, [doubtId]: true }));
    try {
      const updatedDoubt = await api.post(`/teachers/doubts/${doubtId}/respond`, {
        response_text: text
      });
      
      setDoubts(prevDoubts => 
        prevDoubts.map(d => d.doubt_id === doubtId ? { 
          ...d, 
          status: updatedDoubt.status, 
          response_text: updatedDoubt.response_text,
          messages: updatedDoubt.messages
        } : d)
      );
      
      setResponseInputs(prev => ({ ...prev, [doubtId]: '' }));
    } catch (err: any) {
      console.error("Failed to respond to doubt directly:", err);
      alert(`Failed to respond: ${err.detail || err.message}`);
    } finally {
      setSubmittingIds(prev => ({ ...prev, [doubtId]: false }));
    }
  };

  const handleResolveDoubt = async (doubtId: string) => {
    setSubmittingIds(prev => ({ ...prev, [doubtId]: true }));
    try {
      const updatedDoubt = await api.post(`/teachers/doubts/${doubtId}/resolve`);
      setDoubts(prevDoubts => 
        prevDoubts.map(d => d.doubt_id === doubtId ? { 
          ...d, 
          status: updatedDoubt.status,
          messages: updatedDoubt.messages
        } : d)
      );
    } catch (err: any) {
      console.error("Failed to resolve doubt:", err);
      alert(`Failed to resolve: ${err.detail || err.message}`);
    } finally {
      setSubmittingIds(prev => ({ ...prev, [doubtId]: false }));
    }
  };

  const handlePlayAudio = (url: string) => {
    if (playingAudioUrl === url && currentAudio) {
      currentAudio.pause();
      setPlayingAudioUrl(null);
      setCurrentAudio(null);
    } else {
      if (currentAudio) {
        currentAudio.pause();
      }
      const audio = new Audio(url);
      audio.play().catch(e => console.error("Audio playback error:", e));
      setPlayingAudioUrl(url);
      setCurrentAudio(audio);
      audio.onended = () => {
        setPlayingAudioUrl(null);
        setCurrentAudio(null);
      };
    }
  };

  const handleRespond = async (doubtId: string) => {
    const text = responseInputs[doubtId]?.trim();
    if (!text) return;
    await handleRespondDirectly(doubtId, text);
    
    // Clear the AI suggestion after successfully sending a reply
    setAiSuggestions(prev => {
      const updated = { ...prev };
      delete updated[doubtId];
      return updated;
    });
  };


  const handleAnalyticsNav = () => {
    if (classes && classes.length > 0) {
      const firstClass = classes[0];
      navigate(`/teacher/analytics/${firstClass.class_id || firstClass.id}`);
    } else {
      navigate('/teacher/analytics');
    }
  };

  const toggleRecording = async (doubtId: string) => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (isRecording) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      } else if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
        mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      }
      setIsRecording(false);
    } else {
      voiceStartTextRef.current = responseInputs[doubtId] || '';

      if (SpeechRecognition) {
        try {
          const recognition = new SpeechRecognition();
          recognitionRef.current = recognition;
          recognition.continuous = true;
          recognition.interimResults = true;
          recognition.lang = 'en-US';

          recognition.onstart = () => {
            setIsRecording(true);
          };

          recognition.onresult = (event: any) => {
            let finalTranscript = '';
            let interimTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; ++i) {
              const transcript = event.results[i][0].transcript;
              if (event.results[i].isFinal) {
                finalTranscript += transcript;
              } else {
                interimTranscript += transcript;
              }
            }

            const currentSpeech = finalTranscript || interimTranscript;
            setResponseInputs(prev => {
              const base = voiceStartTextRef.current;
              const newVal = base ? `${base.trim()} ${currentSpeech.trim()}` : currentSpeech.trim();
              focusAndMoveCursorToEnd(newVal);
              return {
                ...prev,
                [doubtId]: newVal
              };
            });
          };

          recognition.onerror = (err: any) => {
            console.error("Speech recognition error:", err);
            setIsRecording(false);
          };

          recognition.onend = () => {
            setIsRecording(false);
            recognitionRef.current = null;
          };

          recognition.start();
        } catch (err) {
          console.error("Failed to start SpeechRecognition:", err);
          setIsRecording(false);
        }
      } else {
        // Fallback to MediaRecorder + Gemini API
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          const mediaRecorder = new MediaRecorder(stream);
          mediaRecorderRef.current = mediaRecorder;
          audioChunksRef.current = [];

          mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
              audioChunksRef.current.push(e.data);
            }
          };

          mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
            setIsTranscribing(true);
            try {
              const transcription = await transcribeAudioWithGemini(audioBlob);
              if (transcription) {
                setResponseInputs(prev => {
                  const newVal = ((prev[doubtId] || '').trim() + ' ' + transcription.trim()).trim();
                  focusAndMoveCursorToEnd(newVal);
                  return {
                    ...prev,
                    [doubtId]: newVal
                  };
                });
              }
            } catch (err) {
              console.error("Transcription error:", err);
              alert("Failed to transcribe voice. Make sure microphone permission is enabled.");
            } finally {
              setIsTranscribing(false);
            }
          };

          mediaRecorder.start();
          setIsRecording(true);
        } catch (err) {
          console.error("Recording failed to start:", err);
          alert("Failed to access microphone.");
        }
      }
    }
  };

  const generateAIResponse = async (doubtId: string, queryText: string) => {
    if (responseInputs[doubtId]?.trim()) return;
    if (aiSuggestions[doubtId]) return;
    
    setIsGeneratingSuggestions(true);
    try {
      const apiKey = getGeminiApiKey();
      const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`;
      
      const prompt = `You are an expert teaching assistant helping a teacher respond to a student's doubt.
Student's question: "${queryText}"

Provide a direct, helpful, and polite response to this question. Keep it concise (1-3 sentences).
Do not add any prefix, introductory remarks, markdown, or formatting. Output only the raw text response itself.`;

      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }]
        })
      });
      
      if (!response.ok) throw new Error("Gemini suggestions error");
      const data = await response.json();
      let text = data.candidates?.[0]?.content?.parts?.[0]?.text || '';
      text = text.trim();
      if (text) {
        setAiSuggestions(prev => ({
          ...prev,
          [doubtId]: text
        }));
      }
    } catch (err) {
      console.error("Failed to generate AI reply:", err);
    } finally {
      setIsGeneratingSuggestions(false);
    }
  };

  useEffect(() => {
    if (selectedDoubtId) {
      const selectedDoubt = doubts.find(d => d.doubt_id === selectedDoubtId);
      if (selectedDoubt) {
        const isResolved = selectedDoubt.status.toLowerCase() === 'resolved' || selectedDoubt.status.toLowerCase() === 'responded';
        if (!isResolved && selectedDoubt.query_text && selectedDoubt.query_text.trim() !== '') {
          generateAIResponse(selectedDoubtId, selectedDoubt.query_text);
        }
      }
    }
  }, [selectedDoubtId, doubts]);

  const displayedDoubts = doubts.filter(d => selectedFilter === 'all' || d.class_id === selectedFilter);

  return (
    <div className="flex flex-1 w-full h-[100dvh] bg-[#1800ad] font-montserrat text-[#1800ad] overflow-hidden relative">
      
      {/* Mobile Bottom Navigation */}
      <nav className="md:hidden fixed bottom-4 left-4 right-4 bg-[#1800ad] px-6 py-2.5 flex justify-between items-center z-40 rounded-full border-[2px] border-[#f6f4ee] shadow-xl font-montserrat">
        <NavItem icon={<LayoutDashboard size={24} />} onClick={() => navigate('/teacher/home')} />
        <NavItem icon={<BookOpen size={24} />} onClick={handleClassroomNav} />
        <NavItem icon={<BarChart2 size={24} />} onClick={handleAnalyticsNav} />
        <NavItem icon={<MessageSquare size={24} />} active onClick={() => navigate('/teacher/doubts')} />
      </nav>

      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex w-[80px] lg:w-[100px] flex-col items-center justify-between py-8 fixed top-0 bottom-0 left-0 h-full shrink-0 bg-[#1800ad] text-[#f6f4ee] z-30 font-montserrat">
        <div className="flex items-center justify-center shrink-0 mt-4 cursor-pointer" onClick={() => navigate('/teacher/home')}>
          <span className="text-[#f6f4ee] font-val text-[42px] leading-none tracking-widest mt-1 mr-1 notranslate">M</span>
        </div>
        <nav className="flex flex-col gap-6 w-full items-center my-auto">
          <NavItem icon={<LayoutDashboard size={24} />} onClick={() => navigate('/teacher/home')} />
          <NavItem icon={<BookOpen size={24} />} onClick={handleClassroomNav} />
          <NavItem icon={<BarChart2 size={24} />} onClick={handleAnalyticsNav} />
          <NavItem icon={<MessageSquare size={24} />} active onClick={() => navigate('/teacher/doubts')} />
        </nav>
        <div onClick={() => setIsLogoutModalOpen(true)} className="shrink-0 cursor-pointer flex items-center justify-center w-12 h-12 rounded-full border-2 border-[#1800ad] bg-[#f6f4ee] hover:opacity-90 transition-all shadow-sm">
          <span className="text-[#1800ad] font-montserrat font-black text-lg">{teacherName.charAt(0)}</span>
        </div>
      </aside>

      {/* Viewport content */}
      <main className="flex-1 md:ml-[80px] lg:ml-[100px] bg-[#f6f4ee] md:rounded-l-[40px] lg:rounded-l-[50px] p-4 md:p-8 lg:p-10 w-full overflow-y-auto custom-scrollbar pt-3 md:pt-10 pb-24 md:pb-8 lg:pb-10 relative flex flex-col h-[100dvh]">
        <div className="max-w-[1600px] w-full mx-auto flex flex-col h-full">
          
          {/* Header Element */}
          <header className="flex flex-col xl:flex-row xl:justify-between xl:items-end gap-3 border-b-2 border-[#1800ad]/15 pb-2 md:pb-4 mb-3 md:mb-6">
            <div className="flex items-center justify-between w-full lg:w-auto">
              <div>
                <span className="text-xs font-black uppercase tracking-widest text-[#1800ad]/60 font-mono">Live Doubt Resolution Center</span>
                <h1 className="text-2xl md:text-3xl font-black text-[#1800ad] tracking-tight mt-1">
                  Direct Teacher-Student Chat
                </h1>
              </div>
            </div>
          </header>

          <div className="flex flex-1 gap-6 overflow-hidden relative w-full min-h-0">
            
            {/* Left List (Fixed width on desktop, full width on mobile) */}
            <div className={`flex flex-col h-full overflow-hidden w-full md:w-[300px] lg:w-[350px] shrink-0 ${selectedDoubtId ? 'hidden md:flex' : 'flex'}`}>
              



              {/* Doubts scroll list */}
              <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-3 custom-scrollbar">
                {displayedDoubts.length === 0 ? (
                  <div className="bg-white rounded-2xl border-2 border-[#1800ad]/15 flex items-center justify-center p-8 text-center text-[#1800ad]/35 h-full flex-col font-montserrat">
                    <MessageSquare size={32} className="mx-auto mb-2" />
                    <span className="font-extrabold uppercase text-[10px] tracking-widest text-[#1800ad]/60">No doubts found</span>
                  </div>
                ) : (
                  displayedDoubts.map((doubt) => {
                    const isResolved = doubt.status.toLowerCase() === 'resolved' || doubt.status.toLowerCase() === 'responded';
                    const isNew = newDoubtIds.has(doubt.doubt_id);
                    const isSelected = selectedDoubtId === doubt.doubt_id;

                    return (
                      <motion.button
                        key={doubt.doubt_id}
                        layout
                        initial={{ opacity: 0, y: 10 }}
                        animate={isNew ? {
                          opacity: 1,
                          y: 0,
                          backgroundColor: ["#ffffff", "#ffe4e6", "#ffffff"],
                          scale: [1, 1.01, 1],
                          transition: { repeat: 2, duration: 1.2 }
                        } : { opacity: 1, y: 0 }}
                        onClick={() => setSelectedDoubtId(doubt.doubt_id)}
                        className={`w-full text-left p-4 rounded-2xl border-2 transition-all flex flex-col gap-2 relative overflow-hidden shadow-sm ${
                          isSelected
                            ? 'border-[#1800ad] bg-[#1800ad]/5 font-bold shadow-md'
                            : 'border-[#1800ad]/10 bg-white hover:border-[#1800ad]/30'
                        }`}
                      >
                        <div className="flex items-center justify-between w-full">
                          <span className="text-xs font-black text-[#1800ad] truncate max-w-[170px]">
                            {doubt.student_name}
                          </span>
                          <span className={`text-[8px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full border ${
                            doubt.status.toLowerCase() === 'resolved'
                              ? 'bg-emerald-50 border-emerald-250 text-emerald-800'
                              : doubt.status.toLowerCase() === 'responded'
                              ? 'bg-blue-50 border-blue-250 text-blue-800'
                              : 'bg-red-50 border-red-250 text-red-800'
                          }`}>
                            {doubt.status.toLowerCase() === 'resolved' ? 'Resolved' : doubt.status.toLowerCase() === 'responded' ? 'Responded' : 'Pending'}
                          </span>
                        </div>
                        <p className="text-xs text-[#1800ad]/75 truncate font-semibold">
                          {doubt.query_text}
                        </p>
                        <span className="text-[9px] font-bold text-[#1800ad]/50 uppercase tracking-wide">
                          {doubt.subjectLabel}
                        </span>
                      </motion.button>
                    );
                  })
                )}
              </div>

            </div>

            {/* RHS: Right Panel (Detail / Response panel) */}
            <div className={`flex-1 flex flex-col h-full overflow-hidden bg-white rounded-[28px] border-2 border-[#1800ad]/15 p-5 relative ${selectedDoubtId ? 'flex' : 'hidden md:flex'}`}>
              {!selectedDoubtId ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center text-[#1800ad]/35 p-8">
                  <MessageSquare size={42} className="text-[#1800ad]/20 mb-3" />
                  <span className="font-black text-xs uppercase tracking-widest text-[#1800ad]/60 mb-1">
                    Select a Doubt
                  </span>
                  <p className="text-xs font-semibold max-w-xs leading-relaxed">
                    Choose a doubt card from the left panel to review attempt details and respond.
                  </p>
                </div>
              ) : (() => {
                const selectedDoubt = doubts.find(d => d.doubt_id === selectedDoubtId);
                if (!selectedDoubt) return null;
                const isResolved = selectedDoubt.status.toLowerCase() === 'resolved';
                
                return (
                  <div className="flex-1 flex flex-col h-full justify-between">
                    {/* Header */}
                    <div className="flex items-center justify-between border-b border-[#1800ad]/10 pb-4 mb-4 select-none">
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => setSelectedDoubtId(null)}
                          className="md:hidden p-2 bg-[#1800ad]/5 hover:bg-[#1800ad]/10 text-[#1800ad] rounded-full transition-all mr-1.5 flex items-center justify-center border border-[#1800ad]/10"
                          title="Back to doubts list"
                        >
                          <ArrowLeft size={14} />
                        </button>
                        <div>
                          <h2 className="font-black text-xs sm:text-sm text-[#1800ad] leading-tight">{selectedDoubt.student_name}</h2>
                          <span className="text-[9px] font-bold text-[#1800ad]/60 uppercase tracking-wide leading-none block mt-0.5 font-montserrat">
                            {selectedDoubt.subjectLabel}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {selectedDoubt.status.toLowerCase() !== 'resolved' ? (
                          <button
                            type="button"
                            onClick={() => handleResolveDoubt(selectedDoubt.doubt_id)}
                            disabled={submittingIds[selectedDoubt.doubt_id]}
                            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-[#f6f4ee] rounded-full text-xs font-black uppercase tracking-wider transition-all hover:scale-[1.02] active:scale-95 shadow-sm"
                          >
                            {submittingIds[selectedDoubt.doubt_id] ? "Resolving..." : "Mark Resolved"}
                          </button>
                        ) : (
                          <span className="px-4 py-2 bg-emerald-100 border border-emerald-300 text-emerald-800 rounded-full text-xs font-black uppercase tracking-wider">
                            Resolved
                          </span>
                        )}
                      </div>
                    </div>
 
                    {/* Question Content */}
                    <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-4 mb-4 custom-scrollbar text-left">
                      
                      {/* Tried Before Section (Attempt Info) */}
                      {selectedDoubt.tried_before && (
                        <div className="flex flex-col gap-1.5 max-w-[90%] self-start select-none">
                          <span className="text-[8px] font-black uppercase tracking-wider text-amber-850 select-none">
                            Student's Attempt details:
                          </span>
                          <div className="p-4 bg-amber-50/50 text-amber-900 border border-amber-250 rounded-[22px] rounded-tl-none text-xs font-semibold italic leading-relaxed">
                            "{selectedDoubt.attempt_text || 'No details provided.'}"
                          </div>
                        </div>
                      )}

                      {/* Chat Messages Log */}
                      {selectedDoubt.messages && selectedDoubt.messages.length > 0 ? (
                        <div className="flex flex-col gap-4">
                          {selectedDoubt.messages.map((msg: any, mIdx: number) => {
                            const isMe = msg.sender === 'teacher';
                            return (
                              <div 
                                key={msg.id || mIdx} 
                                className={`flex flex-col gap-1 max-w-[85%] ${isMe ? 'self-end items-end' : 'self-start'}`}
                              >
                                <span className="text-[8px] font-black uppercase tracking-wider text-[#1800ad]/55 select-none">
                                  {isMe ? 'You (Teacher)' : selectedDoubt.student_name}
                                </span>
                                <div className={`p-4 rounded-[22px] text-xs sm:text-sm font-semibold leading-relaxed ${
                                  isMe 
                                    ? 'bg-[#1800ad] text-[#f6f4ee] rounded-tr-none' 
                                    : 'bg-[#f6f4ee] text-[#1800ad] border border-[#1800ad]/15 rounded-tl-none'
                                }`}>
                                  {msg.text}
                                </div>
                                {isMe && msg.audio_url && (
                                  <button
                                    type="button"
                                    onClick={() => handlePlayAudio(msg.audio_url)}
                                    className="mt-1 flex items-center gap-1.5 self-end px-3 py-1 bg-[#1800ad] text-[#f6f4ee] rounded-full text-[9px] font-black uppercase tracking-wider transition-all hover:scale-[1.03] active:scale-95"
                                  >
                                    Play Voice Note
                                  </button>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <>
                          {/* Fallback Question Bubble if messages list not loaded */}
                          <div className="flex flex-col gap-1.5 max-w-[90%] self-start">
                            <span className="text-[8px] font-black uppercase tracking-wider text-[#1800ad]/55 select-none">
                              Student's Question:
                            </span>
                            <div className="p-4 bg-[#f6f4ee] text-[#1800ad] border border-[#1800ad]/15 rounded-[22px] rounded-tl-none text-xs sm:text-sm font-semibold leading-relaxed">
                              {selectedDoubt.query_text}
                            </div>
                          </div>
                          {selectedDoubt.response_text && (
                            <div className="flex flex-col gap-1.5 max-w-[90%] self-end items-end">
                              <span className="text-[8px] font-black uppercase tracking-wider text-[#1800ad]/55 select-none">
                                Your Reply:
                              </span>
                              <div className="p-4 bg-[#1800ad] text-[#f6f4ee] rounded-[22px] rounded-tr-none text-xs sm:text-sm font-semibold leading-relaxed">
                                {selectedDoubt.response_text}
                              </div>
                            </div>
                          )}
                        </>
                      )}

                      {/* Suggested AI Reply Draft */}
                      {aiSuggestions[selectedDoubt.doubt_id] && (
                        <div className="flex flex-col gap-1.5 max-w-[85%] self-end items-end mt-2 select-none shrink-0">
                          <span className="text-[9px] font-black uppercase tracking-wider text-[#1800ad]/55 select-none">
                            Suggested AI Reply:
                          </span>
                          <div className="p-4 bg-gradient-to-br from-[#1800ad]/5 to-[#1800ad]/10 text-[#1800ad] border-2 border-dashed border-[#1800ad]/20 rounded-[22px] rounded-tr-none text-xs sm:text-sm font-semibold leading-relaxed shadow-sm">
                            <p className="italic">"{aiSuggestions[selectedDoubt.doubt_id]}"</p>
                            <div className="mt-3.5 flex gap-2 justify-end">
                              <button
                                type="button"
                                onClick={async () => {
                                  const draftText = aiSuggestions[selectedDoubt.doubt_id];
                                  if (!draftText) return;
                                  await handleRespondDirectly(selectedDoubt.doubt_id, draftText);
                                  setResponseInputs(prev => ({
                                    ...prev,
                                    [selectedDoubt.doubt_id]: ''
                                  }));
                                  setAiSuggestions(prev => {
                                    const updated = { ...prev };
                                    delete updated[selectedDoubt.doubt_id];
                                    return updated;
                                  });
                                }}
                                className="px-3.5 py-1.5 bg-[#1800ad] hover:bg-[#1800ad]/90 text-[#f6f4ee] text-[10px] font-black uppercase tracking-wider rounded-full transition-all active:scale-95 flex items-center gap-1 shadow-md hover:scale-[1.02]"
                              >
                                <Check size={11} className="stroke-[2.5]" /> Approve
                              </button>
                              <button
                                type="button"
                                onClick={() => {
                                  setAiSuggestions(prev => {
                                    const updated = { ...prev };
                                    delete updated[selectedDoubt.doubt_id];
                                    return updated;
                                  });
                                }}
                                className="px-3.5 py-1.5 bg-white border border-[#1800ad]/20 hover:bg-gray-50 text-[#1800ad]/75 text-[10px] font-black uppercase tracking-wider rounded-full transition-all active:scale-95 flex items-center gap-1 hover:border-[#1800ad]/40"
                              >
                                <X size={11} className="stroke-[2.5]" /> Dismiss
                              </button>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Input Reply Area */}
                    {!isResolved && (
                      <div className="pt-4 border-t border-[#1800ad]/10 flex flex-col gap-2 shrink-0">
                        
                        {/* Input container with Mic button and Send arrow button */}
                        <div className="relative">
                          <input
                            type="text"
                            ref={chatInputRef}
                            value={responseInputs[selectedDoubt.doubt_id] || ''}
                            onChange={(e) => setResponseInputs(prev => ({ ...prev, [selectedDoubt.doubt_id]: e.target.value }))}
                            placeholder={isTranscribing ? "Transcribing voice using Gemini..." : `Type or record reply to ${selectedDoubt.student_name}...`}
                            disabled={submittingIds[selectedDoubt.doubt_id] || isTranscribing}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                e.preventDefault();
                                handleRespond(selectedDoubt.doubt_id);
                              }
                            }}
                            className="w-full h-12 pl-6 pr-24 bg-[#f6f4ee] border-2 border-[#1800ad] rounded-full text-xs sm:text-sm text-[#1800ad] placeholder:text-[#1800ad]/40 focus:outline-none font-semibold"
                          />
                          <div className="absolute right-1.5 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
                            {/* Microphone Button */}
                            <button
                              type="button"
                              onClick={() => toggleRecording(selectedDoubt.doubt_id)}
                              disabled={submittingIds[selectedDoubt.doubt_id] || isTranscribing}
                              className={`p-2 rounded-full transition-all border ${
                                isRecording 
                                  ? 'bg-[#1800ad] text-[#f6f4ee] border-[#1800ad] animate-breathe' 
                                  : 'text-[#1800ad]/60 border-transparent hover:bg-[#1800ad]/10'
                              }`}
                              title={isRecording ? "Stop recording" : "Record voice response"}
                            >
                              <Mic size={16} />
                            </button>
                            {/* Send Button (just a send arrow) */}
                            <button
                              type="button"
                              onClick={() => handleRespond(selectedDoubt.doubt_id)}
                              disabled={!responseInputs[selectedDoubt.doubt_id]?.trim() || submittingIds[selectedDoubt.doubt_id] || isTranscribing || isRecording}
                              className="p-2 text-[#1800ad] hover:bg-[#1800ad]/10 rounded-full transition-all disabled:opacity-40 flex items-center justify-center"
                              title="Send message"
                            >
                              {submittingIds[selectedDoubt.doubt_id] ? (
                                <div className="w-4 h-4 border-2 border-[#1800ad] border-t-transparent rounded-full animate-spin"></div>
                              ) : (
                                <Send size={16} className="stroke-[2.5]" />
                              )}
                            </button>
                          </div>
                        </div>

                        {isTranscribing && (
                          <div className="text-[10px] text-amber-700 font-semibold italic flex items-center gap-1.5 animate-pulse select-none px-2 mt-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-600 animate-ping"></span> Gemini is transcribing your spoken voice...
                          </div>
                        )}


                      </div>
                    )}

                  </div>
                );
              })()}
            </div>

          </div>

        </div>
      </main>

      {/* MODAL: Logout Confirmation */}
      <LogoutModal isOpen={isLogoutModalOpen} onClose={() => setIsLogoutModalOpen(false)} />
    </div>
  );
}
