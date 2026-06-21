import React, { useState, useEffect, useRef } from 'react';
import { 
  LayoutDashboard, 
  BookOpen,
  BarChart2,
  MessageSquare,
  Search, 
  Copy,
  Check,
  TrendingDown,
  BookMarked,
  ChevronDown
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useNavigate } from 'react-router-dom';
import { ChatbotFab } from '../components/ChatbotFab';
import { NavItem } from '../components/NavItem';
import { LogoutModal } from '../components/LogoutModal';
import { 
  getStoredTasks, 
  getPlaygroundQuota, 
  getTeacherAssignedNew, 
  completeAllTasks, 
  resetAllTasks, 
  setTeacherAssignedNew 
} from '../data/taskStore';
import { api } from '../lib/api';
import { getTranslationLanguage, setTranslationLanguage } from '../lib/translation';

export function TeacherDashboardPage() {
  const navigate = useNavigate();

  // Load profile state
  const [profile, setProfile] = useState<any>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [copiedToast, setCopiedToast] = useState<string | null>(null);
  const [classes, setClasses] = useState<any[]>([]);
  const [teacherName, setTeacherName] = useState<string>('Teacher');

  const [isLangDropdownOpen, setIsLangDropdownOpen] = useState(false);
  const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);
  const [expandedCodeDropdown, setExpandedCodeDropdown] = useState<string | null>(null);
  const langDropdownRef = useRef<HTMLDivElement>(null);
  const codeDropdownRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (langDropdownRef.current && !langDropdownRef.current.contains(event.target as Node)) {
        setIsLangDropdownOpen(false);
      }
      if (expandedCodeDropdown) {
        const ref = codeDropdownRefs.current[expandedCodeDropdown];
        if (ref && !ref.contains(event.target as Node)) {
          setExpandedCodeDropdown(null);
        }
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [expandedCodeDropdown]);

  const handleLanguageChange = async (langCode: string) => {
    try {
      const dbLang = langCode === 'hi' ? 'hindi' : 'english';
      await api.post('/teachers/onboarding/preferences', { preferred_language: dbLang });
    } catch (err) {
      console.error("Failed to save language preference:", err);
    }
    setTranslationLanguage(langCode);
  };
  const [classAnalytics, setClassAnalytics] = useState<Record<string, any>>({});

  useEffect(() => {
    const data = localStorage.getItem('mootion_teacher_setup');
    if (data) {
      setProfile(JSON.parse(data));
    }
  }, []);

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
    const fetchClasses = async () => {
      try {
        const data = await api.get('/teachers/classes');
        setClasses(data);
        if (data.length > 0 && !localStorage.getItem('mootion_last_class_id')) {
          localStorage.setItem('mootion_last_class_id', data[0].class_id);
        }
      } catch (err: any) {
        console.error("Failed to fetch teacher classes:", err);
        if (err.status === 403 || err.status === 401) {
          localStorage.removeItem('mootion_access_token');
          localStorage.removeItem('mootion_refresh_token');
          navigate('/teacher/login');
        }
      }
    };
    fetchClasses();
  }, []);

  useEffect(() => {
    if (classes.length === 0) return;
    const fetchAnalytics = async () => {
      const analyticsMap: Record<string, any> = {};
      await Promise.all(
        classes.map(async (c) => {
          try {
            const data = await api.get(`/teachers/classes/${c.class_id}/analytics/overview`);
            analyticsMap[c.class_id] = data;
          } catch (err) {
            console.error(`Failed to fetch analytics for class ${c.class_id}:`, err);
          }
        })
      );
      setClassAnalytics(analyticsMap);
    };
    fetchAnalytics();
  }, [classes]);

  // Helper to sort grades numerically
  const getGradeNum = (g: string) => {
    const match = g.match(/\d+/);
    return match ? parseInt(match[0], 10) : 999;
  };

  // Group classes by grade
  const groupedClasses = React.useMemo(() => {
    const groups: Record<string, any[]> = {};
    classes.forEach(c => {
      const gradeLabel = c.grade.toLowerCase().includes('class') ? c.grade : `Class ${c.grade}`;
      if (!groups[gradeLabel]) {
        groups[gradeLabel] = [];
      }
      groups[gradeLabel].push(c);
    });
    return groups;
  }, [classes]);

  const sortedGrades = Object.keys(groupedClasses).sort((a, b) => getGradeNum(a) - getGradeNum(b));

  const handleCopyInviteCode = (e: React.MouseEvent, code: string, cardId: string) => {
    e.stopPropagation(); // Stop navigation click
    if (code === 'Loading...') return;
    navigator.clipboard.writeText(code);
    setCopiedId(cardId);
    setCopiedToast(`Class code ${code} copied!`);
    setTimeout(() => {
      setCopiedId(null);
    }, 2000);
    setTimeout(() => {
      setCopiedToast(null);
    }, 3500);
  };

  const handleClassroomNav = () => {
    const lastClassId = localStorage.getItem('mootion_last_class_id');
    if (lastClassId) {
      navigate(`/teacher/class/${lastClassId}`);
      return;
    }
    if (classes && classes.length > 0) {
      const firstClass = classes[0];
      navigate(`/teacher/class/${firstClass.class_id}`);
    } else {
      navigate('/teacher/class/class-8-science');
    }
  };

  const handleAnalyticsNav = () => {
    if (classes && classes.length > 0) {
      const firstClass = classes[0];
      navigate(`/teacher/analytics/${firstClass.class_id || firstClass.id}`);
    } else {
      navigate('/teacher/analytics');
    }
  };

  const getSubjectsForGradeCard = (gradeName: string, allSubjects: string[]) => {
    const num = getGradeNum(gradeName);
    if (num >= 5 && num <= 10) {
      const list: string[] = [];
      const hasScience = allSubjects.some(s => ['physics', 'chemistry', 'biology', 'science'].includes(s.toLowerCase()));
      if (hasScience) list.push('Science');
      if (allSubjects.some(s => s.toLowerCase() === 'mathematics')) list.push('Mathematics');
      return list;
    } else {
      return allSubjects.filter(s => s.toLowerCase() !== 'science');
    }
  };
  return (
    <div className="flex flex-1 w-full bg-[#1800ad] font-montserrat text-[#1800ad] relative">
      
      {/* Mobile Bottom Navigation Bar */}
      <nav className="md:hidden fixed bottom-4 left-4 right-4 bg-[#1800ad] px-6 py-2 flex justify-between items-center z-40 rounded-full shadow-[0_10px_40px_rgba(24,0,173,0.25)] border-[2px] border-[#f6f4ee]">
        <NavItem icon={<LayoutDashboard size={22} />} active onClick={() => navigate('/teacher/home')} />
        <NavItem icon={<BookOpen size={22} />} onClick={handleClassroomNav} />
        <NavItem icon={<BarChart2 size={22} />} onClick={handleAnalyticsNav} />
        <NavItem icon={<MessageSquare size={22} />} onClick={() => navigate('/teacher/doubts')} />
        <div 
          onClick={() => setIsLogoutModalOpen(true)}
          className="shrink-0 cursor-pointer flex items-center justify-center w-8 h-8 rounded-full border border-[#f6f4ee] bg-[#f6f4ee] hover:opacity-90 transition-opacity"
        >
          <span className="text-[#1800ad] font-bold text-xs">
            {teacherName ? teacherName[0].toUpperCase() : 'T'}
          </span>
        </div>
      </nav>

      {/* Floating Copied Toast Notification */}
      <AnimatePresence>
        {copiedToast && (
          <motion.div 
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 25 }}
            className="fixed bottom-24 sm:bottom-8 right-6 z-50 bg-[#1800ad] text-[#f6f4ee] px-6 py-3.5 rounded-2xl shadow-xl flex items-center gap-2.5 border-2 border-[#f6f4ee] font-bold text-xs sm:text-sm tracking-wide lowercase"
          >
            <Check size={16} className="text-[#f6f4ee] stroke-[3]" />
            <span>{copiedToast}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ChatBot FAB */}
      <ChatbotFab />

      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex w-[80px] lg:w-[100px] flex-col items-center justify-between py-8 fixed top-0 bottom-0 left-0 h-full shrink-0 bg-[#1800ad] text-[#f6f4ee] z-30">
        {/* Logo */}
        <div className="flex items-center justify-center shrink-0 mt-4 cursor-pointer" onClick={() => navigate('/teacher/home')}>
          <span className="text-[#f6f4ee] font-val text-[42px] leading-none tracking-widest mt-1 mr-1 notranslate">M</span>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-6 w-full items-center my-auto">
          <NavItem icon={<LayoutDashboard size={24} />} active onClick={() => navigate('/teacher/home')} />
          <NavItem icon={<BookOpen size={24} />} onClick={handleClassroomNav} />
          <NavItem icon={<BarChart2 size={24} />} onClick={handleAnalyticsNav} />
          <NavItem icon={<MessageSquare size={24} />} onClick={() => navigate('/teacher/doubts')} />
        </nav>

        {/* Profile Avatar */}
        <div onClick={() => setIsLogoutModalOpen(true)} className="shrink-0 cursor-pointer flex items-center justify-center group w-12 h-12 rounded-full border-2 border-[#1800ad] bg-[#f6f4ee] hover:opacity-90 transition-opacity duration-300 shadow-sm relative">
           <span className="text-[#1800ad] font-bold text-lg transition-colors duration-300">
             {teacherName ? teacherName[0].toUpperCase() : 'T'}
           </span>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 md:ml-[80px] lg:ml-[100px] bg-[#f6f4ee] md:rounded-l-[40px] lg:rounded-l-[50px] p-5 pb-32 lg:pb-12 md:pl-10 lg:pl-12 xl:pl-16 md:pr-8 lg:pr-10 w-full relative flex flex-col min-h-[100dvh]">
        <div className="max-w-[1300px] w-full mx-auto">
        
        {/* Top Header */}
        <header className="flex flex-col xl:flex-row xl:justify-between xl:items-end gap-6 mb-8 lg:mb-10 w-full relative">
          <div className="flex flex-col gap-2">
            <h1 className="text-3xl md:text-3xl lg:text-4xl font-bold tracking-tight text-[#1800ad]">
              Welcome Back, {teacherName} 👋
            </h1>
            <div className="flex flex-wrap items-center gap-3 mt-1">
              <p className="text-[#1800ad]/70 font-medium">Coordinate your students and assign interactive modules effortlessly.</p>
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
                placeholder="Search your lectures..." 
                className="w-full pl-12 pr-4 py-3 md:py-3.5 bg-transparent border-2 border-[#1800ad]/30 rounded-full text-sm outline-none focus:border-[#1800ad] focus:ring-4 focus:ring-[#1800ad]/10 transition-all placeholder:text-[#1800ad]/50 font-medium text-[#1800ad]"
              />
            </div>
          </div>
        </header>

        <div className="flex flex-col xl:grid xl:grid-cols-[1fr_390px] gap-8 lg:gap-10">
          
          {/* Left Column: Classroom Portals */}
          <section className="flex flex-col order-1 gap-6">
            <div>
              <h2 className="text-2xl font-black text-[#1800ad] tracking-tight uppercase">My Classrooms</h2>
              <p className="text-xs font-semibold text-[#1800ad]/60 leading-normal mt-0.5">
                {classes.length === 1
                  ? `Share your ${classes[0].grade.toLowerCase().includes('class') ? classes[0].grade : `Class ${classes[0].grade}`} ${classes[0].subject.charAt(0).toUpperCase() + classes[0].subject.slice(1)} code with your students to connect with them`
                  : "Share the code with your students and connect with them"}
              </p>
            </div>

            <div className="flex flex-col gap-8 flex-1">
              {classes.length === 0 ? (
                <div className="text-center p-8 bg-[#1800ad]/5 rounded-[32px] border-2 border-dashed border-[#1800ad]/15">
                  <p className="font-bold text-[#1800ad]/60">No classes configured yet.</p>
                </div>
              ) : (
                sortedGrades.map((grade) => {
                  const gradeClasses = groupedClasses[grade] || [];
                  const classCodes = gradeClasses.map(c => c.class_code).join(' / ');
                  const isClassCopied = copiedId === grade;

                  return (
                    <div key={grade} className="flex flex-col gap-3.5 bg-[#1800ad]/5 p-5 sm:p-6 rounded-[32px] border-2 border-[#1800ad]/15">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b-2 border-[#1800ad]/10 pb-3">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-[#1800ad] text-[#f6f4ee] flex items-center justify-center font-bold text-xs sm:text-sm">
                            {getGradeNum(grade) !== 999 ? getGradeNum(grade) : '★'}
                          </div>
                          <span className="text-lg font-extrabold text-[#1800ad]">{grade}</span>
                        </div>
                        
                        <div className="flex items-center flex-wrap gap-2.5">
                          {gradeClasses.length > 1 ? (
                            <div
                              className="relative"
                              ref={(el) => { codeDropdownRefs.current[grade] = el; }}
                            >
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setExpandedCodeDropdown(
                                    expandedCodeDropdown === grade ? null : grade
                                  );
                                }}
                                className={`flex items-center gap-1.5 px-3 py-1 rounded-full border-[2px] text-[11px] font-extrabold tracking-wide transition-all bg-transparent text-[#1800ad] border-[#1800ad]/30 hover:border-[#1800ad]`}
                                title="Click to view class invitation codes"
                              >
                                <span className="uppercase tracking-wider">Codes</span>
                                <ChevronDown
                                  size={11}
                                  className={`transition-transform duration-300 ${
                                    expandedCodeDropdown === grade ? 'rotate-180' : ''
                                  }`}
                                />
                              </button>

                              <AnimatePresence>
                                {expandedCodeDropdown === grade && (
                                  <motion.div
                                    initial={{ opacity: 0, y: 8, scale: 0.95 }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    exit={{ opacity: 0, y: 8, scale: 0.95 }}
                                    transition={{ duration: 0.15 }}
                                    className="absolute left-0 sm:left-auto sm:right-0 top-full mt-2 w-max min-w-[200px] max-w-[calc(100vw-32px)] bg-[#f6f4ee] border-2 border-[#1800ad] rounded-2xl shadow-xl overflow-hidden flex flex-col py-1.5 z-[60]"
                                  >
                                    {gradeClasses.map((cls) => {
                                      const isRowCopied = copiedId === `${grade}-${cls.class_id}`;
                                      const formattedSubj = cls.subject.charAt(0).toUpperCase() + cls.subject.slice(1);
                                      return (
                                        <div
                                          key={cls.class_id}
                                          className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-1 sm:gap-4 px-4 py-2 hover:bg-[#1800ad]/5 transition-colors cursor-pointer"
                                          onClick={(e) => {
                                            handleCopyInviteCode(e, cls.class_code, `${grade}-${cls.class_id}`);
                                          }}
                                        >
                                          <span className="text-xs font-bold text-[#1800ad]/70">
                                            {formattedSubj}
                                          </span>
                                          <div className="flex items-center gap-2">
                                            <span className="text-xs font-mono font-extrabold text-[#1800ad] uppercase tracking-wider">
                                              {cls.class_code}
                                            </span>
                                            {isRowCopied ? (
                                              <Check size={12} className="text-[#1800ad] stroke-[3]" />
                                            ) : (
                                              <Copy size={12} className="text-[#1800ad]/50 hover:text-[#1800ad] transition-colors" />
                                            )}
                                          </div>
                                        </div>
                                      );
                                    })}
                                  </motion.div>
                                )}
                              </AnimatePresence>
                            </div>
                          ) : (
                            <button
                              type="button"
                              onClick={(e) => handleCopyInviteCode(e, classCodes, grade)}
                              className={`flex items-center gap-1.5 px-3 py-1 rounded-full border-[2px] text-[11px] font-extrabold tracking-wide transition-all ${
                                isClassCopied 
                                  ? 'bg-[#1800ad] text-[#f6f4ee] border-[#1800ad] scale-102' 
                                  : 'bg-transparent text-[#1800ad] border-[#1800ad]/30 hover:border-[#1800ad]'
                              }`}
                              title="Click to copy class invitation code"
                            >
                              <span className="opacity-70">code:</span>
                              <span className="font-mono uppercase tracking-wider">{classCodes}</span>
                              {isClassCopied ? <Check size={11} className="stroke-[3]" /> : <Copy size={11} />}
                            </button>
                          )}

                          <div className="text-[10px] sm:text-xs font-bold text-[#1800ad]/70 bg-[#1800ad]/10 px-3 py-1 rounded-full uppercase tracking-wider">
                            {gradeClasses.length} Subjects
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {gradeClasses.map((cls) => {
                          const formattedSubject = cls.subject.charAt(0).toUpperCase() + cls.subject.slice(1);
                          return (
                            <motion.div
                              key={cls.class_id}
                              whileHover={{ y: -4 }}
                              onClick={() => navigate(`/teacher/class/${cls.grade.toLowerCase().replace(/\s+/g, '-')}-${cls.subject.toLowerCase().replace(/\s+/g, '-')}`)}
                              className="bg-[#f6f4ee] border-2 border-[#1800ad]/20 hover:border-[#1800ad] p-4.5 rounded-[24px] flex flex-col justify-between gap-4 cursor-pointer shadow-sm relative overflow-hidden group hover:shadow-md transition-all duration-300"
                            >
                              {/* Class and Subject Name */}
                              <div className="relative z-10">
                                <h4 className="text-xs font-semibold text-[#1800ad]/60 uppercase tracking-wider">
                                  {grade}
                                </h4>
                                <h3 className="text-lg font-black text-[#1800ad] leading-tight mt-1">
                                  {formattedSubject}
                                </h3>
                              </div>

                              {/* Card footer details with non-underlined, simple rename info */}
                              <div className="flex items-center justify-between text-[10px] font-bold text-[#1800ad]/60 mt-2 border-t border-[#1800ad]/10 pt-2 relative z-10">
                                <span className="flex items-center gap-1">
                                  <BookMarked size={12} />
                                  NCERT loaded
                                </span>
                                <span className="text-[#1800ad]/90 flex items-center gap-0.5">
                                  Syllabus &rarr;
                                </span>
                              </div>

                              {/* Card Background subtle grid texture */}
                              <div className="absolute inset-x-0 bottom-0 top-[60%] bg-gradient-to-t from-[#1800ad]/3 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none duration-300"></div>
                            </motion.div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </section>

          {/* Right Column (Notifications/State Indicators) */}
          <aside className="w-full flex flex-col h-fit xl:sticky xl:top-[20px] order-2 shrink-0 gap-6">
            
            {/* Notifications: Class Content Completions */}
            <div>
              <h2 className="text-xl font-bold text-[#1800ad]">Class Content Completed</h2>
              <p className="text-xs font-medium text-[#1800ad]/60 lowercase mt-0.5">Real-time student progress percentages per grade.</p>
            </div>

            <div className="bg-[#f6f4ee] rounded-[32px] border-2 border-[#1800ad] p-5 lg:p-6 shadow-sm flex flex-col gap-4">
              <div className="flex flex-col gap-4">
                {classes.length === 0 ? (
                  <p className="text-xs font-bold text-[#1800ad]/50 text-center">No progress data.</p>
                ) : (
                  classes.map((cls) => {
                    const analytics = classAnalytics[cls.class_id];
                    const progress = analytics ? analytics.task_completion_rate : 0;
                    
                    return (
                      <div key={cls.class_id} className="flex flex-col gap-2">
                        <div className="flex items-between justify-between text-xs font-black">
                          <span className="uppercase tracking-wide text-[#1800ad] truncate max-w-[200px]">
                            Class {cls.grade} • {cls.subject}
                          </span>
                          <span className="bg-[#1800ad] text-[#f6f4ee] font-mono px-2 py-0.5 rounded-full text-[10px] shrink-0">
                            {progress}% done
                          </span>
                        </div>
                        
                        {/* Bar Container */}
                        <div className="w-full bg-[#1800ad]/10 h-3 rounded-full overflow-hidden border border-[#1800ad]/5 relative">
                          <motion.div 
                            initial={{ width: 0 }}
                            animate={{ width: `${progress}%` }}
                            transition={{ duration: 1.2, ease: "easeOut" }}
                            className={`h-full rounded-full ${
                              progress >= 80 
                                ? 'bg-[#1800ad]' 
                                : progress >= 40 
                                  ? 'bg-[#1800ad]/75' 
                                  : 'bg-[#1800ad]/50'
                            }`}
                          />
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Student Struggle Radar & Struggling Concepts */}
            <div>
              <h2 className="text-xl font-bold text-[#1800ad]">Student Struggle Radar</h2>
              <p className="text-xs font-medium text-[#1800ad]/60 lowercase mt-0.5">Lowest scoring concepts identified automatically by Mootion AI.</p>
            </div>

            <div className="bg-[#f6f4ee] rounded-[32px] border-2 border-[#1800ad] p-5 lg:p-6 shadow-sm flex flex-col gap-3.5">
              <div className="flex flex-col gap-3">
                {classes.length === 0 ? (
                  <p className="text-xs font-bold text-[#1800ad]/50 text-center">No struggle radar data.</p>
                ) : (
                  classes.map((cls) => {
                    const analytics = classAnalytics[cls.class_id];
                    const misconception = analytics?.most_common_misconception;
                    const score = analytics?.average_scores 
                      ? Math.round(((analytics.average_scores.understanding + analytics.average_scores.reasoning + analytics.average_scores.expression) / 9) * 100)
                      : 100;
                    
                    return (
                      <div key={cls.class_id} className="p-3.5 rounded-2xl bg-white border border-[#1800ad]/10 flex flex-col gap-1.5 hover:border-[#1800ad]/30 transition-colors">
                        <div className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1">
                          <span className="text-[9px] font-black uppercase text-[#1800ad]/55 tracking-widest leading-none">
                            Class {cls.grade} • {cls.subject}
                          </span>
                          <div className="flex items-center gap-1 shrink-0">
                            <TrendingDown size={11} className="text-[#1800ad]/70" />
                            <span className="text-[10px] font-bold text-[#1800ad]/80 font-mono">
                              {score}% accuracy
                            </span>
                          </div>
                        </div>
                        {misconception && misconception !== "No struggle areas detected yet." && misconception !== "No submissions yet." ? (
                          <>
                            <span className="text-[9px] font-black uppercase text-amber-600/80 tracking-wider">Latest gap identified</span>
                            <p className="text-xs font-semibold text-[#121212] leading-snug line-clamp-3">{misconception}</p>
                          </>
                        ) : (
                          <p className="text-xs font-bold text-[#1800ad]/40 leading-snug italic">No struggle areas detected yet.</p>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>

          </aside>

        </div>
      </div>
    </main>

      {/* MODAL: Logout Confirmation */}
      <LogoutModal isOpen={isLogoutModalOpen} onClose={() => setIsLogoutModalOpen(false)} />

    </div>
  );
}
