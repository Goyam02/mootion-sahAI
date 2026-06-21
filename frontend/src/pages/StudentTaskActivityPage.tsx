import React, { useState, useEffect } from 'react';
import { LogoutModal } from '../components/LogoutModal';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { 
  ArrowLeft, 
  ChevronRight,
  X,
  Beaker,
  Maximize2,
  Minimize2
} from 'lucide-react';
import { TASKS, Task } from '../data/tasks';
import { NavItem } from '../components/NavItem';
import { api } from '../lib/api';
import { ChatbotFab } from '../components/ChatbotFab';
import { LayoutDashboard, CheckSquare, Gamepad2, BarChart2 } from 'lucide-react';

// Import modular Teach AI activities and progress panels
import { LiveVoiceActivity } from '../components/LiveVoiceActivity';
import ConnectItActivity from '../components/ConnectItActivity';

// --- Content Components ---

function QuizContent({ task }: { task: Task }) {
  const [questions, setQuestions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [timeLeft, setTimeLeft] = useState(10);

  useEffect(() => {
    // If it's a real backend task and we have quiz questions, use them!
    if ((task as any).dbTask) {
      const mainJob = (task as any).dbTask.jobs?.find((j: any) => j.asset_type === 'quiz' || j.asset_type === 'interactive_quiz');
      const questionsData = mainJob?.result_json?.questions || mainJob?.result_json?.quiz || (task as any).dbTask.content_json?.quiz;
      if (questionsData && Array.isArray(questionsData)) {
        setQuestions(questionsData);
        setLoading(false);
        return;
      }
    }

    // Fallback to generating simulated quiz
    fetch('/api/quiz', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subject: task.subject, topic: task.topic })
    })
    .then(res => res.json())
    .then(data => {
      if (data.questions) setQuestions(data.questions);
      setLoading(false);
    })
    .catch(() => setLoading(false));
  }, [task]);

  useEffect(() => {
    if (loading || isSubmitted || questions.length === 0) return;
    
    if (timeLeft <= 0) {
      if (currentIdx === questions.length - 1) {
        setIsSubmitted(true);
      } else {
        setCurrentIdx(prev => prev + 1);
        setTimeLeft(10);
      }
      return;
    }

    const timer = setInterval(() => {
      setTimeLeft(prev => prev - 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [timeLeft, loading, isSubmitted, questions.length, currentIdx]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center h-full min-h-[400px]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 border-4 border-[#1800ad]/20 border-t-[#1800ad] rounded-full animate-spin"></div>
          <p className="text-[#1800ad] font-bold text-lg animate-pulse">Generating quiz...</p>
        </div>
      </div>
    );
  }

  if (questions.length === 0) {
    return <div className="p-8 font-bold">Failed to load quiz.</div>;
  }

  const q = questions[currentIdx];
  const progress = ((currentIdx) / questions.length) * 100;

  if (isSubmitted) {
    let score = 0;
    questions.forEach((question, idx) => {
      const selectedOptString = answers[idx];
      const correctOptString = question.options[question.correctAnswer];
      if (selectedOptString === correctOptString) score++;
    });

    return (
       <div className="flex flex-col items-center flex-1 mt-6 max-w-3xl mx-auto w-full">
         <div className="bg-white p-10 rounded-[40px] flex flex-col items-center max-w-lg w-full border-2 border-[#1800ad]/10 shadow-xl">
            <h2 className="text-3xl font-black text-[#1800ad] mb-6">Quiz Complete!</h2>
            <div className="w-32 h-32 rounded-full border-8 border-[#1800ad] flex items-center justify-center mb-6">
              <span className="text-4xl font-black text-[#1800ad]">{Math.round((score / questions.length) * 100)}%</span>
            </div>
            <p className="font-bold text-[#1800ad]/70 mb-8">You answered {score} out of {questions.length} correctly.</p>
            
            <div className="flex gap-4 w-full">
              <button onClick={() => { setIsSubmitted(false); setAnswers({}); setCurrentIdx(0); setTimeLeft(10); }} className="flex-1 py-4 bg-[#1800ad]/10 text-[#1800ad] rounded-full font-bold hover:bg-[#1800ad]/20 transition-colors">
                Try Again
              </button>
            </div>
         </div>
       </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 max-w-3xl mx-auto w-full mt-6">
       <div className="w-full bg-[#1800ad]/10 h-2 rounded-full mb-8 overflow-hidden">
         <div className="h-full bg-[#1800ad] transition-all duration-300" style={{ width: `${progress}%` }}></div>
       </div>

       <div className="bg-white rounded-[40px] p-8 md:p-12 border-2 border-[#1800ad]/10 shadow-lg mb-6 relative min-h-[480px]">
          <div className="absolute top-8 right-8 flex items-center justify-center w-12 h-12 bg-[#1800ad]/10 text-[#1800ad] rounded-full font-bold text-xl">
            {timeLeft}
          </div>
          <span className="font-bold text-[#1800ad]/50 text-sm mb-4 block uppercase tracking-wider">Question {currentIdx + 1} of {questions.length}</span>
          <h3 className="text-2xl font-black text-[#1800ad] mb-8 pr-16">{q.questionText ?? q.question ?? q.prompt ?? q.text ?? ''}</h3>

          <div className="flex flex-col gap-4">
             {q.options?.map((opt: string) => (
                <button
                  key={opt} 
                  onClick={() => setAnswers({...answers, [currentIdx]: opt})}
                  className={`text-left flex items-center gap-4 p-5 rounded-2xl border-2 transition-all w-full ${answers[currentIdx] === opt ? 'border-[#1800ad] bg-[#1800ad]/5 shadow-[0_0_0_2px_rgba(24,0,173,0.1)]' : 'border-[#1800ad]/10 hover:border-[#1800ad]/30 hover:bg-[#f6f4ee]'}`}
                >
                  <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors ${answers[currentIdx] === opt ? 'border-[#1800ad]' : 'border-[#1800ad]/30'}`}>
                    {answers[currentIdx] === opt && <div className="w-3 h-3 bg-[#1800ad] rounded-full" />}
                  </div>
                  <span className={`font-bold text-lg ${answers[currentIdx] === opt ? 'text-[#1800ad]' : 'text-[#1800ad]/80'}`}>{opt}</span>
                </button>
             ))}
          </div>
       </div>

       <div className="flex justify-end items-center mt-auto pb-8">
          {currentIdx === questions.length - 1 ? (
             <button 
                onClick={() => setIsSubmitted(true)}
                disabled={!answers[currentIdx]}
                className="px-8 py-4 bg-[#1800ad] text-white rounded-full font-bold shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all disabled:opacity-50 disabled:hover:translate-y-0"
             >
                Submit Answers
              </button>
          ) : (
             <button 
                onClick={() => { setCurrentIdx(prev => prev + 1); setTimeLeft(10); }}
                disabled={!answers[currentIdx]}
                className="px-8 py-4 bg-[#1800ad] text-white rounded-full font-bold shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all flex items-center gap-2 disabled:opacity-50 disabled:hover:translate-y-0"
             >
                Next <ChevronRight size={20} />
             </button>
          )}
       </div>
    </div>
  );
}

function VideoSimulationContent({ task }: { task: Task }) {
  const [isFullscreen, setIsFullscreen] = useState(false);

  // ─── FIX: Prioritise content_json.external_url / embedUrl ──────────────
  const dbTask = (task as any).dbTask;
  const contentJson = dbTask?.content_json || {};

  // If content_json provides a direct URL, use that
  let mediaUrl: string | null = null;
  if (contentJson.external_url) {
    mediaUrl = contentJson.external_url;
  } else if (contentJson.embedUrl) {
    mediaUrl = contentJson.embedUrl;
  }

  // Fallback: old asset‑ID construction
  if (!mediaUrl) {
    const mainJob = dbTask?.jobs?.[0];
    const assetId = mainJob?.asset_id || task.id;
    const getBackendBaseUrl = () => {
      if (typeof window !== 'undefined') {
        const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        return isLocalhost ? 'http://localhost:8000' : window.location.origin;
      }
      return 'http://localhost:8000';
    };
    mediaUrl = `${getBackendBaseUrl()}/media/assets/${assetId}`;
  }

  // For mock tasks (no dbTask) we use a sample video
  const fallbackVideo = "https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4";
  const finalUrl = dbTask ? mediaUrl : fallbackVideo;

  const renderContent = (fullscreenMode = false) => {
    // Simulation / 3D Model rendering
    if (task.type === 'Simulation' || task.type === 'Predict It' || task.typeLabel === '3D Model') {
      return (
        <div className={`w-full bg-white flex items-center justify-center relative flex-col shrink-0 ${
          fullscreenMode 
            ? 'h-full' 
            : 'border-2 border-[#1800ad] overflow-hidden aspect-video md:aspect-auto md:flex-1 md:h-full md:min-h-[580px] md:rounded-[32px] rounded-2xl'
        }`}>
          {!fullscreenMode && (
            <div className="absolute inset-x-0 top-0 h-10 bg-[#1800ad] flex items-center justify-between px-4 z-10">
              <span className="text-white font-bold text-sm tracking-wider uppercase">{task.typeLabel || 'Simulation'}</span>
              <button 
                onClick={() => setIsFullscreen(true)}
                className="text-white hover:text-[#f6f4ee] hover:scale-105 transition-all p-1 flex items-center gap-1.5 text-xs font-bold uppercase"
                title="Enter Full Screen"
              >
                <Maximize2 size={14} />
                <span>Fullscreen</span>
              </button>
            </div>
          )}
          {dbTask ? (
            <iframe
              src={finalUrl}
              title={task.topic}
              allowFullScreen
              className={`w-full h-full border-0 ${fullscreenMode ? 'pt-0' : 'pt-10'}`}
              style={{ background: '#ffffff' }}
            />
          ) : (
            <div className={`px-8 py-16 flex flex-col items-center justify-center text-center ${fullscreenMode ? 'my-auto' : 'mt-10'}`}>
               <Beaker size={48} className="text-[#1800ad] mb-4 md:mb-6 md:w-16 md:h-16 animate-pulse" />
               <h3 className="text-xl md:text-2xl font-black text-[#1800ad] mb-2 md:mb-4">Sample {task.topic} Simulation</h3>
               <p className="text-[#1800ad]/70 font-medium max-w-lg text-sm md:text-base hidden sm:block">
                  Interact with the elements to observe the outcomes and prepare for your activities.
               </p>
               <button className="mt-4 md:mt-8 px-6 py-2 md:py-3 bg-[#1800ad] text-white rounded-full font-bold hover:scale-105 transition-transform text-sm md:text-base">
                  Run Complete Lifecycle
               </button>
            </div>
          )}
        </div>
      );
    }

    // Video
    const videoSrc = finalUrl;
    return (
      <div className={`w-full bg-black overflow-hidden relative shrink-0 font-montserrat font-semibold ${
        fullscreenMode 
          ? 'h-full flex items-center justify-center' 
          : 'aspect-video md:aspect-auto md:flex-1 md:h-full md:min-h-[580px] md:rounded-[32px] rounded-2xl'
      }`}>

        <video 
          className="w-full h-full object-contain md:object-cover" 
          controls 
          src={videoSrc}
          poster={!dbTask ? "https://storage.googleapis.com/gtv-videos-bucket/sample/images/BigBuckBunny.jpg" : undefined}
        ></video>
      </div>
    );
  };

  if (isFullscreen) {
    return (
      <div className="fixed inset-0 w-screen h-screen bg-[#f6f4ee] z-[99999] flex flex-col overflow-hidden font-montserrat">
        {/* Fullscreen Header */}
        <div className="w-full h-14 bg-[#1800ad] flex items-center justify-between px-6 shrink-0 shadow-md">
          <div className="flex flex-col">
            <span className="text-white/60 font-bold text-[10px] uppercase tracking-wider">{task.subject} • {task.typeLabel || 'Simulation'}</span>
            <span className="text-white font-extrabold text-sm md:text-base leading-tight">{task.topic}</span>
          </div>
          <button 
            onClick={() => setIsFullscreen(false)}
            className="bg-white/10 hover:bg-white/20 border border-white/20 text-white rounded-full px-4 py-1.5 font-black text-xs md:text-sm uppercase tracking-wider flex items-center gap-2 hover:scale-103 transition-all"
          >
            <Minimize2 size={16} />
            <span>Exit Fullscreen</span>
          </button>
        </div>
        {/* Fullscreen Content Area */}
        <div className="flex-1 w-full bg-white relative">
          {renderContent(true)}
        </div>
      </div>
    );
  }

  return renderContent(false);
}

// --- Main Page ---

export function StudentTaskActivityPage() {
  const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);
  const { taskId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const fromHome = searchParams.get('fromHome') === 'true';
  const classId = searchParams.get('class_id');
  
  let backUrl = fromHome ? '/student/home' : '/student/tasks';

  const [dbTask, setDbTask] = useState<any | null>(null);
  const [loadingDbTask, setLoadingDbTask] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [resolvedSubject, setResolvedSubject] = useState('Science');

  useEffect(() => {
    if (!classId) return;
    const fetchClassSubject = async () => {
      try {
        const classes: any[] = await api.get('/students/classes');
        const matched = classes.find(c => c.class_id === classId);
        if (matched?.subject) {
          setResolvedSubject(matched.subject);
        }
      } catch (err) {
        console.error("Failed to load class subject:", err);
      }
    };
    fetchClassSubject();
  }, [classId]);

  useEffect(() => {
    // If it's a static task ID (like p1, c1, m1), we don't fetch
    if (!taskId || ['p1', 'p2', 'c1', 'c2', 'c3', 'm1', 'm2', 'm3', 'b1', 'b2', 'b3'].includes(taskId)) {
      return;
    }
    
    if (!classId) {
      setFetchError("Missing class_id parameter to load assignment.");
      return;
    }

    const fetchAssignment = async () => {
      setLoadingDbTask(true);
      setFetchError(null);
      try {
        const res = await api.get(`/students/classes/${classId}/assignments/${taskId}`);
        setDbTask(res);
      } catch (err: any) {
        console.error("Failed to load assignment:", err);
        setFetchError(err?.detail || err?.message || "Failed to load assignment.");
      } finally {
        setLoadingDbTask(false);
      }
    };
    fetchAssignment();
  }, [taskId, classId]);
  
  // Resolve task or dynamic task from explore chapters or backend
  let task: any = null;

  if (dbTask) {
    let taskType: any = 'Video';
    let typeLabel = 'Watch Video';
    if (dbTask.assignment_type === 'quiz') {
      taskType = 'Quiz';
      typeLabel = 'Attempt Quiz';
    } else if (['predict_ai', 'PREDICT_IT', 'predict_it', 'simulation'].includes(dbTask.assignment_type)) {
      taskType = 'Predict It';
      typeLabel = 'Predict It';
    } else if (dbTask.assignment_type === 'model') {
      taskType = 'Simulation';
      typeLabel = '3D Model';
    } else if (['explain_ai', 'EXPLAIN_IT', 'explain_it'].includes(dbTask.assignment_type)) {
      taskType = 'Explain It';
      typeLabel = 'Explain It';
    } else if (['spot_it', 'SPOT_IT', 'connect_it'].includes(dbTask.assignment_type)) {
      taskType = 'Connect It';
      typeLabel = 'Connect It';
    } else if (['interactive_quiz', 'INTERACTIVE_QUIZ'].includes(dbTask.assignment_type)) {
      taskType = 'Interactive Quiz';
      typeLabel = 'Interactive Quiz';
    }

    task = {
      id: dbTask.assignment_id,
      type: taskType,
      typeLabel: typeLabel,
      topic: dbTask.title,
      subject: resolvedSubject,
      deadline: 'Due Soon',
      status: dbTask.status === 'ready' ? 'Not Started' : 'In Progress',
      dbTask: dbTask
    };
  } else {
    task = TASKS.find(t => t.id === taskId);
  }

  const [activeActivity, setActiveActivity] = useState<string | null>(null);

  useEffect(() => {
    if (task && ['Explain It', 'Connect It'].includes(task.type)) {
      setActiveActivity(task.type);
    } else {
      setActiveActivity(null);
    }
  }, [task?.type]);

  if (loadingDbTask) {
    return (
      <div className="flex flex-1 w-full h-[100dvh] bg-[#f6f4ee] font-montserrat text-[#1800ad] flex-col items-center justify-center">
        <div className="w-16 h-16 border-4 border-[#1800ad]/20 border-t-[#1800ad] rounded-full animate-spin mb-4"></div>
        <p className="font-bold text-lg animate-pulse">Loading assignment details...</p>
      </div>
    );
  }

  if (fetchError && !task) {
    return (
      <div className="flex flex-1 w-full h-[100dvh] bg-[#f6f4ee] font-montserrat text-rose-600 flex-col items-center justify-center p-6 text-center">
        <div className="text-4xl mb-4">⚠️</div>
        <h3 className="text-xl font-bold">Failed to load assignment</h3>
        <p className="text-sm opacity-80 mt-1 max-w-sm">{fetchError}</p>
        <button onClick={() => navigate(backUrl)} className="mt-6 px-6 py-2.5 bg-[#1800ad] text-white rounded-full font-bold font-montserrat">
          Go Back
        </button>
      </div>
    );
  }

  if (!task) {
    return <div className="p-10 font-bold text-[#1800ad]">Task not found</div>;
  }

  return (
    <div className="flex flex-1 w-full h-[100dvh] bg-[#1800ad] font-montserrat text-[#1800ad] overflow-hidden relative">
      <ChatbotFab context={`User is doing ${activeActivity || task.type} for subject ${task.subject}, topic ${task.topic}`} />
      
      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex w-[80px] lg:w-[100px] flex-col items-center justify-between py-8 fixed top-0 bottom-0 left-0 h-full shrink-0 bg-[#1800ad] text-[#f6f4ee] z-30">
        {/* Logo */}
        <div className="flex items-center justify-center shrink-0 mt-4 cursor-pointer" onClick={() => navigate('/')}>
          <span className="text-[#f6f4ee] font-val text-[42px] leading-none tracking-widest mt-1 mr-1">M</span>
        </div>
        <nav className="flex flex-col gap-6 w-full items-center my-auto">
          <NavItem icon={<LayoutDashboard size={24} />} onClick={() => navigate('/student/home')} />
          <NavItem icon={<CheckSquare size={24} />} active onClick={() => navigate('/student/tasks')} />
          <NavItem icon={<Gamepad2 size={24} />} onClick={() => navigate('/student/playground')} />
          <NavItem icon={<BarChart2 size={24} />} onClick={() => navigate('/student/analytics')} />
        </nav>
        <div onClick={() => setIsLogoutModalOpen(true)} className="shrink-0 cursor-pointer flex items-center justify-center group w-12 h-12 rounded-full border-2 border-[#1800ad] bg-[#f6f4ee] relative">
           <span className="text-[#1800ad] font-bold text-lg">P</span>
        </div>
      </aside>

      <main className="flex-1 md:ml-[80px] lg:ml-[100px] bg-[#f6f4ee] md:rounded-l-[40px] p-5 md:p-8 flex flex-col overflow-hidden h-[100dvh]">
        {!activeActivity && (
          <header className="shrink-0 mb-6 flex items-center gap-4">
            <button onClick={() => navigate(backUrl)} className="p-2 border-2 border-[#1800ad]/10 rounded-full text-[#1800ad] hover:bg-[#1800ad]/5 transition-colors">
              <ArrowLeft size={20} />
            </button>
            <div className="flex flex-col">
              <span className="text-[#1800ad]/60 font-bold text-xs uppercase tracking-wider">{task.subject}</span>
              <h1 className="text-xl md:text-2xl font-black text-[#1800ad] leading-none mt-1">{task.topic}</h1>
            </div>
          </header>
        )}

        <div className="flex flex-1 overflow-hidden min-h-0 gap-8">
          {/* Main Content Area */}
          <div className={`flex-1 flex flex-col min-h-0 overflow-y-auto custom-scrollbar pb-20 md:pb-0 ${activeActivity ? 'max-w-none' : ''}`}>
             <AnimatePresence mode="wait">
               {activeActivity === 'Explain It' && (
                 <motion.div key="ExplainIt" initial={{opacity:0, y:20}} animate={{opacity:1, y:0}} exit={{opacity:0, y:-20}} className="h-full">
                   <LiveVoiceActivity task={task} activityName="Explain It" instructions="Teach the concept and answer questions." onDone={() => navigate(backUrl)} />
                 </motion.div>
               )}
               {activeActivity === 'Connect It' && (
                 <motion.div key="ConnectIt" initial={{opacity:0, y:20}} animate={{opacity:1, y:0}} exit={{opacity:0, y:-20}} className="h-full">
                   <ConnectItActivity task={task} onDone={() => navigate(backUrl)} />
                 </motion.div>
               )}
              {!activeActivity && (
                  <motion.div key="default" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="h-full flex flex-col">
                      {(task.type === 'Quiz' || task.type === 'Interactive Quiz') ? <QuizContent task={task} /> : <VideoSimulationContent task={task} />}
                     
                     {/* Mobile Activity Grid */}
                     <div className="lg:hidden w-full mt-6 pb-12">
                        <div className="bg-[#1800ad] rounded-[22px] p-4 shadow-lg relative overflow-hidden">
                          <h3 className="font-bold text-md text-white mb-2 pb-1 border-b border-white/10 tracking-wide">Activity</h3>
                          <div className="grid grid-cols-2 gap-2.5 relative z-10 w-full">
                             <button onClick={() => setActiveActivity('Explain It')} className="bg-[#f6f4ee] rounded-[16px] h-14 flex flex-col items-center justify-center shadow-md hover:scale-102 transition-transform">
                                <span className="font-bold text-sm text-[#1800ad] text-center leading-tight">Explain It</span>
                             </button>
                             <button onClick={() => setActiveActivity('Connect It')} className="bg-[#f6f4ee] rounded-[16px] h-14 flex flex-col items-center justify-center shadow-md hover:scale-102 transition-transform">
                                <span className="font-bold text-sm text-[#1800ad] text-center leading-tight">Connect It</span>
                             </button>
                          </div>
                        </div>
                     </div>
                 </motion.div>
               )}
             </AnimatePresence>
          </div>

          {/* Activity Sidebar */}
          {!activeActivity && (
            <div className="hidden lg:flex w-80 shrink-0 flex-col bg-[#1800ad] px-6 pt-5 pb-5 rounded-[28px] overflow-y-auto custom-scrollbar relative shadow-xl h-fit">
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-bold tracking-wide text-lg text-white">Activity</h3>
                <button onClick={() => navigate(backUrl)} className="p-1.5 text-white/80 hover:bg-white/20 rounded-full transition-colors bg-white/10">
                  <X size={16} />
                </button>
              </div>
              
              <div className="grid grid-cols-2 gap-3">
                <button 
                  onClick={() => setActiveActivity('Explain It')} 
                  className="h-24 bg-[#f6f4ee] rounded-[20px] p-3 flex flex-col justify-center items-center group hover:scale-[1.03] transition-all shadow-md relative"
                >
                  <span className="font-bold text-center text-[#1800ad] text-sm leading-tight">Explain<br/>It</span>
                </button>

                <button 
                  onClick={() => setActiveActivity('Connect It')} 
                  className="h-24 bg-[#f6f4ee] rounded-[20px] p-3 flex flex-col justify-center items-center group hover:scale-[1.03] transition-all shadow-md relative"
                >
                  <span className="font-bold text-center text-[#1800ad] text-sm leading-tight">Connect<br/>It</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </main>
      {/* MODAL: Logout Confirmation */}
      <LogoutModal isOpen={isLogoutModalOpen} onClose={() => setIsLogoutModalOpen(false)} />
    </div>
  );
}