import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Sparkles, Send, RefreshCw, Atom, FlaskConical,
  Dna, Sigma, CheckCircle2, AlertCircle, Lightbulb,
  BookOpen, Sliders, BarChart3,
} from 'lucide-react';
import { MootionSimulationPlayer } from '../../components/MootionSimulationPlayer';
import { api, API_BASE } from '../../api';

interface SimResult {
  simulation_id: string;
  status: string;
  html: string;
  spec: Record<string, any> | null;
  validation: Record<string, any> | null;
  quality_score: number;
  assessments: { id: string; type: string; question: string; hint: string; difficulty: string }[];
  error: string | null;
  duration_ms: number;
}

interface SubjectInfo {
  id: string;
  name: string;
  topics: string[];
  icon: string;
}

const SUBJECT_ICONS: Record<string, React.ReactNode> = {
  physics: <Atom size={18} className="text-cyan-400" />,
  chemistry: <FlaskConical size={18} className="text-green-400" />,
  biology: <Dna size={18} className="text-rose-400" />,
  mathematics: <Sigma size={18} className="text-violet-400" />,
};

const SUBJECT_COLORS: Record<string, string> = {
  physics: 'border-cyan-500/30 bg-cyan-500/5',
  chemistry: 'border-green-500/30 bg-green-500/5',
  biology: 'border-rose-500/30 bg-rose-500/5',
  mathematics: 'border-violet-500/30 bg-violet-500/5',
};

const SUBJECT_ACCENT: Record<string, string> = {
  physics: 'text-cyan-400',
  chemistry: 'text-green-400',
  biology: 'text-rose-400',
  mathematics: 'text-violet-400',
};

export const SimulationGenerator: React.FC = () => {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState('');
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<SimResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [subjects, setSubjects] = useState<SubjectInfo[]>([]);
  const [examplePrompts, setExamplePrompts] = useState<string[]>([]);
  const [currentSubject, setCurrentSubject] = useState<string | null>(null);
  const [activeAssessment, setActiveAssessment] = useState(0);
  const [showSpec, setShowSpec] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/simulations/supported-subjects`)
      .then(r => r.json())
      .then(setSubjects)
      .catch(() => {});
    fetch(`${API_BASE}/simulations/example-prompts`)
      .then(r => r.json())
      .then(d => setExamplePrompts(d.prompts || []))
      .catch(() => {});
  }, []);

  const handleDownload = useCallback(() => {
    if (!result?.html) return;
    const blob = new Blob([result.html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = (result.spec?.title || 'simulation').replace(/[^a-z0-9]/gi, '_') + '.html';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [result]);

  const handleGenerate = useCallback(async () => {
    if (!prompt.trim()) return;
    setGenerating(true);
    setError(null);
    setResult(null);
    setActiveAssessment(0);

    try {
      const token = localStorage.getItem('mootion_token');
      const res = await fetch(`${API_BASE}/simulations/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ prompt: prompt.trim() }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Generation failed');
      }

      const data: SimResult = await res.json();
      setResult(data);

      if (data.spec?.subject) {
        setCurrentSubject(data.spec.subject);
      }

      if (data.error) {
        setError(data.error);
      }
    } catch (e: any) {
      setError(e.message || 'Failed to generate simulation');
    } finally {
      setGenerating(false);
    }
  }, [prompt]);

  const handleExampleClick = (ex: string) => {
    setPrompt(ex);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleGenerate();
    }
  };

  const getSubjectClass = (subjectId: string | null) => {
    if (!subjectId) return 'border-violet-500/30 bg-violet-500/5';
    return SUBJECT_COLORS[subjectId] || 'border-slate-700 bg-slate-800/30';
  };

  const getSubjectAccent = (subjectId: string | null) => {
    if (!subjectId) return 'text-violet-400';
    return SUBJECT_ACCENT[subjectId] || 'text-slate-300';
  };

  return (
    <div className="flex-1 flex flex-col bg-[#07070c] relative z-10 min-h-screen">
      <div className="grid-overlay" />
      <div className="ambient-light" />

      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-900">
        <button
          onClick={() => navigate('/student/home')}
          className="text-slate-400 hover:text-white text-xs font-semibold inline-flex items-center gap-1.5 transition-colors"
        >
          <ArrowLeft size={14} />
          <span>Back</span>
        </button>
        <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase bg-slate-950 px-3 py-1.5 border border-slate-800 rounded-full">
          <Sparkles size={13} className="text-violet-400" />
          <span>AI Simulation Generator</span>
        </div>
      </div>

      <div className="flex-1 flex flex-col max-w-6xl w-full mx-auto p-4 md:p-6 gap-6">
        {/* Input Section */}
        <div className="glass-panel p-5 flex flex-col gap-4">
          <h3 className="font-bold text-slate-200 text-sm font-heading flex items-center gap-1.5">
            <Lightbulb size={16} className="text-amber-400" />
            What STEM concept do you want to explore?
          </h3>

          <div className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              placeholder="e.g. Explain projectile motion, Show membrane transport, Teach me electric fields..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={generating}
              className="form-input flex-1 bg-slate-900 text-xs font-semibold"
            />
            <button
              onClick={handleGenerate}
              disabled={generating || !prompt.trim()}
              className="btn-primary py-2.5 px-6 text-xs font-bold flex items-center gap-1.5"
            >
              {generating ? (
                <RefreshCw size={14} className="animate-spin" />
              ) : (
                <Send size={13} />
              )}
              <span>{generating ? 'Generating...' : 'Generate'}</span>
            </button>
          </div>

          {/* Example prompts */}
          {examplePrompts.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2">
              <span className="text-[10px] text-slate-500 font-semibold pt-1">Try:</span>
              {examplePrompts.slice(0, 5).map((ex, i) => (
                <button
                  key={i}
                  onClick={() => handleExampleClick(ex)}
                  className="text-[10px] font-semibold text-slate-400 hover:text-white bg-slate-950 hover:bg-slate-800 border border-slate-800 px-2.5 py-1 rounded-full transition-colors"
                >
                  {ex}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Subject indicator */}
        {currentSubject && result && (
          <div className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${getSubjectClass(currentSubject)}`}>
            {SUBJECT_ICONS[currentSubject]}
            <span className={`text-xs font-bold uppercase tracking-wider ${getSubjectAccent(currentSubject)}`}>
              {subjects.find(s => s.id === currentSubject)?.name || currentSubject}
            </span>
            <span className="text-[10px] text-slate-500 ml-auto">
              Generated in {(result.duration_ms / 1000).toFixed(1)}s
            </span>
          </div>
        )}

        {/* Error display */}
        {error && (
          <div className="flex items-start gap-3 p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl">
            <AlertCircle size={18} className="text-rose-400 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="text-xs font-bold text-rose-300">Generation Error</h4>
              <p className="text-xs text-slate-400 mt-1">{error}</p>
            </div>
          </div>
        )}

        {/* Generating state */}
        {generating && (
          <div className="glass-panel p-12 flex flex-col items-center justify-center gap-4 animate-pulse border-violet-500/20">
            <span className="w-10 h-10 border-4 border-violet-500/20 border-t-violet-500 rounded-full animate-spin" />
            <div className="text-center">
              <h4 className="font-bold text-slate-300 text-xs uppercase tracking-wider">
                AI Synthesizing Simulation
              </h4>
              <p className="text-[10px] text-slate-500 mt-1">
                Understanding prompt &rarr; Planning &rarr; Building &rarr; Validating &rarr; Assessing
              </p>
            </div>
          </div>
        )}

        {/* Results */}
        {result && !generating && (
          <div className="flex flex-col gap-4 animate-fade-in">
            {/* Simulation Player */}
            {result.html && result.status === 'completed' && (
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold text-violet-400 uppercase tracking-widest bg-violet-500/10 px-2.5 py-1 rounded-full border border-violet-500/20 flex items-center gap-1.5">
                    <CheckCircle2 size={12} />
                    Simulation Generated
                  </span>
                  <div className="flex items-center gap-2">
                    {result.quality_score > 0 && (
                      <span className="text-[10px] text-slate-500 font-mono">
                        Quality: {(result.quality_score * 100).toFixed(0)}%
                      </span>
                    )}
                    <button
                      onClick={handleDownload}
                      className="text-[10px] text-emerald-400 hover:text-white bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-1 rounded-lg transition-colors"
                    >
                      Download HTML
                    </button>
                    <button
                      onClick={() => setShowSpec(!showSpec)}
                      className="text-[10px] text-slate-400 hover:text-white bg-slate-900 border border-slate-800 px-2.5 py-1 rounded-lg transition-colors"
                    >
                      {showSpec ? 'Hide Details' : 'Show Details'}
                    </button>
                  </div>
                </div>

                <MootionSimulationPlayer
                  html={result.html}
                  title={result.spec?.title || 'Mootion Simulation'}
                />
              </div>
            )}

            {/* Specification details */}
            {showSpec && result.spec && (
              <div className="glass-panel p-4 flex flex-col gap-3 text-xs">
                <h4 className="font-bold text-slate-300 uppercase tracking-wider text-[10px]">
                  Simulation Specification
                </h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="bg-slate-950 rounded-lg p-3 border border-slate-800">
                    <span className="text-[9px] text-slate-500 uppercase block">Topic</span>
                    <span className="text-slate-200 font-semibold">{result.spec.topic}</span>
                  </div>
                  <div className="bg-slate-950 rounded-lg p-3 border border-slate-800">
                    <span className="text-[9px] text-slate-500 uppercase block">Type</span>
                    <span className="text-slate-200 font-semibold">{result.spec.simulation_type}</span>
                  </div>
                  <div className="bg-slate-950 rounded-lg p-3 border border-slate-800">
                    <span className="text-[9px] text-slate-500 uppercase block">Grade</span>
                    <span className="text-slate-200 font-semibold">{result.spec.grade_level}</span>
                  </div>
                  <div className="bg-slate-950 rounded-lg p-3 border border-slate-800">
                    <span className="text-[9px] text-slate-500 uppercase block">Params</span>
                    <span className="text-slate-200 font-semibold">
                      {result.spec.parameters?.length || 0} controls
                    </span>
                  </div>
                </div>

                {result.spec.learning_objectives && (
                  <div className="bg-slate-950 rounded-lg p-3 border border-slate-800">
                    <span className="text-[9px] text-slate-500 uppercase block mb-1">Learning Objectives</span>
                    <ul className="list-disc list-inside text-slate-300 space-y-0.5">
                      {result.spec.learning_objectives.map((obj: string, i: number) => (
                        <li key={i}>{obj}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {result.spec.equations && result.spec.equations.length > 0 && (
                  <div className="bg-slate-950 rounded-lg p-3 border border-slate-800">
                    <span className="text-[9px] text-slate-500 uppercase block mb-1">Equations</span>
                    {result.spec.equations.map((eq: any, i: number) => (
                      <div key={i} className="text-slate-300 font-mono text-[11px] mb-1">
                        {eq.latex} - {eq.description}
                      </div>
                    ))}
                  </div>
                )}

                {result.validation && (
                  <div className="bg-slate-950 rounded-lg p-3 border border-slate-800">
                    <span className="text-[9px] text-slate-500 uppercase block mb-1">Validation</span>
                    <div className="flex items-center gap-2">
                      <span className={`text-[11px] font-bold ${result.validation.passed ? 'text-green-400' : 'text-rose-400'}`}>
                        {result.validation.passed ? 'PASSED' : 'FAILED'}
                      </span>
                      <span className="text-[11px] text-slate-400">
                        Score: {(result.validation.score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Assessment Prompts */}
            {result.assessments && result.assessments.length > 0 && (
              <div className="glass-panel p-4 flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-slate-300 uppercase tracking-wider text-[10px] flex items-center gap-1.5">
                    <BookOpen size={13} className="text-amber-400" />
                    Assessment Prompts
                  </h4>
                  <div className="flex gap-1">
                    {result.assessments.map((_, i) => (
                      <button
                        key={i}
                        onClick={() => setActiveAssessment(i)}
                        className={`w-2 h-2 rounded-full transition-all ${
                          i === activeAssessment ? 'bg-amber-400 w-4' : 'bg-slate-700 hover:bg-slate-600'
                        }`}
                      />
                    ))}
                  </div>
                </div>

                {result.assessments[activeAssessment] && (
                  <div className="bg-slate-950 rounded-xl p-4 border border-slate-800">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-[9px] font-bold text-amber-400 uppercase tracking-wider bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                        {result.assessments[activeAssessment].type}
                      </span>
                      <span className="text-[9px] text-slate-500 uppercase">
                        {result.assessments[activeAssessment].difficulty}
                      </span>
                    </div>
                    <p className="text-xs text-slate-200 leading-relaxed font-semibold">
                      {result.assessments[activeAssessment].question}
                    </p>
                    {result.assessments[activeAssessment].hint && (
                      <div className="mt-2 flex items-start gap-1.5 text-[10px] text-slate-400 italic">
                        <Lightbulb size={11} className="text-amber-400/70 flex-shrink-0 mt-0.5" />
                        <span>{result.assessments[activeAssessment].hint}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
