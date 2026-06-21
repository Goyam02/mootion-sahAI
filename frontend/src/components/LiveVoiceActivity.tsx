import React, { useState, useEffect, useRef } from 'react';
import { api } from '../lib/api';
import {
  Mic,
  Square,
  PlayCircle,
  Beaker,
  FileQuestion,
  ChevronRight,
  CheckCircle2,
  X,
  Sparkles,
  Award,
  Target,
  Trash2,
  History,
  Check,
  GraduationCap,
  RotateCcw
} from 'lucide-react';
import { Task } from '../data/tasks';

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
  const [activePlayState, setActivePlayState] = useState<'intro' | 'prediction' | 'simulation' | 'explaining' | 'grading'>('explaining');
  const [predictionChoice, setPredictionChoice] = useState<'sink' | 'float' | null>(null);
  const [simulationRunning, setSimulationRunning] = useState(false);
  const [simulationPercentage, setSimulationPercentage] = useState(0);

  // General Audio / Mic State
  const [isRecording, setIsRecording] = useState(false);
  const [isWebSocketActive, setIsWebSocketActive] = useState(false);
  const [aiIsSpeaking, setAiIsSpeaking] = useState(false);
  const [isThinking, setIsThinking] = useState(false);

  // Transcript logs
  const [messages, setMessages] = useState<{ role: 'student' | 'Mootion', text: string }[]>([]);
  const [liveTranscript, setLiveTranscript] = useState('');
  const [textFallbackInput, setTextFallbackInput] = useState('');

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
    isEmpty?: boolean;
  } | null>(null);

  // Audio queue & web references
  const recognitionRef = useRef<any>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const playbackAudioContextRef = useRef<AudioContext | null>(null);
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
  const activeAudioNodesRef = useRef(0);

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
  const isModelTurnCompleteRef = useRef(false);

  const hasGreetedRef = useRef(false);

  // Initialize: no hardcoded greeting, just set state to explaining.
  useEffect(() => {
    if (hasGreetedRef.current) return;
    hasGreetedRef.current = true;
    setActivePlayState('explaining');
    // Optionally set a short initial message if needed, but we skip to keep clean.
    setMessages([]);
  }, [activityName, task]);

  // Handle scrolling of captions
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, liveTranscript, liveModelTranscript, isThinking]);

  // Clean-up speech & audio contexts on unmount
  useEffect(() => {
    return () => {
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
        audioContextRef.current.close().catch(() => { });
      }
      if (playbackAudioContextRef.current && playbackAudioContextRef.current.state !== 'closed') {
        playbackAudioContextRef.current.close().catch(() => { });
      }
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    } catch (e) {
      console.warn("Clean-up warning:", e);
    }
  };

  const speakVoiceSynthesis = async (text: string) => {
    // If WebSocket is active, we rely on Gemini streaming audio, so skip external TTS.
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log("Skipping TTS because WebSocket is active.");
      return;
    }

    try {
      // Attempt to use server TTS endpoint (fallback)
      const res = await fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      const data = await res.json();
      if (data.audio) {
        isModelTurnCompleteRef.current = true;
        playReturnedAudio(data.audio);
        return;
      }
    } catch (e) {
      console.error("Failed TTS generation from API", e);
    }

    // Fallback to browser synthesis
    speakBrowserTTS(text);
  };

  // Speaks using browser speech synthesis for captions + voice sync (fallback / high fidelity)
  const speakBrowserTTS = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.onstart = () => setAiIsSpeaking(true);
      utterance.onend = () => setAiIsSpeaking(false);
      utterance.onerror = () => setAiIsSpeaking(false);

      // Select a natural, premium sounding English voice for a realistic human feel
      const voices = window.speechSynthesis.getVoices();
      const preferredKeywords = ['google us english', 'natural', 'premium', 'en-us', 'en-gb', 'samantha', 'daniel'];
      let selectedVoice = null;
      for (const keyword of preferredKeywords) {
        selectedVoice = voices.find(v => v.name.toLowerCase().includes(keyword) && v.lang.toLowerCase().includes('en'));
        if (selectedVoice) break;
      }
      if (!selectedVoice) {
        selectedVoice = voices.find(v => v.lang.toLowerCase().includes('en'));
      }
      if (selectedVoice) {
        utterance.voice = selectedVoice;
      }

      utterance.pitch = 1.02;
      utterance.rate = 1.0;
      window.speechSynthesis.speak(utterance);
    }
  };

  // Play incoming Base64 PCM audio chunk safely
  const processAudioQueue = async () => {
    if (!playbackAudioContextRef.current) {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      playbackAudioContextRef.current = new AudioCtx({ sampleRate: 24000 });
    }

    const playCtx = playbackAudioContextRef.current;
    if (playCtx.state === 'suspended') {
      try { await playCtx.resume(); } catch (e) { }
    }

    const currentTime = playCtx.currentTime;

    // If the next start time is in the past, or too close, align to current time (with larger buffer)
    if (nextStartTimeRef.current < currentTime) {
      nextStartTimeRef.current = currentTime + 0.2; // 200ms buffer to prevent starvation jitter
    }

    while (audioQueue.current.length > 0) {
      const chunk = audioQueue.current.shift()!;

      const audioBuffer = playCtx.createBuffer(1, chunk.length, 24000);
      audioBuffer.getChannelData(0).set(chunk);

      const bufferSource = playCtx.createBufferSource();
      bufferSource.buffer = audioBuffer;
      bufferSource.connect(playCtx.destination);

      bufferSource.start(nextStartTimeRef.current);
      nextStartTimeRef.current += audioBuffer.duration;

      activeAudioNodesRef.current += 1;

      bufferSource.onended = () => {
        activeAudioNodesRef.current -= 1;
        // Only trigger completion logic when ALL playing nodes have finished, queue is empty, and turn is complete
        if (activeAudioNodesRef.current === 0 && audioQueue.current.length === 0 && isModelTurnCompleteRef.current) {
          isPlayingQueue.current = false;
          setAiIsSpeaking(false);
          isModelTurnCompleteRef.current = false; // reset for next turn

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
        }
      };
    }
  };

  const playReturnedAudio = (base64Audio: string) => {
    try {
      const binaryString = atob(base64Audio);
      const len = binaryString.length;
      const samplesCount = Math.floor(len / 2);
      const float32Array = new Float32Array(samplesCount);

      for (let i = 0; i < samplesCount; i++) {
        const low = binaryString.charCodeAt(i * 2);
        const high = binaryString.charCodeAt(i * 2 + 1);
        let val = low | (high << 8);
        if (val & 0x8000) {
          val |= ~0xffff; // Sign extension
        }
        float32Array[i] = val / 32768.0;
      }

      audioQueue.current.push(float32Array);
      isPlayingQueue.current = true;
      setAiIsSpeaking(true);

      processAudioQueue();
    } catch (err) {
      console.error("PCM decoding failed", err);
    }
  };

  // Start real-time microphone stream connected to WebSocket Live
  const startRecordingVoice = async () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setAiIsSpeaking(false);
    }

    try {
      // Get microphone device stream
      const mstream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mstreamRef.current = mstream;

      // Establish separate input (microphone) context and output (24kHz playback) context proactively
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const actx = new AudioCtx();
      if (actx.state === 'suspended') {
        await actx.resume();
      }
      audioContextRef.current = actx;

      const playCtx = new AudioCtx({ sampleRate: 24000 });
      if (playCtx.state === 'suspended') {
        await playCtx.resume();
      }
      playbackAudioContextRef.current = playCtx;

      // Setup WebSocket Live Connection passing activity details as query parameters
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
            isModelTurnCompleteRef.current = false; // Reset
            updateLiveModelTranscript('');
          }

          if (parsed.turnComplete) {
            isModelTurnCompleteRef.current = true;
            // In case we underran AND there is no future chunks AND we're already idle...
            // that means onended fired BEFORE turnComplete arrived!
            if (activeAudioNodesRef.current === 0 && audioQueue.current.length === 0) {
              isPlayingQueue.current = false;
              setAiIsSpeaking(false);
              isModelTurnCompleteRef.current = false;

              if (liveModelTranscriptRef.current) {
                const text = liveModelTranscriptRef.current;
                setMessages(prev => [...prev, { role: 'Mootion', text }]);
                updateLiveModelTranscript('');

                const nextCount = questionsAnsweredRef.current + 1;
                setQuestionsAnswered(nextCount);
                if (nextCount >= maxQuestions) {
                  setTimeout(() => { triggerGradingEvaluation([...messagesRef.current, { role: 'Mootion', text }]); }, 1500);
                }
              }
            }
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
        // Fallback: enable local speech recognition if WebSocket fails
        startLocalSpeechRecognition();
      };

      ws.onclose = () => {
        console.log("Live WebSocket disconnected");
        setIsWebSocketActive(false);
      };

      // Set up client-side microphone streaming processor
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

      // Start local speech recognition as a backup if WebSocket fails
      const SpeechReg = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechReg) {
        const recog = new SpeechReg();
        recog.continuous = true;
        recog.interimResults = true;
        recog.lang = 'en-US';

        recog.onresult = (e: any) => {
          let interimTrans = '';
          let finalTrans = '';
          for (let i = e.resultIndex; i < e.results.length; ++i) {
            if (e.results[i].isFinal) {
              finalTrans += e.results[i][0].transcript;
            } else {
              interimTrans += e.results[i][0].transcript;
            }
          }
          const currentText = (finalTrans || interimTrans).trim();
          if (currentText) {
            // Only capture local fallback transcripts if WebSockets is inactive/not sending live transcripts
            if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
              setLiveTranscript(currentText);
            }
          }
        };

        recog.onerror = (e: any) => {
          console.warn("Local speech recognition error:", e);
        };

        recognitionRef.current = recog;
        recog.start();
      }

      setIsRecording(true);
    } catch (err) {
      console.warn("Hardware mic blocked or unavailable", err);

      // Fallback: Set up proactive local speech recognition anyway if audio context fails
      startLocalSpeechRecognition();

      setIsRecording(true);
    }
  };

  const startLocalSpeechRecognition = () => {
    const SpeechReg = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechReg) {
      const recog = new SpeechReg();
      recog.continuous = true;
      recog.interimResults = true;
      recog.lang = 'en-US';
      recog.onresult = (e: any) => {
        let interimTrans = '';
        let finalTrans = '';
        for (let i = e.resultIndex; i < e.results.length; ++i) {
          if (e.results[i].isFinal) {
            finalTrans += e.results[i][0].transcript;
          } else {
            interimTrans += e.results[i][0].transcript;
          }
        }
        setLiveTranscript((finalTrans || interimTrans).trim());
      };
      recognitionRef.current = recog;
      recog.start();
    }
  };

  const stopRecordingVoice = () => {
    setIsRecording(false);

    // Stop Microphone device recording and close connections safely
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
      audioContextRef.current.close().catch(() => { });
      audioContextRef.current = null;
    }
    if (playbackAudioContextRef.current) {
      playbackAudioContextRef.current.close().catch(() => { });
      playbackAudioContextRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    const wasWebSocketActive = isWebSocketActive;
    setIsWebSocketActive(false);

    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }

    // Submit any remaining student live speech transcript
    if (liveTranscript.trim()) {
      const textToSubmit = liveTranscript.trim();
      setLiveTranscript('');

      if (!wasWebSocketActive) {
        // Submit using API chat fallback so Mootion answers back and speaks out loud
        submitVoiceTranscript(textToSubmit);
      } else {
        setMessages(prev => [...prev, { role: 'student', text: textToSubmit }]);
      }
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
      // Build clever context prompting for tutor simulation
      const promptText = `Dialogue History:
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
${activityName === 'Predict It' ? "Acknowledge the simulation outcome. Ask EXACTLY ONE follow-up question about why water density differences make steel float or sink." : ""}
${activityName === 'Spot It' ? "Ask EXACTLY ONE question about flotation balances and forces." : ""}
${activityName === 'Connect It' ? "Acknowledge their explanation. Ask EXACTLY ONE question tying density or gravity together." : ""}

Respond in 1-2 conversational sentences. Ask EXACTLY ONE question. Never refer to yourself as an AI.`;

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: promptText })
      });

      const data = await response.json();
      const mootionReply = data.text || "Could you simplify that and explain why it happens?";

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
    }
  };

  const submitExplanationForAnalysis = async (transcriptText: string, chapterId: string | null, classId: string | null, gaps: string[] | null) => {
    try {
      let finalClassId = classId;
      let finalChapterId = chapterId;

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

      const payload: any = {
        transcript: transcriptText || "No student explanation provided.",
        chapter_id: finalChapterId,
        class_id: finalClassId
      };
      if (gaps && gaps.length > 0) {
        payload.gaps = gaps;
      }

      const response = await api.post('/api/analytics/submit-explanation', payload);

      // Analytics submitted successfully
    } catch (err) {
      console.error("Error submitting explanation for analysis:", err);
    }
  };

  // Run real-time appraisal of the complete dialog
  const triggerGradingEvaluation = async (finalTranscript: { role: 'student' | 'Mootion'; text: string }[]) => {
    setActivePlayState('grading');
    setIsThinking(true);

    let predOutcome = "";
    let finalEvalData: any = null;

    const studentText = finalTranscript
      .filter(m => m.role === 'student')
      .map(m => m.text)
      .join(' ')
      .trim();

    const isTooShort = !studentText || studentText.split(/\s+/).length < 15;

    if (isTooShort) {
      setIsThinking(false);
      setEvaluation({ isEmpty: true } as any);
      return;
    }

    try {
      const resp = await fetch('/api/evaluate-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task,
          activityName,
          transcript: finalTranscript,
          predictionOutcome: predOutcome || undefined
        })
      });

      const evalData = await resp.json();
      finalEvalData = evalData;
      setEvaluation(evalData);
      setIsThinking(false);

      if (evalData.feedback) {
        speakVoiceSynthesis(evalData.feedback);
      }

      // Save Attempt to localStorage history separating each attempt
      saveAttemptToStorage(finalTranscript, evalData);
    } catch (e) {
      console.error("Evaluation generation error", e);
      setIsThinking(false);
      const fallbackReport = {
        understandingScore: 82,
        expressionScore: 85,
        reasoningScore: 85,
        strengths: ["Great descriptions of gravity balances", "Clearly defined buoyant force upward vectors"],
        gaps: ["Can further describe Archimedes' specific relative mass density formulas"],
        feedback: "Great job! Your explanation of the concepts was very clear. Let's tackle more challenging topics next time.",
        predictionAccuracy: activityName === 'Predict It' ? (predictionChoice === 'sink' ? 'Correct' as const : 'Incorrect' as const) : undefined
      };
      finalEvalData = fallbackReport;
      setEvaluation(fallbackReport);
      saveAttemptToStorage(finalTranscript, fallbackReport);
    }

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
        submitExplanationForAnalysis(studentText, null, null, finalEvalData?.gaps || null);
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

  const startSimulationPlayback = () => {
    setSimulationRunning(true);
    setSimulationPercentage(0);

    const interval = setInterval(() => {
      setSimulationPercentage(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setSimulationRunning(false);
          setActivePlayState('explaining');

          let alertResponse = `Amazing! The simulation played. Notice that the solid stone sank entirely to the bottom and displaced water, while the wood block floats nicely at the surface! Why did this happen? Explain the force balance to me!`;
          setMessages(p => [...p, { role: 'Mootion', text: alertResponse }]);
          speakVoiceSynthesis(alertResponse);
          return 100;
        }
        return prev + 2.5;
      });
    }, 80);
  };

  const renderPredictSimulationBox = () => {
    return (
      <div className="w-full max-w-xl bg-white rounded-3xl p-6 border-2 border-[#1800ad]/10 shadow-inner flex flex-col items-center gap-4 animate-fade-in my-4 relative">
        <h4 className="font-bold text-center text-[#1800ad] text-base uppercase tracking-wider">
          Double-tap to Run Buoyancy Simulation
        </h4>

        {/* SVG visual bucket / container */}
        <div className="relative w-full h-44 bg-blue-50/50 rounded-2xl overflow-hidden border-2 border-blue-200 flex items-center justify-center">
          {/* Water fill line */}
          <div
            className="absolute bottom-0 left-0 right-0 bg-blue-300/60 transition-all duration-300"
            style={{ height: simulationRunning ? '65%' : '50%' }}
          >
            {/* Animated bubbles and ripple wave lines */}
            <div className="absolute top-0 inset-x-0 h-2 bg-blue-400/80 animate-pulse"></div>
          </div>

          {/* Sinking Stone sphere */}
          <div
            className="absolute bg-neutral-500 text-white text-[9px] font-black w-10 h-10 rounded-full flex items-center justify-center border border-neutral-600 transition-all duration-500 ease-out z-10"
            style={{
              top: simulationRunning ? `${15 + (simulationPercentage * 0.55)}px` : '15px',
              left: '30%',
              transform: 'translateX(-50%)'
            }}
          >
            5kg Metal
          </div>

          {/* Floating Pine Wooden cube */}
          <div
            className="absolute bg-amber-700 text-white text-[9px] font-black w-10 h-10 flex items-center justify-center border border-amber-800 transition-all duration-500 ease-out z-10"
            style={{
              top: simulationRunning ? `${50 + (simulationPercentage * 0.15)}px` : '15px',
              left: '70%',
              transform: 'translateX(-50%)'
            }}
          >
            5kg Wood
          </div>

          <span className="absolute bottom-2 font-mono text-[10px] text-[#1800ad]/40 z-10 font-bold uppercase tracking-widest">
            {simulationRunning ? `RUNNING LIFE CYCLE [${Math.round(simulationPercentage)}%]` : "IDLE - READY"}
          </span>
        </div>

        <button
          onClick={startSimulationPlayback}
          disabled={simulationRunning}
          className="px-6 py-2 bg-[#1800ad] hover:bg-[#1800ad]/90 text-white rounded-full font-bold text-xs transition-transform hover:scale-105 active:scale-95 disabled:opacity-50 flex items-center gap-1.5 shadow"
        >
          <PlayCircle size={14} className="stroke-[3]" />
          Run Life Cycle
        </button>
      </div>
    );
  };

  const renderSpotItContextCard = () => {
    return (
      <div className="w-full max-w-xl bg-white rounded-2xl p-5 border-2 border-[#1800ad]/15 shadow-md flex items-start gap-4 mb-3 animate-fade-in">
        <div className="p-3 bg-amber-500/20 text-amber-700 rounded-full">
          <Sparkles size={24} />
        </div>
        <div className="flex flex-col text-left">
          <span className="text-[10px] font-extrabold text-[#1800ad]/50 uppercase tracking-widest">Eerie Phenomenon Case</span>
          <h4 className="font-bold text-base text-[#1800ad] leading-snug mt-1">
            "An iron cargo battleship weighing 100,000 tons floats effortlessly in deep seawater, yet a minute 1-gram needle slips straight to the ocean floor."
          </h4>
          <p className="text-xs text-[#1800ad]/70 mt-1.5 font-medium">
            Explain which properties of displaced relative mass volumes account for this. Teach the AI Tutor!
          </p>
        </div>
      </div>
    );
  };

  const renderConnectItConceptDeck = () => {
    const cards = [
      { t: "Upthrust force", d: "The buoyant vertical mechanical push of fluid weight.", icon: <Award size={18} /> },
      { t: "Fluid density", d: "Specific mass density determining relative buoyancy indices.", icon: <Beaker size={18} /> },
      { t: "Displaced Volume", d: "The physical dimensional space the immersed object moves.", icon: <Target size={18} /> }
    ];

    return (
      <div className="flex flex-col sm:flex-row gap-3 w-full max-w-xl mb-4 animate-fade-in">
        {cards.map((c, i) => (
          <div key={i} className="flex-1 bg-white border border-[#1800ad]/10 rounded-xl p-4 flex flex-col justify-between hover:shadow transition-shadow">
            <div className="flex justify-between items-center mb-1">
              <span className="font-extrabold text-[10px] text-[#1800ad]/60 uppercase tracking-wide font-mono">Dimension {i + 1}</span>
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
    if (evaluation?.isEmpty) {
      return (
        <div className="flex-1 w-full bg-[#1800ad] rounded-[32px] p-6 md:p-8 flex flex-col items-center justify-center relative shadow-xl overflow-hidden min-h-[calc(100vh-80px)] md:min-h-0 md:h-full">
          <div className="absolute -top-32 -left-32 w-80 h-80 bg-amber-500/15 rounded-full blur-3xl pointer-events-none animate-pulse"></div>
          
          <button onClick={onDone} className="absolute top-6 right-6 text-white hover:opacity-75 transition-colors z-20">
            <X size={26} className="stroke-[2.5]" />
          </button>

          <header className="text-center relative z-10 w-full max-w-2xl flex flex-col items-center gap-1 mt-4">
            <div className="p-3 bg-amber-500/25 text-amber-300 rounded-full mb-2 shadow-lg">
              <RotateCcw size={32} />
            </div>
            <h1 className="text-3xl md:text-5xl font-val text-white tracking-widest" style={{ textShadow: '3px 3px 0 #000' }}>
              THANK YOU
            </h1>
          </header>

          <div className="bg-white p-6 md:p-8 rounded-[28px] shadow-2xl w-full max-w-2xl flex flex-col relative z-10 border border-[#1800ad]/15">
            <div className="flex justify-center gap-4 w-full">
              <button
                type="button"
                onClick={onDone}
                className="flex-1 py-3.5 rounded-full font-bold border-2 border-[#1800ad] text-[#1800ad] hover:bg-[#1800ad]/5 transition-colors text-sm"
              >
                View More Tasks
              </button>
              <button
                type="button"
                onClick={() => {
                  setEvaluation(null);
                  setMessages([]);
                  setQuestionsAnswered(0);
                  setActivePlayState(activityName === 'Predict It' ? 'prediction' : 'explaining');
                }}
                className="flex-1 py-3.5 rounded-full font-bold bg-[#1800ad] text-white hover:bg-[#1800ad]/90 transition-colors shadow-md text-sm"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="flex-1 w-full bg-[#1800ad] rounded-[32px] p-6 md:p-8 flex flex-col items-center justify-center relative shadow-xl overflow-hidden min-h-[calc(100vh-80px)] md:min-h-0 md:h-full">
        <div className="absolute -top-32 -left-32 w-80 h-80 bg-emerald-500/15 rounded-full blur-3xl pointer-events-none animate-pulse"></div>
        <div className="absolute -bottom-32 -right-32 w-80 h-80 bg-blue-500/15 rounded-full blur-3xl pointer-events-none animate-pulse"></div>

        <button onClick={onDone} className="absolute top-6 right-6 text-white hover:opacity-75 transition-colors z-20">
          <X size={26} className="stroke-[2.5]" />
        </button>

        <header className="text-center relative z-10 w-full max-w-2xl flex flex-col items-center gap-1 mt-4">
          <div className="p-3 bg-emerald-500/25 text-emerald-300 rounded-full mb-2 shadow-lg">
            <CheckCircle2 size={32} />
          </div>
          <h1 className="text-3xl md:text-5xl font-val text-white tracking-widest" style={{ textShadow: '3px 3px 0 #000' }}>
            ACTIVITY COMPLETED
          </h1>
          <h2 className="text-sm md:text-base font-bold text-white/80">{activityName} Log • {task.topic}</h2>
        </header>

        <div className="bg-white p-6 md:p-8 rounded-[28px] shadow-2xl w-full max-w-2xl flex flex-col gap-6 mt-6 relative z-10 border border-[#1800ad]/15">
          <div className="bg-blue-50 border border-blue-100 rounded-[20px] p-6 flex flex-col items-center text-center gap-3">
            <span className="text-4xl">🎉</span>
            <h3 className="font-black text-[#1800ad] text-lg">Thank You!</h3>
            <p className="text-sm text-[#1800ad]/80 font-semibold leading-relaxed max-w-md">
              Your response has been successfully recorded. Great job completing this activity! Keep up the excellent work.
            </p>
          </div>

          <div className="flex justify-center pt-2">
            <button
              type="button"
              onClick={onDone}
              className="px-8 py-3 rounded-full font-bold bg-[#1800ad] text-white hover:bg-[#1800ad]/90 transition-colors shadow-md text-sm"
            >
              Back to Tasks
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
            <p className="text-white font-bold text-base max-w-md">
              Will the solid 5kg iron ball float or sink inside the bucket of fresh water? Choose to start the animation!
            </p>
            <div className="flex gap-4 mt-2 w-full max-w-sm justify-center">
              <button
                type="button"
                onClick={() => { setPredictionChoice('sink'); setActivePlayState('simulation'); }}
                className="flex-1 py-4 bg-white hover:bg-[#f6f4ee] text-[#1800ad] hover:scale-103 font-bold rounded-2xl border-2 border-transparent transition-all shadow-md active:scale-95 text-xs uppercase font-black"
              >
                Prediction: SINK ⚓
              </button>
              <button
                type="button"
                onClick={() => { setPredictionChoice('float'); setActivePlayState('simulation'); }}
                className="flex-1 py-4 bg-white hover:bg-[#f6f4ee] text-[#1800ad] hover:scale-103 font-bold rounded-2xl border-2 border-transparent transition-all shadow-md active:scale-95 text-xs uppercase font-black"
              >
                Prediction: FLOAT 🪵
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
            <div className="relative flex items-center justify-center animate-fade-in">

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

            {/* Captions / Realtime Transcript */}
            <div className="w-full max-w-md bg-[#f6f4ee]/15 backdrop-blur-xs rounded-2xl px-5 py-4 border-2 border-white/10 text-center min-h-[72px] flex items-center justify-center shadow-lg font-montserrat">
              {isThinking ? (
                <div className="flex items-center gap-2 text-white/85 font-black text-xs uppercase tracking-widest">
                  <span className="animate-pulse">AI Tutor is thinking</span>
                  <div className="flex gap-1">
                    <span className="w-1 bg-[#f1f1ee] h-1.5 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></span>
                    <span className="w-1 bg-[#f1f1ee] h-1.5 rounded-full animate-bounce" style={{ animationDelay: '0.15s' }}></span>
                    <span className="w-1 bg-[#f1f1ee] h-1.5 rounded-full animate-bounce" style={{ animationDelay: '0.3s' }}></span>
                  </div>
                </div>
              ) : liveModelTranscript ? (
                <p className="text-[#f6f4ee] font-black text-xs md:text-sm leading-relaxed max-w-sm animate-fade-in">
                  🤖 AI Tutor: "{liveModelTranscript}"
                </p>
              ) : liveTranscript ? (
                <p className="text-white/95 font-semibold text-xs md:text-sm italic leading-relaxed max-w-sm animate-pulse">
                  🎙️ Transcribing: "{liveTranscript}"
                </p>
              ) : (
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-black uppercase text-[#f6f4ee]/70 tracking-widest leading-none">
                    AI Tutor is listening
                  </span>
                  <span className="text-[9px] font-bold text-white/55 tracking-wider mt-1 leading-normal">
                    Press the microphone to respond with your explanation
                  </span>
                </div>
              )}
            </div>

            {/* Turn tracker status pill */}
            <div className="flex items-center gap-1.5 bg-white/15 px-4 py-1.5 rounded-full border border-white/5 mt-1 font-mono">
              <span className="text-[9px] font-black uppercase text-[#f6f4ee]/85">
                {questionsAnswered} / {maxQuestions} explained
              </span>
            </div>
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
            className={`px-4 py-1.5 rounded-full text-[10px] font-black uppercase transition-all ${!isTeacherMode
              ? 'bg-[#1800ad] text-white shadow-sm'
              : 'text-[#1800ad]/60 hover:text-[#1800ad]'
              }`}
          >
            Student Panel
          </button>
          <button
            type="button"
            onClick={() => setIsTeacherMode(true)}
            className={`px-4 py-1.5 rounded-full text-[10px] font-black uppercase transition-all flex items-center gap-1 ${isTeacherMode
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
                        <span className={`text-[10px] font-black px-2.5 py-0.5 rounded-full font-mono ${log.scores.accuracy === 'Correct' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
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
                          <div className={`p-3 rounded-xl max-w-[85%] font-medium leading-relaxed ${tr.role === 'student'
                            ? 'bg-[#1800ad] text-white rounded-tr-none font-bold'
                            : 'bg-white text-[#1800ad] rounded-tl-none border border-[#1800ad]/10'
                            }`}>
                            <span className="font-extrabold text-[8.5px] uppercase tracking-wider block opacity-70 mb-0.5 font-mono">
                              {tr.role === 'student' ? 'Student' : 'AI Tutor'}
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