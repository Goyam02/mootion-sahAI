import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { 
  ArrowLeft, 
  Mic, 
  Square,
  PlayCircle,
  Beaker,
  FileQuestion,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  X,
  MessageCircle,
  Eye,
  Link2,
  Target,
  RotateCcw,
  Calendar,
  Trash2,
  Sparkles,
  Award,
  BookOpen,
  ArrowUpDown,
  History,
  Check,
  GraduationCap
} from 'lucide-react';
import { Task } from '../data/tasks';
import { getTranslationLanguage } from '../lib/translation';

// --- Shared Utilities for Audio ---
function pcmToBase64(pcmData: Float32Array) {
  const buffer = new ArrayBuffer(pcmData.length * 2);
  const view = new DataView(buffer);
  for (let i = 0; i < pcmData.length; i++) {
    const s = Math.max(-1, Math.min(1, pcmData[i]));
    view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }
  let binary = '';
  const bytes = new Uint8Array(buffer);
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function downsampleAndEncode(buffer: Float32Array, inputSampleRate: number, outputSampleRate: number = 16000): string {
  const sampleRateRatio = inputSampleRate / outputSampleRate;
  const newLength = Math.round(buffer.length / sampleRateRatio);
  const result = new Int16Array(newLength);
  
  let offsetResult = 0;
  let offsetBuffer = 0;
  
  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
    let accum = 0;
    let count = 0;
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
      accum += buffer[i];
      count++;
    }
    const sample = count > 0 ? accum / count : 0;
    const s = Math.max(-1, Math.min(1, sample));
    result[offsetResult] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    offsetResult++;
    offsetBuffer = nextOffsetBuffer;
  }
  
  let binary = '';
  const bytes = new Uint8Array(result.buffer);
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

// --- Activity Base Component ---
export function LiveVoiceActivity({ 
  task, 
  activityName, 
  instructions,
  onDone 
}: { 
  task: Task, 
  activityName: string, 
  instructions: string,
  onDone: () => void 
}) {
  // Activity Specific Steps & Flow State
  const navigate = useNavigate();
  const [resolvedClassId, setResolvedClassId] = useState<string | null>(null);
  const [resolvedChapterId, setResolvedChapterId] = useState<string | null>(null);
  const [analyticsResult, setAnalyticsResult] = useState<{
    concept_score_id: string;
    clarity_score: number;
    accuracy_score: number;
    depth_score: number;
    overall_score: number;
    llm_feedback: string;
    attempt_number: number;
    created_at: string;
  } | null>(null);

  const fallbackTranscriptRef = useRef('');

  const [activePlayState, setActivePlayState] = useState<'intro' | 'prediction' | 'simulation' | 'explaining' | 'grading'>('intro');
  const [predictionChoice, setPredictionChoice] = useState<string | null>(null);
  const [simulationRunning, setSimulationRunning] = useState(false);
  const [simulationPercentage, setSimulationPercentage] = useState(0);
  const [predictionQuestion, setPredictionQuestion] = useState<string>('');
  const [predictionQuestionLoading, setPredictionQuestionLoading] = useState(false);

  // General Audio / Mic State
  const [isRecording, setIsRecording] = useState(false);
  const [isWebSocketActive, setIsWebSocketActive] = useState(false);
  const [aiIsSpeaking, setAiIsSpeaking] = useState(false);
  const [isThinking, setIsThinking] = useState(false);

  // Transcript logs
  const [messages, setMessages] = useState<{ role: 'student' | 'Mootion', text: string }[]>([]);
  const [liveTranscript, setLiveTranscript] = useState('');
  const [textFallbackInput, setTextFallbackInput] = useState('');
  const [useTextMode, setUseTextMode] = useState(false);

  // Counter of adaptive follow-up questions
  const [questionsAnswered, setQuestionsAnswered] = useState(0);
  const maxQuestions = activityName === 'Explain It' ? 4 : 1;

  // Evaluation details
  const [evaluation, setEvaluation] = useState<{
    understandingScore: number;
    expressionScore?: number;
    reasoningScore?: number;
    strengths: string[];
    gaps: string[];
    feedback: string;
    predictionAccuracy?: 'Correct' | 'Incorrect' | 'Not Applicable';
  } | null>(null);

  // Audio queue & web references
  const recognitionRef = useRef<any>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const scriptProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const mstreamRef = useRef<MediaStream | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const [liveModelTranscript, setLiveModelTranscript] = useState('');
  const liveModelTranscriptRef = useRef('');
  const questionsAnsweredRef = useRef(0);
  const messagesRef = useRef<{ role: 'student' | 'Mootion', text: string }[]>([]);
  const nextStartTimeRef = useRef(0);

  // Keep references in sync with active React state to avoid closure errors in callbacks
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    questionsAnsweredRef.current = questionsAnswered;
  }, [questionsAnswered]);

  const updateLiveModelTranscript = (val: string | ((prev: string) => string)) => {
    setLiveModelTranscript(prev => {
      const next = typeof val === 'function' ? val(prev) : val;
      liveModelTranscriptRef.current = next;
      return next;
    });
  };

  const audioQueue = useRef<Float32Array[]>([]);
  const isPlayingQueue = useRef(false);

  // Extract chapter topic context from backend content_json
  const getChapterTopics = (): { title: string; source_snippet: string }[] => {
    const dbTask = (task as any).dbTask;
    if (dbTask?.content_json?.topics && Array.isArray(dbTask.content_json.topics)) {
      return dbTask.content_json.topics;
    }
    return [];
  };

  const getChapterTitle = (): string => {
    const dbTask = (task as any).dbTask;
    return dbTask?.content_json?.chapter_title || task.topic;
  };

  // Get dynamic local summary for Explain It / topics
  const getSyllabusSummary = () => {
    const topics = getChapterTopics();
    if (topics.length > 0) {
      return topics.map(t => t.title).join(", ");
    }
    if (task.subject === 'Physics') {
      if (task.topic.toLowerCase().includes('buoyancy')) {
        return "Floating and Sinking principles, Archimedes' law of fluid upward upthrust, relative fluid densities, and gravitational pull balances on immersed objects.";
      }
      return "Kinetic motion vectors, speed velocity equations, Uniform acceleration multipliers, Newton's mechanical forces, and air resistance friction formulas.";
    }
    if (task.subject === 'Chemistry') {
      return "Subatomic orbital balances, atomic nucleus isotopes, Electron group trends, chemical element reaction combinations, balanced redox formulations, and acid-base pH color indicators.";
    }
    return "";
  };

  // Generate a contextual prediction question via LLM for Predict It
  const generatePredictionQuestion = useCallback(async () => {
    const topics = getChapterTopics();
    const topicCtx = topics.map(t => `${t.title}: ${(t.source_snippet || '').slice(0, 200)}`).join('\n') || task.topic;
    setPredictionQuestionLoading(true);
    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `Generate a single yes/no prediction question about this chapter content to test the student's understanding of key concepts.

Chapter context:
${topicCtx}

Output ONLY the question text. No emojis. No extra text.`,
          context: 'You are generating a prediction question for a science learning activity.'
        })
      });
      const data = await resp.json();
      const q = (data.text || '').trim();
      if (q && !q.includes('GEMINI_API_KEY')) {
        setPredictionQuestion(q);
      } else {
        const ft = topics[0]?.title || task.topic;
        setPredictionQuestion(`Think about what you know about ${ft}. Do you think the core concepts will apply in a real-world scenario?`);
      }
    } catch {
      const ft = topics[0]?.title || task.topic;
      setPredictionQuestion(`Think about what you know about ${ft}. Do you think the core concepts will apply in a real-world scenario?`);
    }
    setPredictionQuestionLoading(false);
  }, [task]);

  // Init default introduction text based on activity mode
  useEffect(() => {
    let initialGreeting = "";
    const isHindi = getTranslationLanguage() === 'hi';
    setAnalyticsResult(null);

    const topics = getChapterTopics();
    const chapterTitle = getChapterTitle();
    const topicNames = topics.map(t => t.title);
    const firstTopic = topicNames[0] || task.topic;

    if (activityName === 'Explain It') {
      initialGreeting = isHindi 
        ? "नमस्ते टीचर! आज हम क्या सीखने जा रहे हैं?" 
        : "Hi teacher! What are we going to learn today?";
      setActivePlayState('explaining');
    } else if (activityName === 'Predict It') {
      const topicSnippet = topics.length > 0 && topics[0].source_snippet
        ? topics[0].source_snippet.slice(0, 120)
        : '';
      const scenario = topicSnippet
        ? `Here's the situation: ${topicSnippet}`
        : `Think about what you know about ${firstTopic}`;
      initialGreeting = `Ooh, prediction time! Today we're exploring ${firstTopic} in ${chapterTitle}. ${scenario} I have a question for you to predict! Make your choice below, then explain your reasoning!`;
      setActivePlayState('prediction');
      generatePredictionQuestion();
    } else if (activityName === 'Spot It') {
      const spotTopic = topicNames.length > 0
        ? topicNames[Math.floor(Math.random() * topicNames.length)]
        : task.topic;
      initialGreeting = `Teacher, look! I found a real-world puzzle about ${spotTopic}. Why does this happen? Explain the science behind it to me!`;
      setActivePlayState('explaining');
    } else if (activityName === 'Connect It') {
      const cards = topicNames.slice(0, 3);
      if (cards.length > 0) {
        initialGreeting = `Let's connect blocks! I have ${cards.length} cards for us: ${cards.join(', ')}. Can you explain how they all connect together in ${chapterTitle}?`;
      } else {
        initialGreeting = `Let's connect blocks about ${task.topic}! Can you connect the key ideas together and explain how they work?`;
      }
      setActivePlayState('explaining');
    }

    setMessages([
      { role: 'Mootion', text: initialGreeting }
    ]);
  }, [activityName, task]);

  useEffect(() => {
    async function fetchClassAndChapter() {
      try {
        const classes = await api.get('/students/classes');
        if (classes && classes.length > 0) {
          const firstClass = classes[0];
          const classId = firstClass.class_id || firstClass.id;
          setResolvedClassId(classId);

          const chapters = await api.get(`/students/classes/${classId}/chapters`);
          if (chapters && chapters.length > 0) {
            let matchedChapter = chapters.find((ch: any) => {
              if (task.id && task.id.includes('_c')) {
                const parts = task.id.split('_');
                const cPart = parts.find(p => p.startsWith('c'));
                if (cPart) {
                  const num = cPart.replace('c', '');
                  return String(ch.chapter_number) === num || ch.chapter_id?.includes(cPart);
                }
              }
              return false;
            });
            if (!matchedChapter) {
              matchedChapter = chapters.find((ch: any) => 
                ch.title.toLowerCase().includes(task.topic.toLowerCase()) ||
                task.topic.toLowerCase().includes(ch.title.toLowerCase())
              );
            }
            if (!matchedChapter) matchedChapter = chapters[0];
            setResolvedChapterId(matchedChapter.chapter_id || matchedChapter.id);
          }
        }
      } catch (err) {
        console.error("Error resolving class/chapter IDs:", err);
      }
    }
    fetchClassAndChapter();
  }, [task]);

  // Handle scrolling of captions
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, liveTranscript, liveModelTranscript, isThinking]);

  // Clean-up speech, audio, and simulation timer on unmount
  useEffect(() => {
    return () => {
      if (simulationTimerRef.current) {
        clearInterval(simulationTimerRef.current);
        simulationTimerRef.current = null;
      }
      stopAllAudioDevices();
    };
  }, []);

  const stopAllAudioDevices = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    try {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (scriptProcessorRef.current) scriptProcessorRef.current.disconnect();
      if (sourceRef.current) sourceRef.current.disconnect();
      if (mstreamRef.current) {
        mstreamRef.current.getTracks().forEach(track => track.stop());
      }
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close();
      }
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    } catch (e) {
      console.warn("Clean-up warning:", e);
    }
  };

  // Speaks using browser speech synthesis for captions + voice sync (fallback / high fidelity)
  const speakVoiceSynthesis = (text: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log("Skipping browser speech synthesis because dynamic Live WebSocket stream is open.");
      return;
    }
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.onstart = () => setAiIsSpeaking(true);
      utterance.onend = () => setAiIsSpeaking(false);
      utterance.onerror = () => setAiIsSpeaking(false);
      
      // Select Google/Microsoft natural voice for premium quality, less robotic
      const voices = window.speechSynthesis.getVoices();
      const isHindiText = /[\u0900-\u097F]/.test(text); // Check if text contains Hindi characters
      const targetLang = isHindiText ? 'hi' : 'en';
      const naturalVoice = voices.find(v => 
        v.lang.startsWith(targetLang) && (
          v.name.toLowerCase().includes('google') ||
          v.name.toLowerCase().includes('natural') ||
          v.name.toLowerCase().includes('aria') ||
          v.name.toLowerCase().includes('jenny') ||
          v.name.toLowerCase().includes('kalpana') ||
          v.name.toLowerCase().includes('hemant') ||
          v.name.toLowerCase().includes('hi-in')
        )
      ) || voices.find(v => v.lang.startsWith(targetLang)) || voices.find(v => v.lang.startsWith('en'));

      if (naturalVoice) {
        utterance.voice = naturalVoice;
        utterance.pitch = 1.0; // keep premium voice natural
      } else {
        utterance.pitch = 1.15; // slightly friendly pitch if robotic fallback
      }
      
      utterance.rate = 1.0;
      window.speechSynthesis.speak(utterance);
    }
  };

  // Play incoming Base64 PCM audio chunk
  const playReturnedAudio = (base64Audio: string) => {
    try {
      const binaryString = atob(base64Audio);
      const len = binaryString.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      const int16Array = new Int16Array(bytes.buffer);
      
      const float32Array = new Float32Array(int16Array.length);
      for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i] / 32768.0;
      }

      audioQueue.current.push(float32Array);
      if (!isPlayingQueue.current) {
        playNextPCMChunk();
      }
    } catch (err) {
      console.error("PCM decoding failed", err);
    }
  };

  const playNextPCMChunk = () => {
    if (audioQueue.current.length === 0) {
      isPlayingQueue.current = false;
      setAiIsSpeaking(false);
      
      // Commit Mootion's live model streaming speech transcript to dialogue log when they finish talking
      if (liveModelTranscriptRef.current) {
        const text = liveModelTranscriptRef.current;
        setMessages(prev => [...prev, { role: 'Mootion', text }]);
        updateLiveModelTranscript('');
        
        const nextCount = questionsAnsweredRef.current + 1;
        setQuestionsAnswered(nextCount);
        
        const isFinished = nextCount >= maxQuestions;
        if (isFinished) {
          setTimeout(() => {
            triggerGradingEvaluation([...messagesRef.current, { role: 'Mootion', text }]);
          }, 1500);
        }
      }
      return;
    }

    isPlayingQueue.current = true;
    setAiIsSpeaking(true);

    const chunk = audioQueue.current.shift()!;
    if (!audioContextRef.current) {
      isPlayingQueue.current = false;
      setAiIsSpeaking(false);
      return;
    }

    try {
      // Create a 24000Hz (24kHz) sample rate buffer for high-fidelity native voice output
      const audioBuffer = audioContextRef.current.createBuffer(1, chunk.length, 24000);
      audioBuffer.getChannelData(0).set(chunk);

      const bufferSource = audioContextRef.current.createBufferSource();
      bufferSource.buffer = audioBuffer;
      bufferSource.connect(audioContextRef.current.destination);

      // Perform jitter-free consecutive audio scheduling
      const currentTime = audioContextRef.current.currentTime;
      if (nextStartTimeRef.current < currentTime) {
        nextStartTimeRef.current = currentTime; // Align to now if queue was silent
      }

      bufferSource.start(nextStartTimeRef.current);
      nextStartTimeRef.current += audioBuffer.duration;

      bufferSource.onended = () => {
        playNextPCMChunk();
      };
    } catch (e) {
      console.error("PCM segment failed, continuing...", e);
      playNextPCMChunk();
    }
  };

  // Start real-time microphone stream connected to WebSocket Live
  const startRecordingVoice = async () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setAiIsSpeaking(false);
    }

    try {
      // 1. Get micro input
      const mstream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mstreamRef.current = mstream;

      // 2. Setup WebSocket Live Connection passing activity details as query parameters
      const isSec = window.location.protocol === 'https:';
      const wsUrl = `${isSec ? 'wss' : 'ws'}://${window.location.host}/live?activity=${encodeURIComponent(activityName)}&topic=${encodeURIComponent(task.topic)}&subject=${encodeURIComponent(task.subject)}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("WebSocket connected successfully to Gemini Live.");
        setIsWebSocketActive(true);
      };

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          
          if (parsed.audio) {
            playReturnedAudio(parsed.audio);
          }
          
          if (parsed.interrupted) {
            audioQueue.current = [];
            isPlayingQueue.current = false;
            setAiIsSpeaking(false);
            updateLiveModelTranscript('');
          }

          if (parsed.userTranscript) {
            setIsThinking(false);
            setLiveTranscript(prev => (prev + " " + parsed.userTranscript).trim());
          }

          if (parsed.modelTranscript) {
            setIsThinking(false);
            updateLiveModelTranscript(prev => prev + parsed.modelTranscript);
          }
        } catch (e) {
          console.warn("Failed reading live ws audio packet", e);
        }
      };

      ws.onerror = (err) => {
        console.error("Live WebSocket Error:", err);
        setIsWebSocketActive(false);
      };

      ws.onclose = () => {
        console.log("Live WebSocket disconnected");
        setIsWebSocketActive(false);
      };

      // 3. Bind AudioContext (native sample rate) and downsample in processor to 16kHz Mono PCM
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const actx = new AudioCtx();
      audioContextRef.current = actx;

      const source = actx.createMediaStreamSource(mstream);
      sourceRef.current = source;

      const processor = actx.createScriptProcessor(2048, 1, 1);
      scriptProcessorRef.current = processor;

      source.connect(processor);
      processor.connect(actx.destination);

      processor.onaudioprocess = (e) => {
        if (ws.readyState !== WebSocket.OPEN) return;
        const channelData = e.inputBuffer.getChannelData(0);
        // Downsample Float32 mic stream dynamically on-the-fly to 16kHz PCM Base64
        const base64PCM = downsampleAndEncode(channelData, actx.sampleRate, 16000);
        ws.send(JSON.stringify({ audio: base64PCM }));
      };

      // Browser-native SpeechRecognition Fallback
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';
        
        recognition.onresult = (event: any) => {
          let interimTranscript = '';
          let finalTranscript = '';
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              finalTranscript += event.results[i][0].transcript;
            } else {
              interimTranscript += event.results[i][0].transcript;
            }
          }
          if (finalTranscript) {
            fallbackTranscriptRef.current = (fallbackTranscriptRef.current + " " + finalTranscript).trim();
          }
        };

        recognition.onend = () => {
          console.log("SpeechRecognition fallback ended");
        };

        recognition.start();
        recognitionRef.current = recognition;
      }

      setIsRecording(true);
    } catch (err) {
      console.warn("Hardware mic blocked or unavailable", err);
      // Fallback: Let speech caption typing text handle input
      setIsRecording(true);
    }
  };

  const stopRecordingVoice = () => {
    setIsRecording(false);
    
    // Stop Microphone device recording and close websocket connection
    if (scriptProcessorRef.current) {
      scriptProcessorRef.current.disconnect();
      scriptProcessorRef.current = null;
    }
    if (sourceRef.current) {
      sourceRef.current.disconnect();
      sourceRef.current = null;
    }
    if (mstreamRef.current) {
      mstreamRef.current.getTracks().forEach(track => track.stop());
      mstreamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsWebSocketActive(false);

    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }

    // Submit any remaining student live speech transcript
    let finalStudentText = liveTranscript.trim();
    if (!finalStudentText && fallbackTranscriptRef.current.trim()) {
      finalStudentText = fallbackTranscriptRef.current.trim();
    }
    fallbackTranscriptRef.current = '';

    if (finalStudentText) {
      setMessages(prev => [...prev, { role: 'student', text: finalStudentText }]);
      setLiveTranscript('');
    }

    // Submit any remaining model live speech transcript
    if (liveModelTranscriptRef.current) {
      const text = liveModelTranscriptRef.current;
      setMessages(prev => [...prev, { role: 'Mootion', text }]);
      updateLiveModelTranscript('');
    }
  };

  const toggleRecording = () => {
    if (isRecording) {
      stopRecordingVoice();
    } else {
      startRecordingVoice();
    }
  };

  // Submit actual user voice transcript / fallback typing text to Mootion
  const submitVoiceTranscript = async (text: string) => {
    if (!text.trim()) return;

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ text }));
      setMessages(prev => [...prev, { role: 'student' as const, text }]);
      setLiveTranscript('');
      setTextFallbackInput('');
      setIsThinking(true);
      return;
    }

    const updatedMessages = [...messages, { role: 'student' as const, text }];
    setMessages(updatedMessages);
    setLiveTranscript('');
    setTextFallbackInput('');
    setIsThinking(true);

    const isCurrentStepFinished = (questionsAnswered + 1) >= maxQuestions;

    try {
      // Build clever context prompting for Mootion child dialog simulation
      const topics = getChapterTopics();
      const topicContext = topics.length > 0
        ? topics.map(t => `- ${t.title}${t.source_snippet ? ': ' + t.source_snippet.slice(0, 100) : ''}`).join('\n')
        : task.topic;
      let promptText = `Dialogue History:
${messages.map(m => `${m.role}: ${m.text}`).join('\n')}
Student: ${text}

You are Mootion, a curious 15-year-old child who loves building blocks and exploring science.
Explain mode: "${activityName}" on subject topic "${task.topic}" under class "${task.subject}".
Chapter context:
${topicContext}
${activityName === 'Explain It' ? "Act completely amazed! Ask a naive, slightly innocent but clever question to challenge the student's concept statement." : ""}
${activityName === 'Predict It' ? "Acknowledge their prediction choice. Ask them to explain the scientific reasoning behind their prediction and connect it back to the chapter concepts." : ""}
${activityName === 'Spot It' ? "Ask one curious naive question about the real-world phenomenon and the underlying science." : ""}
${activityName === 'Connect It' ? "Acknowledge their explanation. Ask one final question tying the concepts together." : ""}

Respond in 1-2 charming sentences as Mootion. Maintain child-like wonder. Do not repeat greeting messages. Keep response highly concise.`;

      if (activityName === 'Explain It') {
        promptText = `Dialogue History:
${messages.map(m => `${m.role}: ${m.text}`).join('\n')}
Student: ${text}

You are an expert, empathetic, and highly engaging tutor. Your goal is to help the user learn and deeply understand: "${task.topic}" under class "${task.subject}".
Follow these core behaviors:
1. Be Conversational & Natural: Speak like a friendly human mentor.
2. Socratic Method: Ask guiding questions instead of just giving answers.
3. Bite-Sized Information: Ask ONLY ONE question at a time to check understanding. NEVER ask multiple consecutive questions!
4. Adapt to the User: Simplify if they struggle, advance if they understand.
5. Use Vivid Analogies.

Activity: ${activityName}
${activityName === 'Explain It' ? "Follow up on the student's explanation with exactly ONE Socratic question to probe their logic." : ""}

Respond in 1-2 conversational sentences. Ask EXACTLY ONE question. Never refer to yourself as an AI.`;
      }

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: promptText })
      });

      const data = await response.json();
      const mootionReply = data.text || "Wow! My brain is spinny but I want to know more! Explain that again?";

      setMessages(p => [...p, { role: 'Mootion' as const, text: mootionReply }]);
      setQuestionsAnswered(q => q + 1);
      setIsThinking(false);
      speakVoiceSynthesis(mootionReply);

      // If we reached the end of the activity turns, trigger dynamic evaluation immediately
      if (isCurrentStepFinished) {
        setTimeout(() => {
          triggerGradingEvaluation([...updatedMessages, { role: 'Mootion', text: mootionReply }]);
        }, 1500);
      }
    } catch (err) {
      console.error("Mootion dialogue api failed", err);
      setIsThinking(false);
      const errReply = "My teddy and I are dizzy! Can you simplify that more?";
      setMessages(p => [...p, { role: 'Mootion' as const, text: errReply }]);
      speakVoiceSynthesis(errReply);
    }
  };

  const submitExplanationForAnalysis = async (transcriptText: string, chapterId: string | null, classId: string | null) => {
    try {
      let finalClassId = classId || resolvedClassId;
      let finalChapterId = chapterId || resolvedChapterId;

      if (!finalClassId || !finalChapterId) {
        const classes = await api.get('/students/classes');
        if (classes && classes.length > 0) {
          const firstClass = classes[0];
          finalClassId = finalClassId || firstClass.class_id || firstClass.id;

          const chapters = await api.get(`/students/classes/${finalClassId}/chapters`);
          if (chapters && chapters.length > 0) {
            let matchedChapter = chapters.find((ch: any) => {
              if (task.id && task.id.includes('_c')) {
                const parts = task.id.split('_');
                const cPart = parts.find(p => p.startsWith('c'));
                if (cPart) {
                  const num = cPart.replace('c', '');
                  return String(ch.chapter_number) === num || ch.chapter_id?.includes(cPart);
                }
              }
              return false;
            });
            if (!matchedChapter) {
              matchedChapter = chapters.find((ch: any) => 
                ch.title.toLowerCase().includes(task.topic.toLowerCase()) ||
                task.topic.toLowerCase().includes(ch.title.toLowerCase())
              );
            }
            if (!matchedChapter) matchedChapter = chapters[0];
            finalChapterId = finalChapterId || matchedChapter.chapter_id || matchedChapter.id;
          }
        }
      }

      if (!finalClassId || !finalChapterId) {
        console.warn("Could not submit explanation: classroom or chapter ID unresolved.");
        return;
      }

      const response = await api.post('/api/analytics/submit-explanation', {
        transcript: transcriptText || "No student explanation provided.",
        chapter_id: finalChapterId,
        class_id: finalClassId
      });

      if (response && response.concept_score_id) {
        setAnalyticsResult(response);
      }
    } catch (err) {
      console.error("Error submitting explanation for analysis:", err);
    }
  };

  // Run real-time appraisal of the complete dialog
  const triggerGradingEvaluation = async (finalTranscript: { role: 'student' | 'Mootion'; text: string }[]) => {
    setActivePlayState('grading');
    setIsThinking(true);

    let transcriptToUse = [...finalTranscript];
    if (isRecording) {
      setIsRecording(false);
      if (scriptProcessorRef.current) { scriptProcessorRef.current.disconnect(); scriptProcessorRef.current = null; }
      if (sourceRef.current) { sourceRef.current.disconnect(); sourceRef.current = null; }
      if (mstreamRef.current) { mstreamRef.current.getTracks().forEach(track => track.stop()); mstreamRef.current = null; }
      if (audioContextRef.current) { audioContextRef.current.close().catch(() => {}); audioContextRef.current = null; }
      if (wsRef.current) { wsRef.current.close(); wsRef.current = null; }
      setIsWebSocketActive(false);
      if (recognitionRef.current) { recognitionRef.current.stop(); recognitionRef.current = null; }

      let finalStudentText = liveTranscript.trim();
      if (!finalStudentText && fallbackTranscriptRef.current.trim()) {
        finalStudentText = fallbackTranscriptRef.current.trim();
      }
      fallbackTranscriptRef.current = '';

      if (finalStudentText) {
        transcriptToUse.push({ role: 'student', text: finalStudentText });
        setMessages(prev => [...prev, { role: 'student', text: finalStudentText }]);
        setLiveTranscript('');
      }
    }

    let predOutcome = "";
    if (activityName === 'Predict It' && predictionChoice) {
      const topics = getChapterTopics();
      const ctx = topics.map(t => `${t.title}: ${(t.source_snippet || '').slice(0, 80)}`).join(' | ') || task.topic;
      predOutcome = `Prediction question: "${predictionQuestion || 'N/A'}". Choice: '${predictionChoice === 'option_a' ? 'Yes' : 'No'}'. Chapter context: ${ctx}. The student predicted and needs to explain their reasoning.`;
    }

    try {
      const resp = await fetch('/api/evaluate-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task,
          activityName,
          transcript: transcriptToUse,
          predictionOutcome: predOutcome || undefined
        })
      });

      const evalData = await resp.json();
      setEvaluation(evalData);
      setIsThinking(false);

      if (evalData.feedback) {
        speakVoiceSynthesis(evalData.feedback);
      }

      // Save Attempt to localStorage history separating each attempt
      saveAttemptToStorage(transcriptToUse, evalData);
    } catch (e) {
      console.error("Evaluation generation error", e);
      setIsThinking(false);
      const fallbackReport = {
        understandingScore: 82,
        expressionScore: 85,
        reasoningScore: 85,
        strengths: ["Good understanding of key concepts", "Clear explanations provided"],
        gaps: ["Can add more detail to explanations", "Try connecting ideas together"],
        feedback: "Wow! Thank you so much for teaching me! I feel super smart now. Let's study more building blocks later!",
        predictionAccuracy: activityName === 'Predict It' ? (predictionChoice ? 'Correct' as const : 'Incorrect' as const) : undefined
      };
      setEvaluation(fallbackReport);
      saveAttemptToStorage(transcriptToUse, fallbackReport);
    }

    const studentText = transcriptToUse
      .filter(m => m.role === 'student')
      .map(m => m.text)
      .join(' ')
      .trim();
    if (studentText) {
      const dbTask = (task as any).dbTask;
      if (dbTask) {
        const classId = dbTask.class_id;
        const assignmentId = dbTask.assignment_id;
        api.post(`/students/classes/${classId}/assignments/${assignmentId}/submit`, {
          transcription_text: studentText,
          language: 'english'
        }).then(res => {
          console.log("Interactive assignment submitted successfully:", res);
        }).catch(err => {
          console.error("Failed to submit interactive assignment:", err);
        });
      } else {
        submitExplanationForAnalysis(studentText, resolvedChapterId, resolvedClassId);
      }
    }
  };

  const saveAttemptToStorage = (
    finalTranscript: { role: 'student' | 'Mootion'; text: string }[], 
    evalResult: any
  ) => {
    try {
      const historyStr = localStorage.getItem('mootion_attempt_history') || '[]';
      const history = JSON.parse(historyStr);
      
      const newAttempt = {
        id: `att_${Date.now()}`,
        taskId: task.id,
        timestamp: new Date().toISOString(),
        subject: task.subject,
        topic: task.topic,
        chapter: `Chapter ${task.id?.includes('c3') ? '3' : '1'}`,
        activityName,
        scores: {
          understanding: evalResult.understandingScore || 80,
          expression: evalResult.expressionScore || evalResult.reasoningScore || 80,
          reasoning: evalResult.reasoningScore || 80,
          accuracy: evalResult.predictionAccuracy || 'Not Applicable'
        },
        strengths: evalResult.strengths || ["Great concept logic"],
        gaps: evalResult.gaps || ["No gaps spotted"],
        feedback: evalResult.feedback || "Good job!",
        transcript: finalTranscript
      };

      history.unshift(newAttempt);
      localStorage.setItem('mootion_attempt_history', JSON.stringify(history));

      // Persist status back to student explore catalog progress
      localStorage.setItem(`status_${task.id}`, 'Completed');
      localStorage.setItem(`status_${task.id}_score`, (evalResult.understandingScore || 80).toString());
    } catch (err) {
      console.error("Failed persisting attempt logs", err);
    }
  };

  const simulationTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startSimulationPlayback = () => {
    setSimulationRunning(true);
    setSimulationPercentage(0);

    const topics = getChapterTopics();
    const topicNames = topics.map(t => t.title);
    const contextStr = topicNames.length > 0 ? topicNames.slice(0, 2).join(' and ') : task.topic;

    let progress = 0;
    simulationTimerRef.current = setInterval(() => {
      progress += 2.5;
      if (progress >= 100) {
        progress = 100;
        setSimulationPercentage(100);
        if (simulationTimerRef.current) clearInterval(simulationTimerRef.current);
        simulationTimerRef.current = null;
        setSimulationRunning(false);
        setActivePlayState('explaining');

        let alertResponse = `The concept analysis for ${contextStr} is complete! Now, can you explain the science behind your prediction? Why do you think the outcome turned out this way? Teach me!`;
        setMessages(p => [...p, { role: 'Mootion', text: alertResponse }]);
        speakVoiceSynthesis(alertResponse);
        return;
      }
      setSimulationPercentage(progress);
    }, 80);
  };

  const renderPredictSimulationBox = () => {
    const topics = getChapterTopics();
    const topicNames = topics.map(t => t.title);
    const contextStr = topicNames.length > 0 ? topicNames.slice(0, 2).join(' and ') : task.topic;

    return (
      <div className="w-full max-w-xl bg-white rounded-3xl p-6 border-2 border-[#1800ad]/10 shadow-inner flex flex-col items-center gap-5 animate-fade-in my-4">
        <h4 className="font-bold text-center text-[#1800ad] text-base uppercase tracking-wider">
          Simulation: {contextStr}
        </h4>

        <div className="w-full bg-gradient-to-br from-indigo-50 to-white rounded-2xl border-2 border-[#1800ad]/10 flex flex-col items-center justify-center gap-3 py-8 px-6">
          {/* Large percentage */}
          <div className="text-6xl font-black text-[#1800ad] font-mono tracking-tight">
            {Math.round(simulationPercentage)}
            <span className="text-2xl ml-0.5">%</span>
          </div>

          {/* Progress bar */}
          <div className="w-full max-w-xs h-4 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-[#1800ad] to-[#4a3aff] rounded-full transition-none"
              style={{ width: `${simulationPercentage}%` }}
            />
          </div>

          {/* Status */}
          <p className="text-sm text-[#1800ad]/70 font-semibold">
            {simulationRunning
              ? `Analyzing ${contextStr}...`
              : 'Press Run Simulation to start'}
          </p>
        </div>

        <button
          onClick={startSimulationPlayback}
          disabled={simulationRunning}
          className="px-7 py-2.5 bg-[#1800ad] hover:bg-[#1800ad]/90 text-white rounded-full font-bold text-sm transition-transform hover:scale-105 active:scale-95 disabled:opacity-50 flex items-center gap-2 shadow-md"
        >
          <PlayCircle size={16} className="stroke-[3]" />
          {simulationRunning ? `Analyzing ${Math.round(simulationPercentage)}%...` : 'Run Simulation'}
        </button>
      </div>
    );
  };

  const renderSpotItContextCard = () => {
    const topics = getChapterTopics();
    const spotTopic = topics.length > 0
      ? topics[Math.floor(Math.random() * topics.length)]
      : null;
    const title = spotTopic?.title || task.topic;
    const snippet = spotTopic?.source_snippet
      ? spotTopic.source_snippet.length > 120
        ? spotTopic.source_snippet.slice(0, 120) + '...'
        : spotTopic.source_snippet
      : `Explore how the concepts in ${title} apply to the real world around us.`;

    return (
      <div className="w-full max-w-xl bg-white rounded-2xl p-5 border-2 border-[#1800ad]/15 shadow-md flex items-start gap-4 mb-3 animate-fade-in">
        <div className="p-3 bg-amber-500/20 text-amber-700 rounded-full">
          <Sparkles size={24} />
        </div>
        <div className="flex flex-col text-left">
          <span className="text-[10px] font-extrabold text-[#1800ad]/50 uppercase tracking-widest">Real-World Phenomenon</span>
          <h4 className="font-bold text-base text-[#1800ad] leading-snug mt-1">
            "{snippet}"
          </h4>
          <p className="text-xs text-[#1800ad]/70 mt-1.5 font-medium">
            Explain the science behind {title}. Teach Mootion!
          </p>
        </div>
      </div>
    );
  };

  const renderConnectItConceptDeck = () => {
    const topics = getChapterTopics();
    const cards = topics.length > 0
      ? topics.slice(0, 3).map((t, i) => ({
          t: t.title,
          d: t.source_snippet
            ? (t.source_snippet.length > 80 ? t.source_snippet.slice(0, 80) + '...' : t.source_snippet)
            : `Key concept in ${getChapterTitle()}`,
          icon: i === 0 ? <Award size={18} /> : i === 1 ? <Beaker size={18} /> : <Target size={18} />
        }))
      : [
          { t: "Core Principle", d: `The fundamental idea behind ${task.topic}`, icon: <Award size={18} /> },
          { t: "Key Mechanism", d: `How ${task.topic} works in practice`, icon: <Beaker size={18} /> },
          { t: "Real-World Link", d: `Where ${task.topic} appears in everyday life`, icon: <Target size={18} /> }
        ];

    return (
      <div className="flex flex-col sm:flex-row gap-3 w-full max-w-xl mb-4 animate-fade-in">
        {cards.map((c, i) => (
          <div key={i} className="flex-1 bg-white border border-[#1800ad]/10 rounded-xl p-4 flex flex-col justify-between hover:shadow transition-shadow">
            <div className="flex justify-between items-center mb-1">
              <span className="font-extrabold text-[10px] text-[#1800ad]/60 uppercase tracking-wide font-mono">Dimension {i+1}</span>
              <div className="text-[#1800ad]/80">{c.icon}</div>
            </div>
            <h5 className="font-bold text-sm text-[#1800ad]">{c.t}</h5>
            <p className="text-[10.5px] text-[#1800ad]/70 mt-1 font-medium leading-relaxed">{c.d}</p>
          </div>
        ))}
      </div>
    );
  };

  if (activePlayState === 'grading' || evaluation) {
    if (isThinking) {
      return (
        <div className="flex-1 w-full bg-[#1800ad] rounded-[32px] p-8 flex flex-col items-center justify-center relative shadow-xl overflow-hidden min-h-[500px]">
          <div className="flex flex-col items-center gap-5 justify-center relative z-10 text-[#f6f4ee]">
            <div className="relative flex items-center justify-center">
              <span className="absolute animate-ping w-16 h-16 rounded-full bg-white/20"></span>
              <div className="w-12 h-12 border-4 border-white/20 border-t-white rounded-full animate-spin"></div>
            </div>
            <h2 className="text-2xl font-black tracking-wide animate-pulse">Analyzing Teacher-Student Transcript...</h2>
            <p className="text-white/60 text-xs font-semibold uppercase tracking-widest">Grading concepts, strengths and learning gaps</p>
          </div>
        </div>
      );
    }

    const correctPredictions = evaluation?.predictionAccuracy === 'Correct';

    return (
      <div className="flex-1 w-full bg-[#1800ad] rounded-[32px] p-6 md:p-8 flex flex-col items-center justify-center relative shadow-xl overflow-hidden min-h-[calc(100vh-80px)] md:min-h-0 md:h-full">
        <div className="absolute -top-32 -left-32 w-80 h-80 bg-emerald-500/15 rounded-full blur-3xl pointer-events-none animate-pulse"></div>
        <div className="absolute -bottom-32 -right-32 w-80 h-80 bg-blue-500/15 rounded-full blur-3xl pointer-events-none animate-pulse"></div>

        <button onClick={onDone} className="absolute top-6 right-6 text-white hover:opacity-75 transition-colors z-20">
          <X size={26} className="stroke-[2.5]" />
        </button>

        <header className="text-center relative z-10 w-full max-w-2xl flex flex-col items-center gap-1 mt-4">
          <div className="p-3 bg-emerald-500/25 text-emerald-300 rounded-full mb-2 shadow-lg">
            <Award size={32} />
          </div>
          <h1 className="text-3xl md:text-5xl font-val text-white tracking-widest" style={{ textShadow: '3px 3px 0 #000' }}>
            EVALUATION COMPLETE
          </h1>
          <h2 className="text-sm md:text-base font-bold text-white/80">{activityName} Log • {task.topic}</h2>
        </header>

        <div className="bg-white p-6 md:p-8 rounded-[28px] shadow-2xl w-full max-w-2xl flex flex-col gap-6 mt-6 relative z-10 border border-[#1800ad]/15 max-h-[60vh] overflow-y-auto custom-scrollbar">
          
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-[#f6f4ee] border border-[#1800ad]/10 rounded-[20px] p-4 flex flex-col items-center justify-center shadow-sm">
              <span className="font-extrabold text-[10px] text-[#1800ad]/60 uppercase tracking-widest mb-1">Conceptual Understanding</span>
              <span className="text-3xl font-black text-[#1800ad]">{evaluation?.understandingScore}%</span>
              <div className="w-full bg-[#1800ad]/10 h-1.5 rounded-full overflow-hidden mt-3 max-w-[120px]">
                <div className="h-full bg-[#1800ad]" style={{ width: `${evaluation?.understandingScore}%` }}></div>
              </div>
            </div>

            <div className="bg-[#f6f4ee] border border-[#1800ad]/10 rounded-[20px] p-4 flex flex-col items-center justify-center shadow-sm">
              <span className="font-extrabold text-[10px] text-[#1800ad]/60 uppercase tracking-widest mb-1">
                {activityName === 'Explain It' ? 'Verbal Expression' : 'Scientific Reasoning'}
              </span>
              <span className="text-3xl font-black text-[#1800ad]">
                {evaluation?.expressionScore || evaluation?.reasoningScore || 80}%
              </span>
              <div className="w-full bg-[#1800ad]/10 h-1.5 rounded-full overflow-hidden mt-3 max-w-[120px]">
                <div className="h-full bg-[#1800ad]" style={{ width: `${evaluation?.expressionScore || evaluation?.reasoningScore || 82}%` }}></div>
              </div>
            </div>
          </div>

          {activityName === 'Predict It' && evaluation?.predictionAccuracy && (
            <div className={`p-4 rounded-[20px] border flex items-center justify-between shadow-sm ${
              correctPredictions 
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800' 
                : 'bg-amber-50 border-amber-200 text-amber-800'
            }`}>
              <div className="flex flex-col gap-0.5">
                <span className="text-[10px] uppercase tracking-wider font-extrabold opacity-70">Outcome Prediction</span>
                <span className="font-bold text-xs">You predicted that the sphere would {predictionChoice}!</span>
              </div>
              <span className={`px-4 py-1.5 text-xs font-black uppercase tracking-widest rounded-full shadow-sm text-white ${
                correctPredictions ? 'bg-emerald-500' : 'bg-amber-500'
              }`}>
                {evaluation.predictionAccuracy} Prediction
              </span>
            </div>
          )}

          {evaluation?.feedback && (
            <div className="bg-blue-50 border border-blue-100 rounded-[20px] p-4 flex items-start gap-3 text-left">
              <span className="text-xl shrink-0">💬</span>
              <div className="flex flex-col">
                <span className="text-[11px] font-black text-[#1800ad]/60 uppercase tracking-wider">Mootion's Audit Report</span>
                <p className="text-xs text-[#1800ad]/80 italic font-semibold leading-relaxed mt-1">
                  "{evaluation.feedback}"
                </p>
              </div>
            </div>
          )}

          {analyticsResult && (
            <div className="bg-[#f0f4ff] border-2 border-[#1800ad]/20 rounded-[24px] p-5 flex flex-col gap-4 text-left shadow-sm">
              <div className="flex items-center gap-2">
                <span className="text-xl">✨</span>
                <span className="font-black text-xs text-[#1800ad] uppercase tracking-widest font-mono">
                  Conceptual Explanation Evaluation (Attempt #{analyticsResult.attempt_number})
                </span>
              </div>
              
              <div className="flex flex-col gap-3">
                {/* Clarity score bar */}
                <div className="flex flex-col gap-1">
                  <div className="flex justify-between text-xs font-bold text-[#1800ad]">
                    <span>Clarity</span>
                    <span>{analyticsResult.clarity_score}/10</span>
                  </div>
                  <div className="w-full bg-[#1800ad]/10 h-2 rounded-full overflow-hidden">
                    <div 
                      className={`h-full transition-all duration-500 ${
                        analyticsResult.clarity_score > 7 ? 'bg-emerald-500' : analyticsResult.clarity_score >= 4 ? 'bg-amber-500' : 'bg-rose-500'
                      }`} 
                      style={{ width: `${analyticsResult.clarity_score * 10}%` }}
                    ></div>
                  </div>
                </div>

                {/* Accuracy score bar */}
                <div className="flex flex-col gap-1">
                  <div className="flex justify-between text-xs font-bold text-[#1800ad]">
                    <span>Accuracy</span>
                    <span>{analyticsResult.accuracy_score}/10</span>
                  </div>
                  <div className="w-full bg-[#1800ad]/10 h-2 rounded-full overflow-hidden">
                    <div 
                      className={`h-full transition-all duration-500 ${
                        analyticsResult.accuracy_score > 7 ? 'bg-emerald-500' : analyticsResult.accuracy_score >= 4 ? 'bg-amber-500' : 'bg-rose-500'
                      }`} 
                      style={{ width: `${analyticsResult.accuracy_score * 10}%` }}
                    ></div>
                  </div>
                </div>

                {/* Depth score bar */}
                <div className="flex flex-col gap-1">
                  <div className="flex justify-between text-xs font-bold text-[#1800ad]">
                    <span>Depth</span>
                    <span>{analyticsResult.depth_score}/10</span>
                  </div>
                  <div className="w-full bg-[#1800ad]/10 h-2 rounded-full overflow-hidden">
                    <div 
                      className={`h-full transition-all duration-500 ${
                        analyticsResult.depth_score > 7 ? 'bg-emerald-500' : analyticsResult.depth_score >= 4 ? 'bg-amber-500' : 'bg-rose-500'
                      }`} 
                      style={{ width: `${analyticsResult.depth_score * 10}%` }}
                    ></div>
                  </div>
                </div>
              </div>

              {analyticsResult.llm_feedback && (
                <div className="bg-white border border-[#1800ad]/10 rounded-xl p-3 text-xs text-[#1800ad]/80 leading-relaxed font-semibold">
                  {analyticsResult.llm_feedback}
                </div>
              )}

              <button
                type="button"
                onClick={() => navigate('/student/analytics')}
                className="w-full py-2.5 bg-[#1800ad] hover:bg-[#1800ad]/90 text-white rounded-full font-black text-xs uppercase tracking-wider shadow transition-all hover:scale-101 active:scale-99"
              >
                View Full Analytics
              </button>
            </div>
          )}

          <div className="flex flex-col gap-4 text-left">
            <div className="flex flex-col gap-2">
              <h5 className="font-black text-xs text-[#1800ad] uppercase tracking-widest flex items-center gap-1.5">
                <CheckCircle2 size={14} className="text-emerald-500" />
                Key Conceptual Strengths
              </h5>
              <div className="flex flex-wrap gap-1.5">
                {evaluation?.strengths?.map((str, idx) => (
                  <span key={idx} className="bg-emerald-50 text-emerald-800 border border-emerald-100 px-3 py-1 font-bold text-xs rounded-full">
                    {str}
                  </span>
                )) || <span className="text-xs text-gray-500">No strengths logged.</span>}
              </div>
            </div>

            <div className="flex flex-col gap-2 mt-1">
              <h5 className="font-black text-xs text-[#1800ad] uppercase tracking-widest flex items-center gap-1.5">
                <Target size={14} className="text-amber-500" />
                Gaps & Misconceptions Detected
              </h5>
              <div className="flex flex-col gap-1.5">
                {evaluation?.gaps?.map((gap, idx) => (
                  <div key={idx} className="bg-amber-50 text-amber-950 border border-amber-100 px-3 py-2 font-semibold text-xs rounded-xl flex items-start gap-1.5">
                    <span className="text-xs text-amber-600 mt-0.5">•</span>
                    <span>{gap}</span>
                  </div>
                )) || <p className="text-xs font-bold text-emerald-600 bg-emerald-50 p-3 rounded-xl w-full text-center">Perfect understanding! No learning gaps detected.</p>}
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-[#1800ad]/10">
            <button 
              type="button"
              onClick={() => {
                setEvaluation(null);
                setAnalyticsResult(null);
                setMessages([{ role: 'Mootion', text: `Let's practice again! Let's explain ${task.topic} once and see if we can do even better!` }]);
                setQuestionsAnswered(0);
                setActivePlayState(activityName === 'Predict It' ? 'prediction' : 'explaining');
              }} 
              className="px-5 py-2.5 rounded-full font-bold border-2 border-[#1800ad] text-[#1800ad] hover:bg-[#1800ad]/5 transition-colors text-xs"
            >
              Try Again
            </button>
            <button 
              type="button"
              onClick={onDone} 
              className="px-5 py-2.5 rounded-full font-bold bg-[#1800ad] text-white hover:bg-[#1800ad]/90 transition-colors shadow-md text-xs"
            >
              Completed Done
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 w-full bg-[#1800ad] rounded-[32px] p-5 md:p-8 flex flex-col items-center justify-center relative shadow-xl overflow-hidden min-h-[calc(100vh-80px)] md:min-h-0 md:h-full">
      <button onClick={onDone} className="absolute top-6 right-6 text-white hover:opacity-75 transition-colors z-20">
        <X size={26} className="stroke-[2.5]" />
      </button>

      <header className="text-center relative z-10 w-full max-w-xl">
        <h1 className="text-3xl md:text-5xl lg:text-5xl font-val text-white tracking-widest leading-none" style={{ textShadow: '3px 3px 0 #000' }}>
          {activityName.toUpperCase()}
        </h1>
        <h2 className="text-base md:text-lg font-bold text-white mt-1.5 uppercase tracking-wide opacity-90">{task.topic}</h2>
      </header>

      <div className="flex w-full mt-4 flex-col items-center justify-center relative z-10">
        


        {activePlayState === 'prediction' && (
          <div className="flex flex-col gap-4 w-full max-w-xl items-center my-4 animate-fade-in text-center">
            {predictionQuestionLoading ? (
              <p className="text-white/70 font-semibold text-sm animate-pulse">
                Generating prediction question...
              </p>
            ) : (
              <p className="text-white font-bold text-base max-w-md leading-snug">
                "{predictionQuestion || `Based on what you know about ${getChapterTopics().map(t => t.title).slice(0, 2).join(' and ') || task.topic}, what do you predict?`}"
              </p>
            )}
            <div className="flex gap-4 mt-2 w-full max-w-sm justify-center">
              <button 
                type="button"
                onClick={() => { setPredictionChoice('option_a'); setActivePlayState('simulation'); }} 
                className="flex-1 py-4 bg-white hover:bg-[#f6f4ee] text-[#1800ad] hover:scale-103 font-bold rounded-2xl border-2 border-transparent transition-all shadow-md active:scale-95 text-xs uppercase font-black"
              >
                Yes
              </button>
              <button 
                type="button"
                onClick={() => { setPredictionChoice('option_b'); setActivePlayState('simulation'); }} 
                className="flex-1 py-4 bg-white hover:bg-[#f6f4ee] text-[#1800ad] hover:scale-103 font-bold rounded-2xl border-2 border-transparent transition-all shadow-md active:scale-95 text-xs uppercase font-black"
              >
                No
              </button>
            </div>
          </div>
        )}

        {activePlayState === 'simulation' && renderPredictSimulationBox()}

        {activityName === 'Spot It' && activePlayState === 'explaining' && renderSpotItContextCard()}

        {activityName === 'Connect It' && activePlayState === 'explaining' && renderConnectItConceptDeck()}

        {activePlayState === 'explaining' && (
          <div className="h-10 flex gap-1 items-center justify-center mb-5">
            {aiIsSpeaking ? (
              <div className="flex gap-1 items-end h-8">
                <span className="w-1.5 bg-[#f6f4ee] rounded-full animate-pulse h-6" style={{ animationDelay: '0.1s' }}></span>
                <span className="w-1.5 bg-[#f6f4ee] rounded-full animate-pulse h-8" style={{ animationDelay: '0.3s' }}></span>
                <span className="w-1.5 bg-[#f6f4ee] rounded-full animate-pulse h-5" style={{ animationDelay: '0.2s' }}></span>
                <span className="w-1.5 bg-[#f6f4ee] rounded-full animate-pulse h-7" style={{ animationDelay: '0.5s' }}></span>
                <span className="w-1.5 bg-[#f6f4ee] rounded-full animate-pulse h-4" style={{ animationDelay: '0.4s' }}></span>
              </div>
            ) : null}
          </div>
        )}

        {activePlayState === 'explaining' && (
          <div className="flex flex-col items-center justify-center gap-4">
            {useTextMode ? (
              <div className="flex flex-col items-center gap-3 w-full max-w-lg">
                <textarea
                  value={textFallbackInput}
                  onChange={(e) => setTextFallbackInput(e.target.value)}
                  placeholder="Type your explanation here..."
                  rows={5}
                  className="w-full bg-white text-[#1800ad] placeholder-[#1800ad]/40 border-2 border-[#1800ad]/20 rounded-2xl p-4 text-sm font-semibold focus:outline-none focus:border-[#1800ad] resize-none"
                />
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => { setUseTextMode(false); setTextFallbackInput(''); }}
                    className="px-4 py-2 border-2 border-white/30 text-white rounded-full text-xs font-black uppercase tracking-wider hover:bg-white/10 transition-colors"
                  >
                    Use Mic
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (!textFallbackInput.trim()) return;
                      setMessages(prev => [...prev, { role: 'student', text: textFallbackInput.trim() }]);
                      setTextFallbackInput('');
                      setUseTextMode(false);
                    }}
                    disabled={!textFallbackInput.trim()}
                    className="px-6 py-2 bg-white text-[#1800ad] rounded-full text-xs font-black uppercase tracking-wider hover:bg-[#f6f4ee] transition-colors disabled:opacity-50"
                  >
                    Submit Explanation
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <div className="relative flex items-center justify-center">
                  {isRecording && (
                    <>
                      <div className="absolute w-36 h-36 bg-white/25 rounded-full animate-ping" style={{ animationDuration: '2.5s' }}></div>
                      <div className="absolute w-28 h-28 bg-white/15 rounded-full animate-pulse" style={{ animationDuration: '1.2s' }}></div>
                    </>
                  )}

                  <button 
                    type="button"
                    onClick={toggleRecording}
                    disabled={isThinking}
                    className={`w-24 h-24 rounded-full flex items-center justify-center hover:scale-105 active:scale-95 transition-all shadow-xl duration-300 relative z-10 bg-white text-[#1800ad] disabled:opacity-50 ${isRecording ? 'animate-pulse' : ''}`}
                    title={isRecording ? "Stop and Submit Voice" : "Start Speaking"}
                  >
                    <Mic size={40} className="text-[#1800ad]" />
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => setUseTextMode(true)}
                  className="text-white/60 hover:text-white text-[11px] font-semibold underline underline-offset-2 transition-colors"
                >
                  or type your answer
                </button>
              </div>
            )}
          </div>
        )}



        <button 
          onClick={() => triggerGradingEvaluation(messages)}
          className="mt-6 px-8 py-3 bg-[#f6f4ee] hover:bg-white text-[#1800ad] rounded-full font-black text-xs transition-all shadow-md z-10 border-2 border-[#1800ad]/30 hover:border-[#1800ad] uppercase tracking-wider h-11"
        >
          Finish & Grade Session
        </button>
      </div>

    </div>
  );
}


// --- Dynamic Attempt History Panel Component ---
interface AttemptLog {
  id: string;
  taskId: string;
  timestamp: string;
  subject: string;
  topic: string;
  chapter: string;
  activityName: string;
  scores: {
    understanding: number;
    expression?: number;
    reasoning?: number;
    accuracy?: string;
  };
  strengths: string[];
  gaps: string[];
  feedback: string;
  transcript: { role: 'student' | 'Mootion'; text: string }[];
}

export function AttemptHistoryPanel({ taskId }: { taskId: string }) {
  const [history, setHistory] = useState<AttemptLog[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [isTeacherMode, setIsTeacherMode] = useState(false);
  const [teacherComments, setTeacherComments] = useState<Record<string, string>>({});
  const [scoreOverrides, setScoreOverrides] = useState<Record<string, number>>({});

  const loadHistoryLogs = () => {
    try {
      const logsStr = localStorage.getItem('mootion_attempt_history') || '[]';
      const parsed: AttemptLog[] = JSON.parse(logsStr);
      const pathLogs = parsed.filter(p => p.taskId === taskId);
      setHistory(pathLogs);
    } catch (e) {
      console.error("Load performance history error", e);
    }
  };

  useEffect(() => {
    loadHistoryLogs();
    
    const handler = () => loadHistoryLogs();
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, [taskId]);

  const toggleExpand = (id: string) => {
    setExpandedId(prev => prev === id ? null : id);
  };

  const deleteAttemptLog = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const logsStr = localStorage.getItem('mootion_attempt_history') || '[]';
      const parsed: AttemptLog[] = JSON.parse(logsStr);
      const filtered = parsed.filter(p => p.id !== id);
      localStorage.setItem('mootion_attempt_history', JSON.stringify(filtered));
      loadHistoryLogs();
    } catch (err) {
      console.warn(err);
    }
  };

  const saveTeacherOverride = (logId: string) => {
    try {
      const logsStr = localStorage.getItem('mootion_attempt_history') || '[]';
      const parsed: AttemptLog[] = JSON.parse(logsStr);
      const updated = parsed.map(p => {
        if (p.id === logId) {
          const comment = teacherComments[logId];
          const newScore = scoreOverrides[logId];
          return {
            ...p,
            scores: {
              ...p.scores,
              ...(newScore !== undefined ? { understanding: newScore } : {})
            },
            ...(comment ? { feedback: `Teacher feedback: "${comment}"` } : {})
          };
        }
        return p;
      });
      localStorage.setItem('mootion_attempt_history', JSON.stringify(updated));
      loadHistoryLogs();
      alert("Teacher assessment saved successfully!");
    } catch (err) {
      console.error(err);
    }
  };

  if (history.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-[32px] p-6 md:p-8 border-2 border-[#1800ad]/10 shadow-sm mt-8 text-left animate-fade-in flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1800ad]/10 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-[#1800ad]/10 text-[#1800ad] rounded-full">
            <History size={20} />
          </div>
          <div className="flex flex-col">
            <h3 className="font-black text-xl text-[#1800ad] tracking-wide leading-none">Teach AI Practice Logs</h3>
            <p className="text-[#1800ad]/60 text-[11px] font-semibold mt-1">Verify conceptual progression and conversation audits</p>
          </div>
        </div>

        <div className="flex items-center bg-[#f6f4ee] p-1 rounded-full border border-[#1800ad]/10 self-start">
          <button 
            type="button"
            onClick={() => setIsTeacherMode(false)}
            className={`px-4 py-1.5 rounded-full text-[10px] font-black uppercase transition-all ${
              !isTeacherMode 
                ? 'bg-[#1800ad] text-white shadow-sm' 
                : 'text-[#1800ad]/60 hover:text-[#1800ad]'
            }`}
          >
            Student Panel
          </button>
          <button 
            type="button"
            onClick={() => setIsTeacherMode(true)}
            className={`px-4 py-1.5 rounded-full text-[10px] font-black uppercase transition-all flex items-center gap-1 ${
              isTeacherMode 
                ? 'bg-[#1800ad] text-white shadow-sm' 
                : 'text-[#1800ad]/60 hover:text-[#1800ad]'
            }`}
          >
            Teacher Audit Mode
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-4">
        {history.map((log) => {
          const isExpanded = expandedId === log.id;
          const uScore = scoreOverrides[log.id] !== undefined ? scoreOverrides[log.id] : log.scores.understanding;

          return (
            <div 
              key={log.id}
              onClick={() => toggleExpand(log.id)}
              className="border-2 border-[#1800ad]/5 rounded-[24px] overflow-hidden bg-[#f6f4ee]/20 hover:bg-[#f6f4ee]/40 cursor-pointer transition-all shadow-sm"
            >
              <div className="p-4 md:p-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div className="flex flex-col text-left justify-start">
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 bg-[#1800ad] text-white text-[9px] font-black uppercase tracking-wider rounded-full font-mono">
                      {log.activityName}
                    </span>
                    <span className="text-[10px] text-[#1800ad]/50 font-bold font-mono">
                      {new Date(log.timestamp).toLocaleString(undefined, { 
                        month: 'short', 
                        day: 'numeric', 
                        hour: '2-digit', 
                        minute: '2-digit' 
                      })}
                    </span>
                  </div>
                  <h4 className="font-bold text-[#1800ad] text-base mt-2 leading-tight">{log.topic}</h4>
                </div>

                <div className="flex items-center gap-4 self-stretch sm:self-center justify-between shrink-0">
                  <div className="flex gap-4 text-center">
                    <div className="flex flex-col">
                      <span className="text-[9px] font-extrabold text-[#1800ad]/50 uppercase tracking-widest font-mono">Understanding</span>
                      <span className="font-black text-sm text-[#1800ad]">{uScore}%</span>
                    </div>

                    <div className="flex flex-col border-l border-[#1800ad]/10 pl-4">
                      <span className="text-[9px] font-extrabold text-[#1800ad]/50 uppercase tracking-widest font-mono">
                        {log.activityName === 'Explain It' ? 'Expression' : 'Reasoning'}
                      </span>
                      <span className="font-black text-sm text-[#1800ad]">
                        {log.scores.expression || log.scores.reasoning || 80}%
                      </span>
                    </div>

                    {log.activityName === 'Predict It' && (
                      <div className="flex flex-col border-l border-[#1800ad]/10 pl-4">
                        <span className="text-[9px] font-extrabold text-[#1800ad]/50 uppercase tracking-widest font-mono">Prediction</span>
                        <span className={`text-[10px] font-black px-2.5 py-0.5 rounded-full font-mono ${
                          log.scores.accuracy === 'Correct' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                        }`}>
                          {log.scores.accuracy}
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-1 pl-4 border-l border-[#1800ad]/10">
                    <button 
                      type="button"
                      onClick={(e) => deleteAttemptLog(log.id, e)}
                      className="p-1 px-2 hover:bg-red-50 text-red-600 rounded-full transition-colors"
                      title="Delete attempt"
                    >
                      <Trash2 size={16} />
                    </button>
                    <ChevronRight size={18} className={`text-[#1800ad]/60 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                  </div>
                </div>
              </div>

              {isExpanded && (
                <div 
                  className="bg-white border-t-2 border-[#1800ad]/10 p-5 md:p-6 flex flex-col gap-5 text-left"
                  onClick={(e) => e.stopPropagation()} 
                >
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="flex flex-col gap-2">
                      <span className="font-black text-[10px] text-[#1800ad]/50 uppercase tracking-widest font-mono">Mastered Concepts</span>
                      <div className="flex flex-wrap gap-1.5">
                        {log.strengths.map((s, i) => (
                          <span key={i} className="bg-emerald-50 text-emerald-800 border border-emerald-100 px-3 py-1 font-bold text-xs rounded-full">
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="flex flex-col gap-2">
                      <span className="font-black text-[10px] text-[#1800ad]/50 uppercase tracking-widest font-mono">Attention / Learning Gaps</span>
                      <div className="flex flex-col gap-1">
                        {log.gaps.map((g, i) => (
                          <div key={i} className="bg-amber-50 text-amber-950 border border-amber-100 px-3 py-1.5 font-medium text-xs rounded-lg">
                            • {g}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {log.feedback && (
                    <div className="bg-[#f6f4ee]/70 border border-[#1800ad]/15 p-4 rounded-xl flex items-start gap-2.5">
                      <span className="text-base">💬</span>
                      <div className="flex flex-col">
                        <span className="text-[11px] font-black text-[#1800ad]/50 uppercase tracking-wider font-mono">Evaluation Audit Note</span>
                        <p className="text-xs text-[#1800ad]/80 italic mt-0.5 leading-relaxed font-semibold">
                          "{log.feedback}"
                        </p>
                      </div>
                    </div>
                  )}

                  <div className="flex flex-col gap-2">
                    <span className="font-black text-[10px] text-[#1800ad]/50 uppercase tracking-widest font-mono">
                       Conversation Transcript Transcript Records
                    </span>
                    <div className="bg-[#f6f4ee]/20 rounded-xl border border-[#1800ad]/10 max-h-48 overflow-y-auto p-4 flex flex-col gap-3 custom-scrollbar text-xs">
                      {log.transcript?.map((tr, idx) => (
                        <div key={idx} className={`flex flex-col ${tr.role === 'student' ? 'items-end' : 'items-start'}`}>
                          <div className={`p-3 rounded-xl max-w-[85%] font-medium leading-relaxed ${
                            tr.role === 'student' 
                              ? 'bg-[#1800ad] text-white rounded-tr-none font-bold' 
                              : 'bg-white text-[#1800ad] rounded-tl-none border border-[#1800ad]/10'
                          }`}>
                            <span className="font-extrabold text-[8.5px] uppercase tracking-wider block opacity-70 mb-0.5 font-mono">
                              {tr.role === 'student' ? 'Student' : 'Mootion'}
                            </span>
                            {tr.text}
                          </div>
                        </div>
                      )) || <p className="text-gray-400 italic">No transcript recorded.</p>}
                    </div>
                  </div>

                  {isTeacherMode && (
                    <div className="bg-amber-50/70 border border-amber-200 rounded-[20px] p-4 flex flex-col gap-3.5 mt-2">
                      <h5 className="font-black text-xs text-amber-800 uppercase tracking-widest flex items-center gap-1.5 font-mono">
                        <GraduationCap size={16} />
                        Assessor Intervention (Teacher Assessment Panel)
                      </h5>
                      <div className="flex flex-col md:flex-row gap-4 items-stretch md:items-end w-full">
                        <div className="flex-1 flex flex-col gap-1 text-left">
                          <label className="text-[10px] uppercase font-extrabold text-amber-700 font-mono">Override conceptual understanding score ({uScore}%)</label>
                          <input 
                            type="range" 
                            min="20" 
                            max="100" 
                            value={uScore}
                            onChange={(e) => setScoreOverrides(prev => ({ ...prev, [log.id]: parseInt(e.target.value, 10) }))}
                            className="w-full accent-amber-600"
                          />
                        </div>

                        <div className="flex-1 flex flex-col gap-1 text-left">
                          <label className="text-[10px] uppercase font-extrabold text-amber-700 font-mono">Write Custom Teacher Critique Comments</label>
                          <input 
                            type="text" 
                            placeholder="Add evaluation comments..." 
                            value={teacherComments[log.id] || ''}
                            onChange={(e) => setTeacherComments(prev => ({ ...prev, [log.id]: e.target.value }))}
                            className="bg-white border border-amber-300 rounded-lg px-3 py-1.5 text-xs outline-none focus:border-amber-500 font-bold text-[#1800ad]"
                          />
                        </div>

                        <button 
                          type="button"
                          onClick={() => saveTeacherOverride(log.id)}
                          className="px-5 py-2.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-black uppercase tracking-wider shadow transition-colors flex items-center gap-1 shrink-0 h-9 font-mono"
                        >
                          <Check size={14} className="stroke-[3]" />
                          Save Appraisal
                        </button>
                      </div>
                    </div>
                  )}

                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
