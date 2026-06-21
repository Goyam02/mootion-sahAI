import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  LayoutDashboard, 
  CheckSquare, 
  Gamepad2, 
  Search, 
  ArrowRight,
  Flame,
  ChevronLeft, 
  ChevronRight,
  X,
  Play,
  Sparkles,
  BookOpen,
  Clock,
  AlertCircle,
  ChevronDown,
  BarChart2
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useNavigate } from 'react-router-dom';
import { ChatbotFab } from '../components/ChatbotFab';
import { NavItem } from '../components/NavItem';
import { LogoutModal } from '../components/LogoutModal';
import { api } from '../lib/api';
import { getTranslationLanguage, setTranslationLanguage } from '../lib/translation';

// ─── Types ───────────────────────────────────────────────────────────────────

interface StudentClass {
  class_id: string;
  class_code: string;
  display_name: string;
  grade: string;
  subject: string;
}

interface StudentAssignment {
  assignment_id: string;
  class_id: string;
  chapter_id: string;
  assignment_type: string;
  title: string;
  status: string; // 'queued' | 'processing' | 'ready' | 'failed'
  job_count: number;
}

interface Chapter {
  chapter_id: string;
  class_id: string;
  sequence_number: number;
  title: string;
  status: string;
  asset_count: number;
}

// ─── Priority ordering ─────────────────────────────────────────────────────

const formatDisplayTitle = (type: string, title: string) => {
  if (!title) return '';
  let t = title.charAt(0).toUpperCase() + title.slice(1);
  if (type === 'simulation' && !t.toLowerCase().includes('predict it')) {
    return `Predict It - ${t}`;
  }
  return t;
};

const ASSIGNMENT_TYPE_PRIORITY: Record<string, number> = {
  explain_ai: 0,
  predict_ai: 1,
  spot_it: 2,
  connect_it: 3,
  quiz: 4,
  video: 5,
  simulation: 6,
  model: 7,
};

const ASSIGNMENT_TYPE_LABELS: Record<string, string> = {
  explain_ai: 'Explain It',
  predict_ai: 'Predict It',
  spot_it: 'Spot It',
  connect_it: 'Connect It',
  quiz: 'Quiz',
  video: 'Watch',
  simulation: 'Simulation',
  model: '3D Model',
};

// ─── Component ────────────────────────────────────────────────────────────

export function StudentHomePage() {
  const navigate = useNavigate();

  // ── State ──
  const [classes, setClasses] = useState<StudentClass[]>([]);
  const [allAssignments, setAllAssignments] = useState<(StudentAssignment & { subject: string })[]>([]);
  const [isLoadingClasses, setIsLoadingClasses] = useState(true);
  const [isLoadingAssignments, setIsLoadingAssignments] = useState(false);

  // Join Class Modal
  const [isJoinModalOpen, setIsJoinModalOpen] = useState(false);
  const [joinClassCodes, setJoinClassCodes] = useState<{ value: string; error: string | null }[]>([
    { value: '', error: null }
  ]);
  const [isJoining, setIsJoining] = useState(false);

  // Class Chapters Modal
  const [selectedClass, setSelectedClass] = useState<StudentClass | null>(null);
  const [classChapters, setClassChapters] = useState<Chapter[]>([]);
  const [isLoadingChapters, setIsLoadingChapters] = useState(false);

  // Student name
  const [studentName, setStudentName] = useState<string>('');

  // ─── Calendar data ──────────────────────────────────────────────────────
  const [calendarDate, setCalendarDate] = useState<Date>(new Date());
  const [calendarData, setCalendarData] = useState<{ date: Date | null; value: number; dayNumber: number | null }[]>([]);
  const [isLoadingCalendar, setIsLoadingCalendar] = useState(true);

  const [isLangDropdownOpen, setIsLangDropdownOpen] = useState(false);
  const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);
  const langDropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (langDropdownRef.current && !langDropdownRef.current.contains(event.target as Node)) {
        setIsLangDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLanguageChange = async (langCode: string) => {
    try {
      const dbLang = langCode === 'hi' ? 'hindi' : 'english';
      await api.post('/students/language', { preferred_language: dbLang });
    } catch (err) {
      console.error("Failed to save student language preference:", err);
    }
    setTranslationLanguage(langCode);
  };

  // ── Fetch student profile ──
  useEffect(() => {
    api.get('/students/me').then((me: any) => {
      if (me?.full_name) {
        const firstName = me.full_name.split(' ')[0];
        setStudentName(firstName);
      }
    }).catch(() => {});
  }, []);

  // ── Fetch classes then assignments ──
  const fetchClasses = useCallback(async () => {
    setIsLoadingClasses(true);
    try {
      const data: StudentClass[] = await api.get('/students/classes');
      setClasses(data);
      // Now fetch assignments for all classes in parallel
      if (data.length > 0) {
        setIsLoadingAssignments(true);
        const results = await Promise.allSettled(
          data.map(cls =>
            api.get(`/students/classes/${cls.class_id}/assignments`).then((list: StudentAssignment[]) =>
              list.map(a => ({ ...a, subject: cls.subject }))
            )
          )
        );
        const flat: (StudentAssignment & { subject: string })[] = [];
        results.forEach(r => {
          if (r.status === 'fulfilled') flat.push(...r.value);
        });
        setAllAssignments(flat);
        setIsLoadingAssignments(false);
      }
    } catch (err: any) {
      console.error('Failed to fetch student classes:', err);
      if (err.status === 403 || err.status === 401) {
        localStorage.removeItem('mootion_access_token');
        localStorage.removeItem('mootion_refresh_token');
        navigate('/login/student');
      }
    } finally {
      setIsLoadingClasses(false);
    }
  }, [navigate]);

  useEffect(() => { fetchClasses(); }, [fetchClasses]);

  // ── Fetch chapters when a class is selected ──
  useEffect(() => {
    if (!selectedClass) return;
    const fetchChapters = async () => {
      setIsLoadingChapters(true);
      try {
        const data: Chapter[] = await api.get(`/students/classes/${selectedClass.class_id}/chapters`);
        const sorted = [...data].sort((a, b) => a.sequence_number - b.sequence_number);
        setClassChapters(sorted);
      } catch {
        setClassChapters([]);
      } finally {
        setIsLoadingChapters(false);
      }
    };
    fetchChapters();
  }, [selectedClass]);

  // ─── Fetch calendar data ──────────────────────────────────────────────
  const fetchCalendarData = useCallback(async () => {
    setIsLoadingCalendar(true);
    try {
      const year = calendarDate.getFullYear();
      const month = calendarDate.getMonth() + 1; // 1-indexed
      const res = await api.get(`/students/activity/calendar?year=${year}&month=${month}`);
      const daysData: { date: string, value: number }[] = res.days || [];
      
      const data = [];
      const today = new Date();
      
      const firstDay = new Date(year, month - 1, 1);
      const startingDayOfWeek = firstDay.getDay(); 
      
      const daysInMonth = new Date(year, month, 0).getDate();
      
      // Pad beginning of month
      for (let i = 0; i < startingDayOfWeek; i++) {
        data.push({ date: null, value: -1, dayNumber: null });
      }
      
      // Build map of fetched data
      const activityMap = new Map<string, number>();
      daysData.forEach(d => activityMap.set(d.date, d.value));

      for (let i = 1; i <= daysInMonth; i++) {
        const d = new Date(year, month - 1, i);
        // adjust local date to ISO string (YYYY-MM-DD) for lookup
        const isoString = d.toLocaleDateString('en-CA'); // e.g. "2026-06-21"
        const isToday = d.toDateString() === today.toDateString();
        
        let rawValue = activityMap.get(isoString) || 0;
        let mappedValue = 0;
        if (rawValue > 0) {
          // Normalize real data count to 1-4 scale
          if (rawValue >= 10) mappedValue = 4;
          else if (rawValue >= 5) mappedValue = 3;
          else if (rawValue >= 2) mappedValue = 2;
          else mappedValue = 1;
        }

        if (isToday) {
          // Override: forcefully show today as active if it's 0 (Pending user confirmation)
          mappedValue = mappedValue === 0 ? 3 : mappedValue;
        }
        
        data.push({
          date: d,
          value: mappedValue, 
          dayNumber: i
        });
      }

      // Pad remaining cells to complete 7-column grid
      while (data.length % 7 !== 0) {
        data.push({ date: null, value: -1, dayNumber: null });
      }
      
      setCalendarData(data);
    } catch (err) {
      console.error("Failed to fetch calendar:", err);
    } finally {
      setIsLoadingCalendar(false);
    }
  }, [calendarDate]);

  useEffect(() => {
    fetchCalendarData();
  }, [fetchCalendarData]);

  const handlePrevMonth = () => {
    setCalendarDate(prev => new Date(prev.getFullYear(), prev.getMonth() - 1, 1));
  };

  const handleNextMonth = () => {
    setCalendarDate(prev => new Date(prev.getFullYear(), prev.getMonth() + 1, 1));
  };

  // ── Up Next: top ready assignment by priority ──
  const readyAssignments = allAssignments.filter(a => a.status === 'ready');
  readyAssignments.sort((a, b) => {
    const pa = ASSIGNMENT_TYPE_PRIORITY[a.assignment_type] ?? 99;
    const pb = ASSIGNMENT_TYPE_PRIORITY[b.assignment_type] ?? 99;
    return pa - pb;
  });
  const upNext = readyAssignments[0] ?? null;
  const upNextClass = upNext ? classes.find(c => c.class_id === upNext.class_id) : null;

  // ── Join class handlers ──
  const addClassCodeField = () => setJoinClassCodes([...joinClassCodes, { value: '', error: null }]);

  const handleClassCodeChange = (index: number, val: string) => {
    const next = [...joinClassCodes];
    next[index] = { value: val, error: null };
    setJoinClassCodes(next);
  };

  const handleJoinClasses = async () => {
    setIsJoining(true);
    let hasError = false;
    const nextCodes = [...joinClassCodes];
    for (let i = 0; i < nextCodes.length; i++) {
      const item = nextCodes[i];
      if (item.value.trim()) {
        try {
          await api.post('/students/join-class', { class_code: item.value.trim() });
        } catch {
          hasError = true;
          nextCodes[i] = { ...item, error: 'Class not found — check the code with your teacher' };
        }
      }
    }
    setJoinClassCodes(nextCodes);
    await fetchClasses();
    setIsJoining(false);
    if (!hasError) {
      setIsJoinModalOpen(false);
      setJoinClassCodes([{ value: '', error: null }]);
    }
  };

  // ── Calendar helpers ──
  const getCellColor = (value: number, date: Date | null) => {
    if (date) {
      const dOpts = new Date(date).setHours(0,0,0,0);
      const todayOpts = new Date().setHours(0,0,0,0);
      if (dOpts > todayOpts) return 'bg-gray-300 pointer-events-none text-gray-500';
    }
    if (value === 0) return 'bg-[#1800ad]/10';
    if (value === 1) return 'bg-[#1800ad]/30';
    if (value === 2) return 'bg-[#1800ad]/50';
    if (value === 3) return 'bg-[#1800ad]/70';
    return 'bg-[#1800ad]';
  };

  return (
    <div className="flex flex-1 w-full h-[100dvh] bg-[#1800ad] font-montserrat text-[#1800ad] overflow-hidden relative">

      {/* Mobile Bottom Navigation Bar */}
      <nav className="md:hidden fixed bottom-4 left-4 right-4 bg-[#1800ad] px-6 py-2 flex justify-between items-center z-45 rounded-full shadow-[0_10px_40px_rgba(24,0,173,0.25)] border-[2px] border-[#f6f4ee]">
        <NavItem icon={<LayoutDashboard size={22} />} active onClick={() => navigate('/student/home')} />
        <NavItem icon={<CheckSquare size={22} />} onClick={() => navigate('/student/tasks')} />

        <NavItem icon={<Gamepad2 size={22} />} onClick={() => navigate('/student/playground')} />
        <NavItem icon={<BarChart2 size={22} />} onClick={() => navigate('/student/analytics')} />
        <div 
          onClick={() => setIsLogoutModalOpen(true)}
          className="shrink-0 cursor-pointer flex items-center justify-center w-8 h-8 rounded-full border border-[#f6f4ee] bg-[#f6f4ee] hover:opacity-90 transition-opacity"
        >
          <span className="text-[#1800ad] font-bold text-xs">
            {studentName ? studentName[0].toUpperCase() : 'S'}
          </span>
        </div>
      </nav>

      {/* ChatBot FAB */}
      <ChatbotFab />


      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex w-[80px] lg:w-[100px] flex-col items-center justify-between py-8 fixed top-0 bottom-0 left-0 h-full shrink-0 bg-[#1800ad] text-[#f6f4ee] z-30 font-montserrat">
        <div className="flex items-center justify-center shrink-0 mt-4 cursor-pointer" onClick={() => navigate('/student/home')}>
          <span className="text-[#f6f4ee] font-val text-[42px] leading-none tracking-widest mt-1 mr-1 notranslate">M</span>
        </div>
        <nav className="flex flex-col gap-6 w-full items-center my-auto">
          <NavItem icon={<LayoutDashboard size={24} />} active onClick={() => navigate('/student/home')} />
          <NavItem icon={<CheckSquare size={24} />} onClick={() => navigate('/student/tasks')} />

          <NavItem icon={<Gamepad2 size={24} />} onClick={() => navigate('/student/playground')} />
          <NavItem icon={<BarChart2 size={24} />} onClick={() => navigate('/student/analytics')} />
        </nav>
        <div onClick={() => setIsLogoutModalOpen(true)} className="shrink-0 cursor-pointer flex items-center justify-center group w-12 h-12 rounded-full border-2 border-[#1800ad] bg-[#f6f4ee] hover:opacity-90 transition-opacity duration-300 shadow-sm relative">
          <span className="text-[#1800ad] font-bold text-lg transition-colors duration-300">
            {studentName ? studentName[0].toUpperCase() : 'S'}
          </span>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 md:ml-[80px] lg:ml-[100px] bg-[#f6f4ee] md:rounded-l-[40px] lg:rounded-l-[50px] p-5 md:pl-10 lg:pl-12 xl:pl-16 md:pr-8 lg:pr-10 w-full overflow-y-auto custom-scrollbar pt-6 md:pt-10 pb-32 lg:pb-12 relative flex flex-col h-[100dvh]">
        <div className="max-w-[1300px] w-full h-full">

          {/* Top Header */}
          <header className="flex flex-col xl:flex-row xl:justify-between xl:items-end gap-6 mb-8 lg:mb-10 w-full relative">
            <div className="flex flex-col gap-2">
              <h1 className="text-3xl md:text-3xl lg:text-4xl font-bold tracking-tight text-[#1800ad]">
                Welcome Back{studentName ? `, ${studentName}` : ''} 👋
              </h1>
              <div className="flex flex-wrap items-center gap-3 mt-1">
                <p className="text-[#1800ad]/70 font-medium">Let's keep the momentum going.</p>
                <div className="flex items-center gap-1.5 px-3 py-1 bg-[#f6f4ee] text-[#1800ad] rounded-full border-2 border-[#1800ad] shadow-sm">
                  <Flame size={16} className="text-[#1800ad]" fill="currentColor" />
                  <span className="text-xs sm:text-sm font-bold tracking-wide">Keep Learning!</span>
                </div>
              </div>
            </div>
            {/* Search Bar & Language Selector */}
            <div className="flex flex-wrap sm:flex-nowrap items-center gap-4 relative w-[calc(100%+16px)] -ml-2 translate-y-1.5 xl:translate-y-0 xl:ml-0 xl:w-auto">
              <div ref={langDropdownRef} className="relative mr-5 -left-2 z-40">
                <button
                  type="button"
                  onClick={() => setIsLangDropdownOpen(!isLangDropdownOpen)}
                  className="pl-6 pr-12 py-3.5 bg-[#f6f4ee] border-2 border-[#1800ad] rounded-full text-xs sm:text-sm outline-none focus:ring-4 focus:ring-[#1800ad]/10 transition-all font-black text-[#1800ad] cursor-pointer shadow-sm tracking-wide flex items-center justify-between min-w-[130px]"
                >
                  <span>{getTranslationLanguage() === 'hi' ? 'हिन्दी' : 'English'}</span>
                  <div className="absolute right-7 flex items-center pointer-events-none text-[#1800ad]">
                    <ChevronDown size={16} className={`stroke-[3] transition-transform duration-300 ${isLangDropdownOpen ? 'rotate-180' : ''}`} />
                  </div>
                </button>

                <AnimatePresence>
                  {isLangDropdownOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 8 }}
                      transition={{ duration: 0.15 }}
                      className="absolute top-full mt-2 left-0 right-0 bg-[#f6f4ee] border-2 border-[#1800ad] rounded-[24px] shadow-lg overflow-hidden flex flex-col py-1.5 z-30"
                    >
                      <button
                        type="button"
                        onClick={() => {
                          handleLanguageChange('en');
                          setIsLangDropdownOpen(false);
                        }}
                        className={`px-5 py-2.5 text-left text-xs sm:text-sm font-bold text-[#1800ad] hover:bg-[#1800ad]/10 transition-colors ${getTranslationLanguage() === 'en' ? 'bg-[#1800ad]/5 font-black' : ''}`}
                      >
                        English
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          handleLanguageChange('hi');
                          setIsLangDropdownOpen(false);
                        }}
                        className={`px-5 py-2.5 text-left text-xs sm:text-sm font-bold text-[#1800ad] hover:bg-[#1800ad]/10 transition-colors ${getTranslationLanguage() === 'hi' ? 'bg-[#1800ad]/5 font-black' : ''}`}
                      >
                        हिन्दी (Hindi)
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <div className="relative w-full sm:w-[380px]">
                <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
                  <Search size={18} className="text-[#1800ad]/60" />
                </div>
                <input
                  type="text"
                  placeholder="Search your library..."
                  className="w-full pl-12 pr-4 py-3 md:py-3.5 bg-transparent border-2 border-[#1800ad]/30 rounded-full text-sm outline-none focus:border-[#1800ad] focus:ring-4 focus:ring-[#1800ad]/10 transition-all placeholder:text-[#1800ad]/50 font-medium text-[#1800ad]"
                />
              </div>
            </div>
          </header>

          {/* Section: My Classes */}
          <section className="mb-8 w-full font-montserrat">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-[#1800ad]">My Classes</h2>
              <button
                onClick={() => setIsJoinModalOpen(true)}
                className="px-5 py-2 bg-[#1800ad] text-[#f6f4ee] border-2 border-[#1800ad] rounded-full text-xs font-extrabold hover:bg-[#f6f4ee] hover:text-[#1800ad] transition-all shadow-md"
              >
                + Join a class
              </button>
            </div>

            {isLoadingClasses ? (
              <div className="py-8 flex items-center justify-center">
                <div className="w-8 h-8 border-4 border-[#1800ad]/20 border-t-[#1800ad] rounded-full animate-spin"></div>
              </div>
            ) : classes.length === 0 ? (
              <div className="bg-[#f6f4ee] border-2 border-dashed border-[#1800ad]/20 rounded-[32px] p-8 text-center text-[#1800ad]/60 font-semibold text-sm">
                You haven't joined any classes yet. Click "+ Join a class" to get started!
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                {classes.map((cls) => (
                  <motion.div
                    key={cls.class_id}
                    whileHover={{ y: -4 }}
                    onClick={() => setSelectedClass(cls)}
                    className="p-5 rounded-[28px] border-2 border-[#1800ad]/20 bg-[#f6f4ee] text-[#1800ad] flex flex-col justify-between cursor-pointer hover:border-[#1800ad] transition-all group shadow-sm min-h-[140px]"
                  >
                    <div>
                      <span className="text-[10px] font-bold opacity-60 uppercase tracking-wider block mb-1">{cls.subject}</span>
                      <h3 className="text-lg font-black group-hover:text-[#1800ad] leading-tight">{cls.display_name}</h3>
                    </div>
                    <div className="flex items-center justify-between mt-4 pt-3 border-t border-[#1800ad]/10 text-xs font-bold opacity-75">
                      <span>Grade {cls.grade}</span>
                      <span className="bg-[#1800ad]/10 px-2.5 py-1 rounded-full font-mono">{cls.class_code}</span>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </section>

          <div className="flex flex-col xl:grid xl:grid-cols-[1fr_380px] gap-8 lg:gap-10">

            {/* Section: Up Next */}
            <section className="flex flex-col h-full order-1">
              <h2 className="text-xl font-bold mb-4 text-[#1800ad]">Up Next</h2>

              {isLoadingClasses || isLoadingAssignments ? (
                <div className="bg-[#1800ad]/5 border-2 border-[#1800ad]/10 rounded-[32px] p-8 flex items-center justify-center min-h-[200px]">
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-8 h-8 border-4 border-[#1800ad]/20 border-t-[#1800ad] rounded-full animate-spin"></div>
                    <span className="text-xs font-bold text-[#1800ad]/60 animate-pulse">Loading assignments...</span>
                  </div>
                </div>
              ) : upNext ? (
                <motion.div
                  whileHover={{ y: -4 }}
                  onClick={() => {
                    if (['video', 'simulation', 'quiz', 'model', 'explain_ai', 'predict_ai', 'spot_it', 'connect_it', 'interactive_quiz', 'EXPLAIN_IT', 'PREDICT_IT', 'SPOT_IT', 'INTERACTIVE_QUIZ', 'explain_it', 'predict_it'].includes(upNext.assignment_type)) {
                      navigate(`/student/task/${upNext.assignment_id}?class_id=${upNext.class_id}`);
                    } else {
                      navigate(`/student/playground?assignment_id=${upNext.assignment_id}&class_id=${upNext.class_id}`);
                    }
                  }}
                  className="bg-[#1800ad] text-[#f6f4ee] p-5 md:p-8 rounded-[32px] md:rounded-[40px] flex flex-col justify-between gap-4 md:gap-6 relative overflow-hidden group cursor-pointer shadow-lg border-2 border-[#1800ad] flex-1"
                >
                  <div className="absolute -top-24 -right-24 w-64 h-64 bg-[#f6f4ee]/10 rounded-full blur-3xl pointer-events-none group-hover:scale-110 transition-transform duration-700"></div>

                  <div>
                    <div className="flex justify-between items-start z-10 w-full mb-2">
                      <div className="flex items-center gap-2 px-4 py-2 bg-[#f6f4ee] text-[#1800ad] rounded-full text-sm font-bold w-fit">
                        <span className="w-2 h-2 rounded-full bg-[#1800ad] animate-pulse"></span>
                        {ASSIGNMENT_TYPE_LABELS[upNext.assignment_type] ?? upNext.assignment_type}
                      </div>
                    </div>

                    <div className="z-10 mt-2">
                      <span className="text-[#f6f4ee]/70 font-semibold mb-1 md:mb-2 block tracking-wider uppercase text-xs">
                        {upNext.subject}{upNextClass ? ` · Grade ${upNextClass.grade}` : ''}
                      </span>
                      <h3 className="text-xl md:text-3xl lg:text-4xl font-bold text-[#f6f4ee] leading-tight max-w-[90%]">
                        {formatDisplayTitle(upNext.assignment_type, upNext.title)}
                      </h3>
                    </div>
                  </div>

                  <div className="z-10 mt-4 md:mt-6 lg:mt-auto">
                    <button className="flex items-center justify-center gap-2 bg-[#f6f4ee] text-[#1800ad] px-6 md:px-8 py-3 rounded-full font-bold text-base hover:bg-white hover:shadow-lg transition-all w-full sm:w-auto">
                      Start
                      <ArrowRight size={18} />
                    </button>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="relative bg-[#1800ad] text-[#f6f4ee] p-6 md:p-8 rounded-[32px] md:rounded-[40px] flex flex-col justify-between gap-6 overflow-hidden shadow-xl border-2 border-[#1800ad] flex-1"
                >
                  <div className="absolute top-0 right-0 w-80 h-80 bg-radial-gradient from-white/10 to-transparent rounded-full blur-2xl pointer-events-none animate-pulse"></div>
                  <div>
                    <div className="flex justify-between items-start z-10 w-full mb-3">
                      <div className="flex items-center gap-1.5 px-3.5 py-1.5 bg-[#f6f4ee] text-[#1800ad] rounded-full text-[11px] font-black uppercase tracking-wider shadow">
                        <Sparkles size={13} className="text-amber-500 fill-amber-500 animate-pulse" />
                        All Caught Up!
                      </div>
                    </div>
                    <div className="z-10 mt-3">
                      <p className="text-xl md:text-2xl font-black text-[#f6f4ee] leading-snug">
                        🎉 You're all caught up!
                      </p>
                      <p className="text-xs sm:text-sm text-[#f6f4ee]/70 mt-2 font-medium max-w-[90%] leading-relaxed">
                        No ready assignments right now. Head to the playground to explore freely, or check back later.
                      </p>
                    </div>
                  </div>
                  <div className="z-10 mt-2">
                    <button
                      onClick={() => navigate('/student/playground')}
                      className="flex items-center justify-center gap-2 bg-[#f6f4ee] text-[#1800ad] px-8 py-3.5 rounded-full font-black text-xs hover:bg-white hover:scale-102 transition-all w-full sm:w-auto uppercase tracking-wider"
                    >
                      Open Playground
                      <ArrowRight size={14} />
                    </button>
                  </div>
                </motion.div>
              )}
            </section>

            {/* Right Column: Calendar */}
            <aside className="w-full flex flex-col h-fit xl:sticky xl:top-[20px] order-3 xl:order-2 shrink-0">
              <h2 className="text-xl font-bold text-[#1800ad] mb-4 xl:block">Learning Activity</h2>
              <div className="bg-[#f6f4ee] rounded-[32px] border-2 border-[#1800ad] p-6 lg:p-8 shadow-sm flex-1 flex flex-col justify-between">
                <div className="flex justify-between items-center mb-6">
                  <div>
                    <h3 className="text-lg font-bold text-[#1800ad]">Activity Journey</h3>
                    <p className="text-sm text-[#1800ad]/70 font-medium mt-1">This month</p>
                  </div>
                  <div className="flex gap-1 text-[#1800ad]">
                    <button onClick={handlePrevMonth} className="p-2 hover:bg-[#1800ad]/10 rounded-full transition-colors"><ChevronLeft size={20} /></button>
                    <button onClick={handleNextMonth} className="p-2 hover:bg-[#1800ad]/10 rounded-full transition-colors"><ChevronRight size={20} /></button>
                  </div>
                </div>

                {isLoadingCalendar ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="w-8 h-8 border-4 border-[#1800ad]/20 border-t-[#1800ad] rounded-full animate-spin"></div>
                  </div>
                ) : (
                  <div>
                    <div className="flex justify-between text-[10px] md:text-xs font-bold text-[#1800ad]/60 mb-2 uppercase px-1">
                      <span>{calendarDate.toLocaleString('default', { month: 'long', year: 'numeric' })}</span>
                    </div>
                    <div className="grid grid-cols-7 gap-1.5 md:gap-2">
                      {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((day, i) => (
                        <div key={i} className="text-center text-[10px] font-bold text-[#1800ad]/60 mb-1">{day}</div>
                      ))}
                      {calendarData.length === 0 ? (
                        // Fallback if no data (should not happen)
                        Array.from({ length: 35 }).map((_, i) => (
                          <div key={i} className="aspect-square bg-[#1800ad]/10 rounded-sm" />
                        ))
                      ) : (
                        calendarData.map((day, i) =>
                          day.value === -1 ? (
                            <div key={i} className="aspect-square" />
                          ) : (
                            <div
                              key={i}
                              title={day.value > 0 ? `${day.value} activities` : 'No activity'}
                              className={`aspect-square rounded-sm md:rounded-[4px] relative flex items-center justify-center ${getCellColor(day.value, day.date)} hover:ring-2 hover:ring-offset-1 hover:ring-[#1800ad]/50 transition-all cursor-pointer group/cell`}
                            >
                              <span className="text-[8px] sm:text-[10px] font-bold opacity-0 group-hover/cell:opacity-100 text-[#f6f4ee] bg-[#1800ad]/40 px-1 rounded-sm">{day.dayNumber}</span>
                            </div>
                          )
                        )
                      )}
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-end gap-2 mt-6 text-xs font-medium text-[#1800ad]/70">
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 rounded-[3px] bg-gray-300"></div>
                      <span>Upcoming</span>
                    </div>
                    <span>Less</span>
                    <div className="flex gap-1">
                      <div className="w-3 h-3 rounded-[3px] bg-[#1800ad]/10"></div>
                      <div className="w-3 h-3 rounded-[3px] bg-[#1800ad]/30"></div>
                      <div className="w-3 h-3 rounded-[3px] bg-[#1800ad]/50"></div>
                      <div className="w-3 h-3 rounded-[3px] bg-[#1800ad]/70"></div>
                      <div className="w-3 h-3 rounded-[3px] bg-[#1800ad]"></div>
                    </div>
                    <span>More</span>
                  </div>
                </div>
              </div>
            </aside>

            {/* Section: Upcoming Tasks summary */}
            <section className="order-2 xl:order-3 xl:col-start-1 xl:col-span-1">
              <h2 className="text-xl font-bold mb-4 text-[#1800ad]">
                Upcoming Tasks
                {readyAssignments.length > 0 && (
                  <span className="ml-2 text-sm font-semibold bg-[#1800ad] text-[#f6f4ee] px-2 py-0.5 rounded-full">
                    {readyAssignments.length}
                  </span>
                )}
              </h2>
              {isLoadingClasses || isLoadingAssignments ? (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[1, 2, 3, 4].map(i => (
                    <div key={i} className="p-4 md:p-5 rounded-3xl border-2 border-[#1800ad]/10 animate-pulse bg-[#1800ad]/5 h-[100px]"></div>
                  ))}
                </div>
              ) : readyAssignments.length === 0 ? (
                <div className="py-6 text-center text-[#1800ad]/50 font-semibold text-sm border-2 border-dashed border-[#1800ad]/20 rounded-3xl">
                  No tasks assigned yet.
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {readyAssignments.slice(0, 4).map(a => {
                    const cls = classes.find(c => c.class_id === a.class_id);
                    return (
                      <motion.div
                        key={a.assignment_id}
                        whileHover={{ y: -2 }}
                        onClick={() => {
                          if (['video', 'simulation', 'quiz', 'model', 'explain_ai', 'predict_ai', 'spot_it', 'connect_it', 'interactive_quiz', 'EXPLAIN_IT', 'PREDICT_IT', 'SPOT_IT', 'INTERACTIVE_QUIZ', 'explain_it', 'predict_it'].includes(a.assignment_type)) {
                            navigate(`/student/task/${a.assignment_id}?class_id=${a.class_id}`);
                          } else {
                            navigate(`/student/playground?assignment_id=${a.assignment_id}&class_id=${a.class_id}`);
                          }
                        }}
                        className="p-4 md:p-5 rounded-3xl border-2 border-[#1800ad]/20 bg-[#f6f4ee] text-[#1800ad] flex flex-col gap-2 cursor-pointer hover:border-[#1800ad] transition-colors group shadow-sm"
                      >
                        <span className="text-xs font-bold opacity-70 uppercase tracking-wider">{cls?.subject ?? 'Assignment'}</span>
                        <span className="text-sm font-black leading-tight line-clamp-2">{formatDisplayTitle(a.assignment_type, a.title)}</span>
                        <span className="text-[10px] font-bold px-2 py-0.5 bg-[#1800ad]/10 rounded-full w-fit">
                          {ASSIGNMENT_TYPE_LABELS[a.assignment_type] ?? a.assignment_type}
                        </span>
                      </motion.div>
                    );
                  })}
                </div>
              )}
              {readyAssignments.length > 4 && (
                <button
                  onClick={() => navigate('/student/tasks')}
                  className="mt-4 text-[#1800ad] font-bold text-sm hover:underline opacity-80 flex items-center gap-1"
                >
                  View all {readyAssignments.length} tasks <ArrowRight size={14} />
                </button>
              )}
            </section>

          </div>

          {/* Section: Continue Exploring */}
          <div className="mt-8 lg:mt-10">
            <section>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-[#1800ad]">Continue Exploring</h2>
                <button
                  onClick={() => navigate('/student/explore')}
                  className="text-[#1800ad] font-bold text-sm hover:underline opacity-80"
                >
                  View All
                </button>
              </div>
              {classes.length === 0 ? (
                <div className="py-6 text-center text-[#1800ad]/50 font-semibold text-sm border-2 border-dashed border-[#1800ad]/20 rounded-3xl">
                  Join a class to start exploring chapters.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-4">
                  {classes.slice(0, 3).map(cls => (
                    <motion.div
                      key={cls.class_id}
                      whileHover={{ y: -4 }}
                      onClick={() => navigate(`/student/playground?class_id=${cls.class_id}`)}
                      className="bg-[#1800ad] text-[#f6f4ee] p-6 rounded-[32px] flex flex-col justify-between gap-4 relative overflow-hidden group cursor-pointer shadow-lg border-2 border-[#1800ad] min-h-[160px]"
                    >
                      <div className="absolute -top-24 -right-24 w-64 h-64 bg-[#f6f4ee]/10 rounded-full blur-3xl pointer-events-none group-hover:scale-110 transition-transform duration-700"></div>
                      <div className="z-10">
                        <span className="text-[#f6f4ee]/70 font-semibold block tracking-wider uppercase text-xs mb-1">{cls.subject}</span>
                        <h3 className="text-lg font-bold text-[#f6f4ee] leading-tight">{cls.display_name}</h3>
                        <p className="text-[#f6f4ee]/60 text-xs mt-1">Grade {cls.grade}</p>
                      </div>
                      <div className="z-10 flex items-center justify-between">
                        <div className="flex items-center gap-1.5 text-[#f6f4ee]/80 text-xs font-bold">
                          <BookOpen size={14} />
                          Explore chapters
                        </div>
                        <ArrowRight size={16} className="text-[#f6f4ee]/60" />
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </section>
          </div>

        </div>
      </main>

      {/* MODAL: Join Classes */}
      <AnimatePresence>
        {isJoinModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-[#f6f4ee] border-2 border-[#1800ad] rounded-[32px] shadow-2xl p-6 md:p-8 max-w-md w-full font-montserrat text-[#1800ad] flex flex-col gap-4 relative max-h-[85vh] overflow-y-auto custom-scrollbar"
            >
              <button onClick={() => setIsJoinModalOpen(false)} className="absolute top-5 right-5 hover:opacity-75 transition-opacity">
                <X size={20} />
              </button>

              <h2 className="text-xl md:text-2xl font-black text-center uppercase tracking-wide">Join Your Classes</h2>
              <p className="text-xs text-[#1800ad]/70 font-semibold text-center -mt-2">Enter the class codes provided by your teacher</p>

              <div className="flex flex-col gap-2.5 mt-2">
                {joinClassCodes.map((codeItem, index) => (
                  <div key={index} className="flex flex-col gap-1 w-full shrink-0">
                    <input
                      type="text"
                      placeholder={`Class Code ${index + 1}`}
                      value={codeItem.value}
                      onChange={(e) => handleClassCodeChange(index, e.target.value)}
                      disabled={isJoining}
                      className="w-full px-6 py-2.5 text-sm bg-transparent border border-[#1800ad] rounded-full text-center text-[#2c2c2c] placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-[#1800ad] font-montserrat"
                    />
                    {codeItem.error && (
                      <span className="text-[10px] text-red-600 font-bold text-center px-2">{codeItem.error}</span>
                    )}
                  </div>
                ))}
                <button
                  type="button"
                  onClick={addClassCodeField}
                  disabled={isJoining}
                  className="w-full py-3.5 border-2 border-dashed border-[#1800ad]/40 text-[#1800ad] hover:border-[#1800ad] rounded-full font-black text-sm transition-all flex items-center justify-center gap-1.5 mt-1 shrink-0"
                >
                  + Add another class
                </button>
              </div>

              <div className="flex gap-3 mt-4">
                <button
                  type="button"
                  onClick={() => setIsJoinModalOpen(false)}
                  className="w-1/2 py-3 bg-transparent border-2 border-[#1800ad] hover:bg-[#1800ad]/5 font-bold rounded-full text-center text-sm"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleJoinClasses}
                  disabled={isJoining}
                  className="w-1/2 py-3 bg-[#1800ad] border-2 border-[#1800ad] hover:bg-[#f6f4ee] text-[#f6f4ee] hover:text-[#1800ad] font-bold rounded-full text-center text-sm disabled:opacity-50"
                >
                  {isJoining ? 'Joining...' : 'Join Classes'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* MODAL: Class Chapters List */}
      <AnimatePresence>
        {selectedClass && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-[#f6f4ee] border-2 border-[#1800ad] rounded-[32px] shadow-2xl p-6 md:p-8 max-w-lg w-full font-montserrat text-[#1800ad] flex flex-col gap-4 relative max-h-[85vh]"
            >
              <button onClick={() => setSelectedClass(null)} className="absolute top-5 right-5 hover:opacity-75 transition-opacity">
                <X size={20} />
              </button>

              <div>
                <span className="text-[10px] font-bold opacity-60 uppercase tracking-wider block mb-0.5">{selectedClass.subject} • Grade {selectedClass.grade}</span>
                <h2 className="text-xl md:text-2xl font-black">{selectedClass.display_name}</h2>
              </div>

              <div className="flex-1 overflow-y-auto custom-scrollbar flex flex-col gap-3.5 my-2 pr-1 min-h-[180px]">
                {isLoadingChapters ? (
                  <div className="m-auto flex flex-col items-center gap-3 py-8">
                    <div className="w-8 h-8 border-4 border-[#1800ad]/20 border-t-[#1800ad] rounded-full animate-spin"></div>
                    <span className="text-xs font-bold text-[#1800ad]/60 animate-pulse">Loading chapters...</span>
                  </div>
                ) : classChapters.length === 0 ? (
                  <div className="m-auto text-center py-8 text-[#1800ad]/60 font-semibold text-sm leading-relaxed max-w-[80%]">
                    Your teacher hasn't set up this class yet
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pb-2">
                    {classChapters.map((chapter, index) => (
                      <motion.div
                        key={chapter.chapter_id}
                        initial={{ opacity: 0, scale: 0.97 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.2, delay: index * 0.03 }}
                        onClick={() => {
                          setSelectedClass(null);
                          navigate(`/student/playground?class_id=${selectedClass.class_id}&chapter_id=${chapter.chapter_id}`);
                        }}
                        className="h-[148px] bg-[#1800ad] text-[#f6f4ee] p-5 rounded-[22px] border-[2px] border-[#1800ad] flex flex-col justify-between relative overflow-hidden cursor-pointer hover:opacity-90 transition-opacity"
                      >
                        <div className="flex justify-between items-center">
                          <span className="text-[10px] font-black uppercase tracking-wider text-[#f6f4ee]/80">
                            Chapter {chapter.sequence_number}
                          </span>
                          <span className="text-[11px] font-semibold text-[#f6f4ee]/90 flex items-center gap-1 bg-[#f6f4ee]/15 px-2 py-0.5 rounded-full">
                            {chapter.asset_count} Assets
                          </span>
                        </div>
                        <div className="my-1.5">
                          <h3 className="text-[14px] sm:text-[15px] font-extrabold leading-snug tracking-tight text-[#f6f4ee] line-clamp-2">
                            {chapter.title}
                          </h3>
                        </div>
                        <div className="border-t border-[#f6f4ee]/15 pt-2 flex items-center justify-between text-[10px] font-bold">
                          <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider ${
                            chapter.status === 'data_ready' ? 'bg-emerald-400/20 text-emerald-300 border border-emerald-400/30' :
                            chapter.status === 'active' ? 'bg-blue-400/20 text-blue-300 border border-blue-400/30' :
                            chapter.status === 'generated' ? 'bg-amber-400/20 text-amber-300 border border-amber-400/30' :
                            'bg-[#f6f4ee]/15 text-[#f6f4ee]/80 border border-[#f6f4ee]/20'
                          }`}>
                            {chapter.status}
                          </span>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                )}
              </div>

              <div className="mt-auto">
                <button
                  onClick={() => setSelectedClass(null)}
                  className="w-full py-3 bg-[#1800ad] border-2 border-[#1800ad] hover:bg-[#f6f4ee] text-[#f6f4ee] hover:text-[#1800ad] font-bold rounded-full text-center text-sm transition-all"
                >
                  Close
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
      {/* MODAL: Logout Confirmation */}
      <LogoutModal isOpen={isLogoutModalOpen} onClose={() => setIsLogoutModalOpen(false)} />

    </div>
  );
}