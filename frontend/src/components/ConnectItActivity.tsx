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

  // Memoize initialPairs based on task.id and stringified contents to prevent recreation on every render
  const initialPairs = useMemo<Pair[]>(() => {
    return contentJson.pairs || [];
  }, [task.id, JSON.stringify(contentJson.pairs)]);

  const [pairs, setPairs] = useState<Pair[]>([]);
  const [leftItems, setLeftItems] = useState<{ pairIndex: number; text: string }[]>([]);
  const [rightItems, setRightItems] = useState<{ pairIndex: number; text: string }[]>([]);
  
  // Interaction states
  const [selectedLeft, setSelectedLeft] = useState<number | null>(null);
  const [selectedRight, setSelectedRight] = useState<number | null>(null);
  const [matchedPairs, setMatchedPairs] = useState<Set<number>>(new Set());
  const [feedback, setFeedback] = useState<{ type: 'correct' | 'wrong'; message: string } | null>(null);
  const [allMatched, setAllMatched] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);

  // SVG Drawing states
  const containerRef = useRef<HTMLDivElement>(null);
  const [lineCoords, setLineCoords] = useState<{ [key: string]: { x: number; y: number } }>({});
  const [pointerPos, setPointerPos] = useState<{ x: number; y: number } | null>(null);
  const [wrongAttempt, setWrongAttempt] = useState<{ leftIdx: number; rightIdx: number } | null>(null);
  const [hoveredRightIdx, setHoveredRightIdx] = useState<number | null>(null);
  const hasDragged = useRef(false);

  // Timeout ID ref to defensively prevent race conditions and stale timeout triggers
  const feedbackTimeoutRef = useRef<any>(null);

  // Load from localStorage on mount or when task.id/initialPairs change
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
    // If no stored pairs, use initial pairs from backend
    if (initialPairs.length > 0) {
      setPairs(initialPairs);
    } else {
      // If no pairs at all, generate them
      generatePairs();
    }
  }, [task.id, initialPairs]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (feedbackTimeoutRef.current) {
        clearTimeout(feedbackTimeoutRef.current);
      }
    };
  }, []);

  // When pairs change, rebuild left and right items (once per load)
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

  // Check if all matched
  useEffect(() => {
    if (pairs.length > 0 && matchedPairs.size === pairs.length) {
      setAllMatched(true);
      // Save completion to localStorage
      localStorage.setItem(`connectit_complete_${task.id}`, 'true');
    }
  }, [matchedPairs, pairs.length, task.id]);

  // Helper to recalculate element center positions relative to the container
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

  // Recalculate coordinates when elements render or resize
  useEffect(() => {
    if (leftItems.length === 0) return;

    updateNodeCoordinates();
    const timer1 = setTimeout(updateNodeCoordinates, 100);
    const timer2 = setTimeout(updateNodeCoordinates, 500);

    window.addEventListener('resize', updateNodeCoordinates);
    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
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

      // Use the frontend server's chat endpoint (which proxies to Gemini)
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: prompt })
      });
      const responseData = await response.json();
      const raw = responseData.text || '';
      // Extract JSON from response (handling markdown etc.)
      let jsonStr = raw;
      const jsonMatch = raw.match(/\{[\s\S]*\}/);
      if (jsonMatch) jsonStr = jsonMatch[0];
      const data = JSON.parse(jsonStr);
      if (data.pairs && data.pairs.length > 0) {
        const generatedPairs = data.pairs.slice(0, 8);
        setPairs(generatedPairs);
        // Save to localStorage
        localStorage.setItem(`connectit_${task.id}`, JSON.stringify({ pairs: generatedPairs }));
      } else {
        setGenerationError('Failed to generate pairs. Please try again.');
      }
    } catch (err) {
      console.error('Error generating pairs:', err);
      setGenerationError('Could not generate pairs. Using fallback pairs.');
      // Fallback pairs (static)
      const fallbackPairs = [
        { left: 'Using placeholder content', right: 'Please try regenerating' },
        { left: 'API connection failed', right: 'Placeholder 1' },
        { left: 'Generation Error', right: 'Placeholder 2' },
        { left: 'Missing Topic', right: 'Placeholder 3' },
        { left: 'Concept 5', right: 'Description 5' },
        { left: 'Concept 6', right: 'Description 6' },
        { left: 'Concept 7', right: 'Description 7' },
        { left: 'Concept 8', right: 'Description 8' },
      ];
      setPairs(fallbackPairs);
    } finally {
      setIsGenerating(false);
    }
  };

  const attemptMatch = (leftIdx: number, rightIdx: number) => {
    // Clear any previous feedback timer before starting a new evaluation
    if (feedbackTimeoutRef.current) {
      clearTimeout(feedbackTimeoutRef.current);
      feedbackTimeoutRef.current = null;
    }

    const leftItem = leftItems[leftIdx];
    const rightItem = rightItems[rightIdx];
    const isMatch = leftItem.pairIndex === rightItem.pairIndex;

    if (isMatch) {
      setMatchedPairs(prev => {
        const next = new Set(prev);
        next.add(leftItem.pairIndex);
        return next;
      });
      setFeedback({ type: 'correct', message: '✅ Great match!' });
      setSelectedLeft(null);
      setSelectedRight(null);
      setPointerPos(null);
      setWrongAttempt(null);
      
      feedbackTimeoutRef.current = setTimeout(() => {
        setFeedback(null);
        feedbackTimeoutRef.current = null;
      }, 1500);
    } else {
      setFeedback({ type: 'wrong', message: '❌ Not a match. Try again!' });
      setWrongAttempt({ leftIdx, rightIdx });
      
      // Clear selection and pointer drag-line status synchronously so it detaches immediately
      setSelectedLeft(null);
      setSelectedRight(null);
      setPointerPos(null);
      
      feedbackTimeoutRef.current = setTimeout(() => {
        setFeedback(null);
        setWrongAttempt(null);
        feedbackTimeoutRef.current = null;
      }, 1500);
    }
  };

  // Helper to determine if a point lies over a right node card
  const getRightNodeIndexFromPoint = (clientX: number, clientY: number): number | null => {
    const el = document.elementFromPoint(clientX, clientY);
    if (!el) return null;
    const target = el.closest('[data-right-index]');
    if (!target) return null;
    const indexStr = target.getAttribute('data-right-index');
    return indexStr !== null ? parseInt(indexStr, 10) : null;
  };

  // Mouse / touch interaction handlers on left item cards
  const startConnection = (leftIdx: number, clientX: number, clientY: number) => {
    if (matchedPairs.has(leftItems[leftIdx].pairIndex)) return;
    
    // Defensively clear any pending timeouts and active feedback
    if (feedbackTimeoutRef.current) {
      clearTimeout(feedbackTimeoutRef.current);
      feedbackTimeoutRef.current = null;
    }
    setFeedback(null);
    setWrongAttempt(null);
    
    if (selectedLeft === leftIdx) {
      setSelectedLeft(null);
      setPointerPos(null);
      return;
    }
    
    setSelectedLeft(leftIdx);
    setSelectedRight(null);
    hasDragged.current = false;
    
    if (containerRef.current) {
      const containerRect = containerRef.current.getBoundingClientRect();
      setPointerPos({
        x: clientX - containerRect.left,
        y: clientY - containerRect.top,
      });
    }
  };

  const moveConnection = (clientX: number, clientY: number) => {
    if (selectedLeft === null || !containerRef.current) return;
    
    const containerRect = containerRef.current.getBoundingClientRect();
    setPointerPos({
      x: clientX - containerRect.left,
      y: clientY - containerRect.top,
    });
    
    if (!hasDragged.current) {
      hasDragged.current = true;
    }

    // Interactive Hover Drop Targeting
    const targetRightIdx = getRightNodeIndexFromPoint(clientX, clientY);
    if (targetRightIdx !== null && !matchedPairs.has(rightItems[targetRightIdx].pairIndex)) {
      setHoveredRightIdx(targetRightIdx);
    } else {
      setHoveredRightIdx(null);
    }
  };

  const endConnection = (clientX: number, clientY: number) => {
    setHoveredRightIdx(null); // Always clean up hover highlights immediately
    if (selectedLeft === null) return;
    
    const targetRightIdx = getRightNodeIndexFromPoint(clientX, clientY);
    
    if (targetRightIdx !== null && !matchedPairs.has(rightItems[targetRightIdx].pairIndex)) {
      attemptMatch(selectedLeft, targetRightIdx);
    } else {
      if (hasDragged.current) {
        setSelectedLeft(null);
        setPointerPos(null);
      } else {
        // Tapped elsewhere on screen?
        const el = document.elementFromPoint(clientX, clientY);
        const clickedLeft = el?.closest('[data-left-index]');
        if (!clickedLeft) {
          setSelectedLeft(null);
        }
        setPointerPos(null);
      }
    }
    hasDragged.current = false;
  };

  // Track window events when drawing/connecting is active
  useEffect(() => {
    if (selectedLeft === null) return;

    const handleMouseMove = (e: MouseEvent) => {
      moveConnection(e.clientX, e.clientY);
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length > 0) {
        moveConnection(e.touches[0].clientX, e.touches[0].clientY);
        // Block screen scroll behavior when connecting nodes
        if (e.cancelable) {
          e.preventDefault();
        }
      }
    };

    const handleMouseUp = (e: MouseEvent) => {
      endConnection(e.clientX, e.clientY);
    };

    const handleTouchEnd = (e: TouchEvent) => {
      if (e.changedTouches.length > 0) {
        endConnection(e.changedTouches[0].clientX, e.changedTouches[0].clientY);
      }
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
  }, [selectedLeft]);

  const handleLeftClick = (idx: number) => {
    // Handled natively by startConnection/onMouseDown/onTouchStart
  };

  const handleRightClick = (idx: number) => {
    if (matchedPairs.has(rightItems[idx].pairIndex)) return;
    
    // Clear any pending timeouts and active feedback
    if (feedbackTimeoutRef.current) {
      clearTimeout(feedbackTimeoutRef.current);
      feedbackTimeoutRef.current = null;
    }
    setFeedback(null);
    setWrongAttempt(null);

    if (selectedLeft !== null) {
      attemptMatch(selectedLeft, idx);
    }
  };

  if (isGenerating) {
    return (
      <div className="flex-1 w-full bg-[#f6f4ee] rounded-[32px] p-8 flex flex-col items-center justify-center border border-[#1800ad]/10">
        <div className="w-12 h-12 border-4 border-[#1800ad]/20 border-t-[#1800ad] rounded-full animate-spin mb-4"></div>
        <p className="text-xl font-bold text-[#1800ad]">Generating matching pairs...</p>
        <p className="text-sm text-[#1800ad]/70 mt-2">AI is creating a custom activity for you.</p>
      </div>
    );
  }

  if (generationError && pairs.length === 0) {
    return (
      <div className="flex-1 w-full bg-[#f6f4ee] rounded-[32px] p-8 flex flex-col items-center justify-center border border-[#1800ad]/10">
        <p className="text-xl font-bold text-rose-600">Error generating pairs</p>
        <p className="text-sm text-[#1800ad]/70 mt-2">{generationError}</p>
        <button
          onClick={generatePairs}
          className="mt-6 px-6 py-2 bg-[#1800ad] text-white rounded-full font-bold hover:bg-[#1800ad]/90 transition"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (pairs.length === 0) {
    return (
      <div className="flex-1 w-full bg-[#f6f4ee] rounded-[32px] p-8 flex flex-col items-center justify-center border border-[#1800ad]/10">
        <p className="text-xl font-bold text-[#1800ad]">No pairs available</p>
        <button
          onClick={generatePairs}
          className="mt-6 px-6 py-2 bg-[#1800ad] text-white rounded-full font-bold hover:bg-[#1800ad]/90 transition"
        >
          Generate Pairs
        </button>
      </div>
    );
  }

  return (
    <div className="flex-1 w-full bg-[#f6f4ee] rounded-[32px] p-6 md:p-8 flex flex-col items-center justify-start relative shadow-xl overflow-y-auto border border-[#1800ad]/10 min-h-[calc(100vh-80px)] md:min-h-0 md:h-full">
      <style>{`
        @keyframes card-shake {
          0%, 100% { transform: translateX(0); }
          20%, 60% { transform: translateX(-4px); }
          40%, 80% { transform: translateX(4px); }
        }
        .animate-shake {
          animation: card-shake 0.3s ease-in-out;
        }
      `}</style>

      <button
        onClick={onDone}
        className="absolute top-6 right-6 text-[#1800ad]/70 hover:text-[#1800ad] transition-colors z-35"
      >
        <X size={26} className="stroke-[2.5]" />
      </button>

      <div className="max-w-2xl w-full text-center mb-6 z-20">
        <h2 className="text-2xl md:text-3xl font-val text-[#1800ad] tracking-widest">Connect It</h2>
        <p className="text-[#1800ad]/70 text-sm mt-1">
          Drag a line from a left node to a right node, or tap a node on the left then a node on the right to connect them.
        </p>
        {allMatched && (
          <div className="mt-2 text-emerald-600 font-bold">🎉 All pairs matched! Great job!</div>
        )}
      </div>

      <div 
        ref={containerRef}
        className="relative grid grid-cols-2 gap-12 md:gap-20 w-full max-w-3xl bg-white rounded-3xl p-6 border border-[#1800ad]/10 shadow-lg z-0"
      >
        {/* SVG Drawing Layer */}
        <svg className="absolute inset-0 pointer-events-none w-full h-full z-10">
          {/* 1. Matched Lines */}
          {Array.from(matchedPairs).map((pairIndex) => {
            const leftIdx = leftItems.findIndex(item => item.pairIndex === pairIndex);
            const rightIdx = rightItems.findIndex(item => item.pairIndex === pairIndex);
            if (leftIdx === -1 || rightIdx === -1) return null;
            
            const start = lineCoords[`left-${leftIdx}`];
            const end = lineCoords[`right-${rightIdx}`];
            if (!start || !end) return null;

            return (
              <line
                key={`matched-${pairIndex}`}
                x1={start.x}
                y1={start.y}
                x2={end.x}
                y2={end.y}
                stroke="#10b981"
                strokeWidth="4"
                strokeLinecap="round"
              />
            );
          })}

          {/* 2. Wrong Attempt Line */}
          {wrongAttempt && (() => {
            const start = lineCoords[`left-${wrongAttempt.leftIdx}`];
            const end = lineCoords[`right-${wrongAttempt.rightIdx}`];
            if (!start || !end) return null;

            return (
              <line
                x1={start.x}
                y1={start.y}
                x2={end.x}
                y2={end.y}
                stroke="#f43f5e"
                strokeWidth="4"
                strokeLinecap="round"
                strokeDasharray="6,6"
                className="animate-pulse"
              />
            );
          })()}

          {/* 3. Current Dragging/Drawing Line */}
          {selectedLeft !== null && pointerPos !== null && (() => {
            const start = lineCoords[`left-${selectedLeft}`];
            if (!start) return null;

            return (
              <line
                x1={start.x}
                y1={start.y}
                x2={pointerPos.x}
                y2={pointerPos.y}
                stroke="#1800ad"
                strokeWidth="3"
                strokeLinecap="round"
                strokeDasharray="5,5"
              />
            );
          })()}
        </svg>

        {/* Left Column */}
        <div className="flex flex-col gap-3 relative z-20">
          <h3 className="text-[#1800ad]/60 text-xs font-bold uppercase tracking-wider text-center border-b border-[#1800ad]/10 pb-2 mb-1">
            Concepts
          </h3>
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
                  isMatched
                    ? 'border-emerald-500 bg-emerald-50 text-emerald-800 cursor-default line-through decoration-emerald-500/30'
                    : isSelected
                    ? 'border-[#1800ad] bg-[#1800ad]/5 text-[#1800ad] shadow-[0_0_0_2px_rgba(24,0,173,0.1)] scale-[1.02]'
                    : 'border-[#1800ad]/10 bg-white text-[#1800ad] hover:border-[#1800ad]/30 hover:bg-[#f6f4ee]'
                } ${
                  wrongAttempt !== null && wrongAttempt.leftIdx === idx ? 'animate-shake' : ''
                }`}
              >
                <span className="flex-1 pr-4">{item.text}</span>
                
                {/* Node Connection Handle */}
                <div
                  id={`left-node-${idx}`}
                  className={`w-3.5 h-3.5 rounded-full border-2 absolute right-[-7px] top-1/2 -translate-y-1/2 z-30 pointer-events-none transition-all duration-150 ${
                    isMatched
                      ? 'bg-emerald-500 border-emerald-500 scale-110 shadow-sm'
                      : isSelected
                      ? 'bg-[#1800ad] border-white scale-125 ring-2 ring-[#1800ad]/30'
                      : 'bg-white border-[#1800ad]/30 hover:border-[#1800ad] hover:scale-110'
                  }`}
                />
                
                {isMatched && <Check size={14} className="shrink-0 text-emerald-600 ml-1" />}
              </button>
            );
          })}
        </div>

        {/* Right Column */}
        <div className="flex flex-col gap-3 relative z-20">
          <h3 className="text-[#1800ad]/60 text-xs font-bold uppercase tracking-wider text-center border-b border-[#1800ad]/10 pb-2 mb-1">
            Descriptions
          </h3>
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
                  isMatched
                    ? 'border-emerald-500 bg-emerald-50 text-emerald-800 cursor-default line-through decoration-emerald-500/30'
                    : isSelected
                    ? 'border-[#1800ad] bg-[#1800ad]/5 text-[#1800ad] shadow-[0_0_0_2px_rgba(24,0,173,0.1)] scale-[1.02]'
                    : isHovered
                    ? 'border-[#1800ad] bg-[#1800ad]/5 text-[#1800ad] shadow-[0_0_12px_rgba(24,0,173,0.15)] scale-[1.04] z-30'
                    : 'border-[#1800ad]/10 bg-white text-[#1800ad] hover:border-[#1800ad]/30 hover:bg-[#f6f4ee]'
                } ${
                  wrongAttempt !== null && wrongAttempt.rightIdx === idx ? 'animate-shake' : ''
                }`}
              >
                {/* Node Connection Handle */}
                <div
                  id={`right-node-${idx}`}
                  className={`w-3.5 h-3.5 rounded-full border-2 absolute left-[-7px] top-1/2 -translate-y-1/2 z-30 pointer-events-none transition-all duration-150 ${
                    isMatched
                      ? 'bg-emerald-500 border-emerald-500 scale-110 shadow-sm'
                      : isSelected
                      ? 'bg-[#1800ad] border-white scale-125 ring-2 ring-[#1800ad]/30'
                      : 'bg-white border-[#1800ad]/30 hover:border-[#1800ad] hover:scale-110'
                  }`}
                />

                <span className="flex-1 pl-4 pr-1">{item.text}</span>
                
                {isMatched && <Check size={14} className="shrink-0 text-emerald-600 ml-1" />}
              </button>
            );
          })}
        </div>
      </div>

      {feedback && (
        <div
          className={`mt-6 px-4 py-2 rounded-full font-bold text-sm border ${
            feedback.type === 'correct' 
              ? 'bg-emerald-100 text-emerald-800 border-emerald-200' 
              : 'bg-rose-100 text-rose-800 border-rose-200'
          } animate-fade-in z-20`}
        >
          {feedback.message}
        </div>
      )}

      {allMatched && (
        <button
          onClick={() => {
            onDone();
            navigate('/student/home');
          }}
          className="mt-8 px-8 py-3 bg-[#1800ad] text-white rounded-full font-black text-sm hover:bg-[#1800ad]/90 transition shadow-lg z-20"
        >
          Finish & Continue
        </button>
      )}

      <div className="mt-4 text-[#1800ad]/40 text-xs font-mono z-20">
        {matchedPairs.size} / {pairs.length} matched
      </div>
    </div>
  );
}