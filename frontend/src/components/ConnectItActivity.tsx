import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Check, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Task } from '../data/tasks';
import { api } from '../lib/api';

interface Pair {
  left: string;
  right: string;
}

interface ConnectItActivityProps {
  task: Task;
  onDone: () => void;
}

export default function ConnectItActivity({ task, onDone }: ConnectItActivityProps) {
  const navigate = useNavigate();
  const dbTask = (task as any).dbTask;
  const contentJson = dbTask?.content_json || {};

  const initialPairs = useMemo<Pair[]>(() => {
    return contentJson.pairs || [];
  }, [task.id, JSON.stringify(contentJson.pairs)]);

  const [pairs, setPairs] = useState<Pair[]>([]);
  const [leftItems, setLeftItems] = useState<{ pairIndex: number; text: string }[]>([]);
  const [rightItems, setRightItems] = useState<{ pairIndex: number; text: string }[]>([]);

  const [selectedLeft, setSelectedLeft] = useState<number | null>(null);
  const [selectedRight, setSelectedRight] = useState<number | null>(null);
  const [matchedPairs, setMatchedPairs] = useState<Set<number>>(new Set());
  const [feedback, setFeedback] = useState<{ type: 'correct' | 'wrong'; message: string } | null>(null);
  const [allMatched, setAllMatched] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);

  // SVG Drawing states (desktop only)
  const containerRef = useRef<HTMLDivElement>(null);
  const [lineCoords, setLineCoords] = useState<{ [key: string]: { x: number; y: number } }>({});
  const [pointerPos, setPointerPos] = useState<{ x: number; y: number } | null>(null);
  const [wrongAttempt, setWrongAttempt] = useState<{ leftIdx: number; rightIdx: number } | null>(null);
  const [hoveredRightIdx, setHoveredRightIdx] = useState<number | null>(null);
  const hasDragged = useRef(false);
  const feedbackTimeoutRef = useRef<any>(null);

  useEffect(() => {
    const stored = localStorage.getItem(`connectit_${task.id}`);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (parsed.pairs && parsed.pairs.length > 0) {
          setPairs(parsed.pairs);
          return;
        }
      } catch (e) {}
    }
    if (initialPairs.length > 0) {
      setPairs(initialPairs);
    } else {
      generatePairs();
    }
  }, [task.id, initialPairs]);

  useEffect(() => {
    return () => {
      if (feedbackTimeoutRef.current) clearTimeout(feedbackTimeoutRef.current);
    };
  }, []);

  useEffect(() => {
    if (pairs.length === 0) return;
    const left = pairs.map((p, i) => ({ pairIndex: i, text: p.left }));
    const shuffled = [...pairs]
      .map((p, i) => ({ pairIndex: i, text: p.right }))
      .sort(() => Math.random() - 0.5);
    setLeftItems(left);
    setRightItems(shuffled);
    setMatchedPairs(new Set());
    setAllMatched(false);
    setSelectedLeft(null);
    setSelectedRight(null);
    setFeedback(null);
    setPointerPos(null);
    setWrongAttempt(null);
    setHoveredRightIdx(null);
    if (feedbackTimeoutRef.current) {
      clearTimeout(feedbackTimeoutRef.current);
      feedbackTimeoutRef.current = null;
    }
  }, [pairs]);

  useEffect(() => {
    if (pairs.length > 0 && matchedPairs.size === pairs.length) {
      setAllMatched(true);
      localStorage.setItem(`connectit_complete_${task.id}`, 'true');
    }
  }, [matchedPairs, pairs.length, task.id]);

  const updateNodeCoordinates = () => {
    if (!containerRef.current) return;
    const containerRect = containerRef.current.getBoundingClientRect();
    const coords: { [key: string]: { x: number; y: number } } = {};
    leftItems.forEach((_, idx) => {
      const el = document.getElementById(`left-node-${idx}`);
      if (el) {
        const rect = el.getBoundingClientRect();
        coords[`left-${idx}`] = {
          x: rect.left - containerRect.left + rect.width / 2,
          y: rect.top - containerRect.top + rect.height / 2,
        };
      }
    });
    rightItems.forEach((_, idx) => {
      const el = document.getElementById(`right-node-${idx}`);
      if (el) {
        const rect = el.getBoundingClientRect();
        coords[`right-${idx}`] = {
          x: rect.left - containerRect.left + rect.width / 2,
          y: rect.top - containerRect.top + rect.height / 2,
        };
      }
    });
    setLineCoords(coords);
  };

  useEffect(() => {
    if (leftItems.length === 0) return;
    updateNodeCoordinates();
    const t1 = setTimeout(updateNodeCoordinates, 100);
    const t2 = setTimeout(updateNodeCoordinates, 500);
    window.addEventListener('resize', updateNodeCoordinates);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      window.removeEventListener('resize', updateNodeCoordinates);
    };
  }, [leftItems, rightItems, matchedPairs]);

  const generatePairs = async () => {
    setIsGenerating(true);
    setGenerationError(null);
    try {
      const topic = task.topic || 'science concept';
      const subject = task.subject || 'Science';
      const prompt = `Generate 8 pairs of related items for a "Connect It" matching activity on the topic: "${topic}" in subject "${subject}". Each pair should consist of a left item and a right item that are meaningfully related (e.g., term-definition, cause-effect, scenario-concept, etc.). The pairs should be appropriate for school students (grades 6-12). Return ONLY a valid JSON object with a "pairs" key containing an array of 8 objects, each with "left" and "right" strings. Example format: {"pairs": [{"left": "Photosynthesis", "right": "Process of converting light energy to chemical energy"}, ...]}`;
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: prompt })
      });
      const responseData = await response.json();
      const raw = responseData.text || '';
      let jsonStr = raw;
      const jsonMatch = raw.match(/\{[\s\S]*\}/);
      if (jsonMatch) jsonStr = jsonMatch[0];
      const data = JSON.parse(jsonStr);
      if (data.pairs && data.pairs.length > 0) {
        const generatedPairs = data.pairs.slice(0, 8);
        setPairs(generatedPairs);
        localStorage.setItem(`connectit_${task.id}`, JSON.stringify({ pairs: generatedPairs }));
      } else {
        setGenerationError('Failed to generate pairs. Please try again.');
      }
    } catch (err) {
      console.error('Error generating pairs:', err);
      setGenerationError('Could not generate pairs. Using fallback pairs.');
      const fallbackPairs = [
        { left: 'Photosynthesis', right: 'Converting light to chemical energy' },
        { left: 'Mitosis', right: 'Cell division producing identical cells' },
        { left: 'Osmosis', right: 'Water moving across a semi-permeable membrane' },
        { left: 'Gravity', right: 'Force attracting objects with mass' },
        { left: 'Evaporation', right: 'Liquid turning to gas at surface' },
        { left: 'Convection', right: 'Heat transfer through fluid movement' },
        { left: 'Reflection', right: 'Light bouncing off a surface' },
        { left: 'Diffusion', right: 'Particles moving from high to low concentration' },
      ];
      setPairs(fallbackPairs);
    } finally {
      setIsGenerating(false);
    }
  };

  const clearFeedbackTimer = () => {
    if (feedbackTimeoutRef.current) {
      clearTimeout(feedbackTimeoutRef.current);
      feedbackTimeoutRef.current = null;
    }
  };

  const attemptMatch = (leftIdx: number, rightIdx: number) => {
    clearFeedbackTimer();
    const leftItem = leftItems[leftIdx];
    const rightItem = rightItems[rightIdx];
    const isMatch = leftItem.pairIndex === rightItem.pairIndex;
    if (isMatch) {
      setMatchedPairs(prev => { const next = new Set(prev); next.add(leftItem.pairIndex); return next; });
      setFeedback({ type: 'correct', message: '✅ Great match!' });
      setSelectedLeft(null);
      setSelectedRight(null);
      setPointerPos(null);
      setWrongAttempt(null);
      feedbackTimeoutRef.current = setTimeout(() => { setFeedback(null); feedbackTimeoutRef.current = null; }, 1500);
    } else {
      setFeedback({ type: 'wrong', message: '❌ Not a match. Try again!' });
      setWrongAttempt({ leftIdx, rightIdx });
      setSelectedLeft(null);
      setSelectedRight(null);
      setPointerPos(null);
      feedbackTimeoutRef.current = setTimeout(() => { setFeedback(null); setWrongAttempt(null); feedbackTimeoutRef.current = null; }, 1500);
    }
  };

  const getRightNodeIndexFromPoint = (clientX: number, clientY: number): number | null => {
    const el = document.elementFromPoint(clientX, clientY);
    if (!el) return null;
    const target = el.closest('[data-right-index]');
    if (!target) return null;
    const indexStr = target.getAttribute('data-right-index');
    return indexStr !== null ? parseInt(indexStr, 10) : null;
  };

  const startConnection = (leftIdx: number, clientX: number, clientY: number) => {
    if (matchedPairs.has(leftItems[leftIdx].pairIndex)) return;
    clearFeedbackTimer();
    setFeedback(null);
    setWrongAttempt(null);
    if (selectedLeft === leftIdx) { setSelectedLeft(null); setPointerPos(null); return; }
    setSelectedLeft(leftIdx);
    setSelectedRight(null);
    hasDragged.current = false;
    if (containerRef.current) {
      const containerRect = containerRef.current.getBoundingClientRect();
      setPointerPos({ x: clientX - containerRect.left, y: clientY - containerRect.top });
    }
  };

  const moveConnection = (clientX: number, clientY: number) => {
    if (selectedLeft === null || !containerRef.current) return;
    const containerRect = containerRef.current.getBoundingClientRect();
    setPointerPos({ x: clientX - containerRect.left, y: clientY - containerRect.top });
    if (!hasDragged.current) hasDragged.current = true;
    const targetRightIdx = getRightNodeIndexFromPoint(clientX, clientY);
    if (targetRightIdx !== null && !matchedPairs.has(rightItems[targetRightIdx].pairIndex)) {
      setHoveredRightIdx(targetRightIdx);
    } else {
      setHoveredRightIdx(null);
    }
  };

  const endConnection = (clientX: number, clientY: number) => {
    setHoveredRightIdx(null);
    if (selectedLeft === null) return;
    const targetRightIdx = getRightNodeIndexFromPoint(clientX, clientY);
    if (targetRightIdx !== null && !matchedPairs.has(rightItems[targetRightIdx].pairIndex)) {
      attemptMatch(selectedLeft, targetRightIdx);
    } else {
      if (hasDragged.current) {
        setSelectedLeft(null);
        setPointerPos(null);
      } else {
        const el = document.elementFromPoint(clientX, clientY);
        const clickedLeft = el?.closest('[data-left-index]');
        if (!clickedLeft) setSelectedLeft(null);
        setPointerPos(null);
      }
    }
    hasDragged.current = false;
  };

  useEffect(() => {
    // Only attach drag listeners when an actual drag/SVG-draw is in progress (pointerPos is set).
    // When selectedLeft is set via mobile tap, pointerPos stays null so this does nothing.
    if (selectedLeft === null || pointerPos === null) return;
    const handleMouseMove = (e: MouseEvent) => moveConnection(e.clientX, e.clientY);
    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length > 0) {
        moveConnection(e.touches[0].clientX, e.touches[0].clientY);
        if (e.cancelable) e.preventDefault();
      }
    };
    const handleMouseUp = (e: MouseEvent) => endConnection(e.clientX, e.clientY);
    const handleTouchEnd = (e: TouchEvent) => {
      if (e.changedTouches.length > 0) endConnection(e.changedTouches[0].clientX, e.changedTouches[0].clientY);
    };
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    window.addEventListener('touchmove', handleTouchMove, { passive: false });
    window.addEventListener('touchend', handleTouchEnd);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('touchmove', handleTouchMove);
      window.removeEventListener('touchend', handleTouchEnd);
    };
  }, [selectedLeft, pointerPos]);

  const handleRightClick = (idx: number) => {
    if (matchedPairs.has(rightItems[idx].pairIndex)) return;
    clearFeedbackTimer();
    setFeedback(null);
    setWrongAttempt(null);
    if (selectedLeft !== null) attemptMatch(selectedLeft, idx);
  };

  // Mobile-only: simple tap-to-select (no drag tracking)
  const handleMobileTap = (idx: number) => {
    if (matchedPairs.has(leftItems[idx].pairIndex)) return;
    clearFeedbackTimer();
    setFeedback(null);
    setWrongAttempt(null);
    // Toggle selection
    setSelectedLeft(prev => prev === idx ? null : idx);
  };

  // ─── Loading states ───────────────────────────────────────────────────────
  const loadingClass = "h-full w-full min-h-[60dvh] bg-[#f6f4ee] rounded-[32px] p-8 flex flex-col items-center justify-center border border-[#1800ad]/10";

  if (isGenerating) {
    return (
      <div className={loadingClass}>
        <div className="w-12 h-12 border-4 border-[#1800ad]/20 border-t-[#1800ad] rounded-full animate-spin mb-4" />
        <p className="text-xl font-bold text-[#1800ad] text-center">Designing Your Connect Challenge...</p>
        <p className="text-sm text-[#1800ad]/70 mt-2 text-center max-w-xs leading-relaxed">
          Our AI model is generating custom concepts and matching terms for your activity.
        </p>
      </div>
    );
  }

  if (generationError && pairs.length === 0) {
    return (
      <div className={loadingClass}>
        <p className="text-xl font-bold text-rose-600">Error generating pairs</p>
        <p className="text-sm text-[#1800ad]/70 mt-2">{generationError}</p>
        <button onClick={generatePairs} className="mt-6 px-6 py-2 bg-[#1800ad] text-white rounded-full font-bold hover:bg-[#1800ad]/90 transition">Try Again</button>
      </div>
    );
  }

  if (pairs.length === 0) {
    return (
      <div className={loadingClass}>
        <p className="text-xl font-bold text-[#1800ad]">No pairs available</p>
        <button onClick={generatePairs} className="mt-6 px-6 py-2 bg-[#1800ad] text-white rounded-full font-bold hover:bg-[#1800ad]/90 transition">Generate Pairs</button>
      </div>
    );
  }

  // ─── Shared styles ────────────────────────────────────────────────────────
  const shakeClass = (isWrong: boolean) => isWrong ? 'animate-shake' : '';

  return (
    <div className="h-full w-full min-h-[60dvh] bg-[#f6f4ee] rounded-[32px] flex flex-col overflow-hidden">
      <style>{`
        @keyframes card-shake {
          0%, 100% { transform: translateX(0); }
          20%, 60% { transform: translateX(-4px); }
          40%, 80% { transform: translateX(4px); }
        }
        .animate-shake { animation: card-shake 0.3s ease-in-out; }
      `}</style>

      {/* Header */}
      <div className="shrink-0 flex items-center justify-between px-5 pt-5 pb-3">
        <div>
          <h2 className="text-lg md:text-2xl font-val text-[#1800ad] tracking-widest">Connect It</h2>
          <p className="text-[#1800ad]/60 text-xs mt-0.5 hidden md:block">Drag a line from concept → description.</p>
          <p className="text-[#1800ad]/60 text-xs mt-0.5 md:hidden">Tap a concept, then tap its matching description.</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-[#1800ad]/40">{matchedPairs.size}/{pairs.length}</span>
          <button onClick={onDone} className="text-[#1800ad]/60 hover:text-[#1800ad] transition-colors">
            <X size={22} className="stroke-[2.5]" />
          </button>
        </div>
      </div>

      {/* Progress bar */}
      <div className="shrink-0 mx-5 mb-3 h-1.5 bg-[#1800ad]/10 rounded-full overflow-hidden">
        <div
          className="h-full bg-[#1800ad] rounded-full transition-all duration-500"
          style={{ width: `${pairs.length > 0 ? (matchedPairs.size / pairs.length) * 100 : 0}%` }}
        />
      </div>

      {/* Feedback banner */}
      {feedback && (
        <div className={`mx-5 mb-2 px-4 py-2 rounded-2xl font-bold text-sm text-center shrink-0 ${
          feedback.type === 'correct' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-rose-50 text-rose-800 border border-rose-200'
        }`}>
          {feedback.message}
        </div>
      )}

      {allMatched && (
        <div className="mx-5 mb-2 shrink-0">
          <div className="bg-emerald-50 border border-emerald-200 rounded-2xl px-4 py-3 text-center">
            <p className="text-emerald-800 font-bold text-sm">🎉 All pairs matched! Great job!</p>
            <button
              onClick={() => { onDone(); navigate('/student/home'); }}
              className="mt-2 px-6 py-2 bg-[#1800ad] text-white rounded-full font-black text-xs shadow-lg"
            >
              Finish &amp; Continue
            </button>
          </div>
        </div>
      )}

      {/* ─── MOBILE: Stacked tap-to-match layout ─── */}
      <div className="md:hidden flex-1 overflow-y-auto px-4 pb-28 flex flex-col gap-4">
        {/* Concepts */}
        <div className="flex flex-col gap-2">
          <h3 className="text-[10px] font-black text-[#1800ad]/40 uppercase tracking-widest ml-1">
            {selectedLeft !== null ? '👆 Now tap a description below' : 'Concepts — tap one to select'}
          </h3>
          {leftItems.map((item, idx) => {
            const isMatched = matchedPairs.has(item.pairIndex);
            const isSelected = selectedLeft === idx;
            return (
              <button
                key={idx}
                data-left-index={idx}
                onClick={() => handleMobileTap(idx)}
                disabled={isMatched}
                className={`w-full text-left p-3.5 rounded-2xl text-sm font-semibold border-2 transition-all flex items-center gap-3 select-none ${
                  isMatched
                    ? 'border-emerald-400 bg-emerald-50 text-emerald-800 cursor-default'
                    : isSelected
                    ? 'border-[#1800ad] bg-[#1800ad] text-white shadow-lg'
                    : 'border-[#1800ad]/15 bg-white text-[#1800ad] active:border-[#1800ad]/40'
                } ${shakeClass(wrongAttempt !== null && wrongAttempt.leftIdx === idx)}`}
              >
                <div className={`w-2.5 h-2.5 rounded-full shrink-0 border ${
                  isMatched ? 'bg-emerald-500 border-emerald-500' : isSelected ? 'bg-white border-white' : 'bg-transparent border-[#1800ad]/30'
                }`} />
                <span className="leading-snug flex-1">{item.text}</span>
                {isMatched && <Check size={14} className="shrink-0 text-emerald-600" />}
              </button>
            );
          })}
        </div>

        {/* Descriptions */}
        <div className="flex flex-col gap-2">
          <h3 className="text-[10px] font-black text-[#1800ad]/40 uppercase tracking-widest ml-1">Descriptions</h3>
          {rightItems.map((item, idx) => {
            const isMatched = matchedPairs.has(item.pairIndex);
            const isWrong = wrongAttempt !== null && wrongAttempt.rightIdx === idx;
            const canTap = selectedLeft !== null && !isMatched;
            return (
              <button
                key={idx}
                data-right-index={idx}
                onClick={() => handleRightClick(idx)}
                disabled={isMatched || selectedLeft === null}
                className={`w-full text-left p-3.5 rounded-2xl text-sm font-semibold border-2 transition-all flex items-center gap-3 ${
                  isMatched
                    ? 'border-emerald-400 bg-emerald-50 text-emerald-800 cursor-default'
                    : isWrong
                    ? 'border-rose-400 bg-rose-50 text-rose-800'
                    : canTap
                    ? 'border-[#1800ad]/30 bg-white text-[#1800ad] active:border-[#1800ad] active:bg-[#1800ad]/5'
                    : 'border-[#1800ad]/10 bg-white/60 text-[#1800ad]/40 cursor-default'
                } ${shakeClass(isWrong)}`}
              >
                <div className={`w-2.5 h-2.5 rounded-full shrink-0 border ${
                  isMatched ? 'bg-emerald-500 border-emerald-500' : canTap ? 'bg-transparent border-[#1800ad]/40' : 'bg-transparent border-[#1800ad]/10'
                }`} />
                <span className="leading-snug flex-1">{item.text}</span>
                {isMatched && <Check size={14} className="shrink-0 text-emerald-600" />}
              </button>
            );
          })}
        </div>
      </div>

      {/* ─── DESKTOP: 2-column SVG drag layout ─── */}
      <div
        ref={containerRef}
        className="hidden md:grid grid-cols-2 gap-16 lg:gap-20 flex-1 bg-white mx-5 mb-5 rounded-3xl p-6 border border-[#1800ad]/10 shadow-lg relative overflow-y-auto"
      >
        {/* SVG Layer */}
        <svg className="absolute inset-0 pointer-events-none w-full h-full z-10">
          {Array.from(matchedPairs).map((pairIndex) => {
            const leftIdx = leftItems.findIndex(i => i.pairIndex === pairIndex);
            const rightIdx = rightItems.findIndex(i => i.pairIndex === pairIndex);
            if (leftIdx === -1 || rightIdx === -1) return null;
            const start = lineCoords[`left-${leftIdx}`];
            const end = lineCoords[`right-${rightIdx}`];
            if (!start || !end) return null;
            return <line key={`m-${pairIndex}`} x1={start.x} y1={start.y} x2={end.x} y2={end.y} stroke="#10b981" strokeWidth="4" strokeLinecap="round" />;
          })}
          {wrongAttempt && (() => {
            const start = lineCoords[`left-${wrongAttempt.leftIdx}`];
            const end = lineCoords[`right-${wrongAttempt.rightIdx}`];
            if (!start || !end) return null;
            return <line x1={start.x} y1={start.y} x2={end.x} y2={end.y} stroke="#f43f5e" strokeWidth="4" strokeLinecap="round" strokeDasharray="6,6" className="animate-pulse" />;
          })()}
          {selectedLeft !== null && pointerPos !== null && (() => {
            const start = lineCoords[`left-${selectedLeft}`];
            if (!start) return null;
            return <line x1={start.x} y1={start.y} x2={pointerPos.x} y2={pointerPos.y} stroke="#1800ad" strokeWidth="3" strokeLinecap="round" strokeDasharray="5,5" />;
          })()}
        </svg>

        {/* Left column */}
        <div className="flex flex-col gap-3 relative z-20">
          <h3 className="text-[#1800ad]/60 text-xs font-bold uppercase tracking-wider text-center border-b border-[#1800ad]/10 pb-2 mb-1">Concepts</h3>
          {leftItems.map((item, idx) => {
            const isMatched = matchedPairs.has(item.pairIndex);
            const isSelected = selectedLeft === idx;
            return (
              <button
                key={idx}
                data-left-index={idx}
                onMouseDown={(e) => startConnection(idx, e.clientX, e.clientY)}
                onTouchStart={(e) => startConnection(idx, e.touches[0].clientX, e.touches[0].clientY)}
                disabled={isMatched}
                className={`p-4 rounded-2xl text-left text-sm font-semibold transition-all border-2 w-full relative flex items-center justify-between min-h-[72px] outline-none touch-none ${
                  isMatched ? 'border-emerald-500 bg-emerald-50 text-emerald-800 cursor-default line-through'
                  : isSelected ? 'border-[#1800ad] bg-[#1800ad]/5 text-[#1800ad] scale-[1.02]'
                  : 'border-[#1800ad]/10 bg-white text-[#1800ad] hover:border-[#1800ad]/30'
                } ${shakeClass(wrongAttempt !== null && wrongAttempt.leftIdx === idx)}`}
              >
                <span className="flex-1 pr-4">{item.text}</span>
                <div
                  id={`left-node-${idx}`}
                  className={`w-3.5 h-3.5 rounded-full border-2 absolute right-[-7px] top-1/2 -translate-y-1/2 z-30 pointer-events-none ${
                    isMatched ? 'bg-emerald-500 border-emerald-500' : isSelected ? 'bg-[#1800ad] border-white scale-125' : 'bg-white border-[#1800ad]/30'
                  }`}
                />
                {isMatched && <Check size={14} className="shrink-0 text-emerald-600 ml-1" />}
              </button>
            );
          })}
        </div>

        {/* Right column */}
        <div className="flex flex-col gap-3 relative z-20">
          <h3 className="text-[#1800ad]/60 text-xs font-bold uppercase tracking-wider text-center border-b border-[#1800ad]/10 pb-2 mb-1">Descriptions</h3>
          {rightItems.map((item, idx) => {
            const isMatched = matchedPairs.has(item.pairIndex);
            const isSelected = selectedRight === idx || (wrongAttempt !== null && wrongAttempt.rightIdx === idx);
            const isHovered = hoveredRightIdx === idx;
            return (
              <button
                key={idx}
                data-right-index={idx}
                onClick={() => handleRightClick(idx)}
                disabled={isMatched}
                className={`p-4 rounded-2xl text-left text-sm font-semibold transition-all border-2 w-full relative flex items-center justify-between min-h-[72px] outline-none ${
                  isMatched ? 'border-emerald-500 bg-emerald-50 text-emerald-800 cursor-default line-through'
                  : isSelected ? 'border-[#1800ad] bg-[#1800ad]/5 text-[#1800ad] scale-[1.02]'
                  : isHovered ? 'border-[#1800ad] bg-[#1800ad]/5 scale-[1.04] z-30'
                  : 'border-[#1800ad]/10 bg-white text-[#1800ad] hover:border-[#1800ad]/30'
                } ${shakeClass(wrongAttempt !== null && wrongAttempt.rightIdx === idx)}`}
              >
                <div
                  id={`right-node-${idx}`}
                  className={`w-3.5 h-3.5 rounded-full border-2 absolute left-[-7px] top-1/2 -translate-y-1/2 z-30 pointer-events-none ${
                    isMatched ? 'bg-emerald-500 border-emerald-500' : isSelected ? 'bg-[#1800ad] border-white scale-125' : 'bg-white border-[#1800ad]/30'
                  }`}
                />
                <span className="flex-1 pl-4 pr-1">{item.text}</span>
                {isMatched && <Check size={14} className="shrink-0 text-emerald-600 ml-1" />}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}