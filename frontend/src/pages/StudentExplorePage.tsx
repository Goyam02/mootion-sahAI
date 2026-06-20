import React, { useState, useEffect, useCallback } from 'react';
import {
  LayoutDashboard,
  CheckSquare,
  Compass,
  Gamepad2,
  Search,
  ChevronRight,
  BookOpen,
  Atom,
  FlaskConical,
  Calculator,
  Leaf,
  Monitor,
  BarChart2
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { NavItem } from '../components/NavItem';
import { ChatbotFab } from '../components/ChatbotFab';

// ─── Types ────────────────────────────────────────────────────────────────

interface StudentClass {
  class_id: string;
  class_code: string;
  display_name: string;
  grade: string;
  subject: string;
}

interface Chapter {
  chapter_id: string;
  class_id: string;
  sequence_number: number;
  title: string;
  status: string;
  asset_count: number;
}

type ChapterWithClass = Chapter & { subject: string; class_id: string };

// ─── Component ────────────────────────────────────────────────────────────

export function StudentExplorePage() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');

  const [classes, setClasses] = useState<StudentClass[]>([]);
  const [chaptersByClass, setChaptersByClass] = useState<Record<string, Chapter[]>>({});
  const [isLoadingClasses, setIsLoadingClasses] = useState(true);
  const [isLoadingChapters, setIsLoadingChapters] = useState(false);
  const [studentName, setStudentName] = useState<string>('');
  const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);

  useEffect(() => {
    api.get('/students/me').then((me: any) => {
      if (me?.full_name) {
        const firstName = me.full_name.split(' ')[0];
        setStudentName(firstName);
      }
    }).catch(() => {});
  }, []);

  // ── Fetch classes then chapters ──
  const loadData = useCallback(async () => {
    setIsLoadingClasses(true);
    try {
      const classData: StudentClass[] = await api.get('/students/classes');
      setClasses(classData);

      if (classData.length > 0) {
        setIsLoadingChapters(true);
        const chapterResults = await Promise.allSettled(
          classData.map(cls =>
            api.get(`/teachers/classes/${cls.class_id}/chapters`).then((chs: Chapter[]) => ({
              class_id: cls.class_id,
              chapters: chs,
            }))
          )
        );
        const byClass: Record<string, Chapter[]> = {};
        chapterResults.forEach(r => {
          if (r.status === 'fulfilled') {
            byClass[r.value.class_id] = r.value.chapters.sort(
              (a, b) => a.sequence_number - b.sequence_number
            );
          }
        });
        setChaptersByClass(byClass);
        setIsLoadingChapters(false);
      }
    } catch (err: any) {
      console.error('Failed to load explore data:', err);
    } finally {
      setIsLoadingClasses(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ── Filtered chapters grouped by subject ──
  const filteredGroups: { cls: StudentClass; chapters: Chapter[] }[] = classes.map(cls => {
    const chapters = (chaptersByClass[cls.class_id] ?? []).filter(ch => {
      if (!searchQuery) return true;
      const q = searchQuery.toLowerCase();
      return ch.title.toLowerCase().includes(q) || cls.subject.toLowerCase().includes(q);
    });
    return { cls, chapters };
  }).filter(g => g.chapters.length > 0);

  return (
    <div className="flex flex-1 w-full h-[100dvh] bg-[#1800ad] font-montserrat text-[#1800ad] overflow-hidden relative">
      <ChatbotFab context="User is browsing the Chapter Learning catalog on the Explore page." />

      {/* Mobile Bottom Navigation Bar */}
      <nav className="md:hidden fixed bottom-4 left-4 right-4 bg-[#1800ad] px-6 py-2 flex justify-between items-center z-40 rounded-full shadow-[0_10px_40px_rgba(24,0,173,0.25)] border-[2px] border-[#f6f4ee]">
        <NavItem icon={<LayoutDashboard size={22} />} onClick={() => navigate('/student/home')} />
        <NavItem icon={<CheckSquare size={22} />} onClick={() => navigate('/student/tasks')} />
        <NavItem icon={<Compass size={22} />} active onClick={() => navigate('/student/explore')} />
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

      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex w-[80px] lg:w-[100px] flex-col items-center justify-between py-8 fixed top-0 bottom-0 left-0 h-full shrink-0 bg-[#1800ad] text-[#f6f4ee] z-30">
        <div className="flex items-center justify-center shrink-0 mt-4 cursor-pointer" onClick={() => navigate('/student/home')}>
          <span className="text-[#f6f4ee] font-val text-[42px] leading-none tracking-widest mt-1 mr-1 notranslate">M</span>
        </div>
        <nav className="flex flex-col gap-6 w-full items-center my-auto">
          <NavItem icon={<LayoutDashboard size={24} />} onClick={() => navigate('/student/home')} />
          <NavItem icon={<CheckSquare size={24} />} onClick={() => navigate('/student/tasks')} />
          <NavItem icon={<Compass size={24} />} active onClick={() => navigate('/student/explore')} />
          <NavItem icon={<Gamepad2 size={24} />} onClick={() => navigate('/student/playground')} />
          <NavItem icon={<BarChart2 size={24} />} onClick={() => navigate('/student/analytics')} />
        </nav>
        <div onClick={() => setIsLogoutModalOpen(true)} className="shrink-0 cursor-pointer flex items-center justify-center group w-12 h-12 rounded-full border-2 border-[#1800ad] bg-[#f6f4ee] relative">
          <span className="text-[#1800ad] font-bold text-lg">{studentName ? studentName[0].toUpperCase() : 'S'}</span>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 md:ml-[80px] lg:ml-[100px] bg-[#f6f4ee] md:rounded-l-[40px] lg:rounded-l-[50px] p-5 md:pl-10 lg:pl-12 xl:pl-16 md:pr-8 lg:pr-10 w-full overflow-y-auto custom-scrollbar pt-6 md:pt-10 pb-32 lg:pb-12 relative flex flex-col h-[100dvh]">
        <div className="max-w-[1300px] w-full h-full flex flex-col">

          {/* Header */}
          <header className="flex flex-col xl:flex-row xl:justify-between xl:items-end gap-6 mb-8 lg:mb-10 w-full relative">
            <div className="flex flex-col gap-2">
              <h1 className="text-3xl md:text-3xl lg:text-4xl font-extrabold tracking-tight text-[#1800ad]">Explore</h1>
              <p className="text-[#1800ad]/70 font-semibold mt-1">Browse all chapters assigned by your teacher.</p>
            </div>
            <div className="relative w-[calc(100%+16px)] -ml-2 translate-y-1.5 xl:translate-y-0 xl:ml-0 xl:w-[380px]">
              <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
                <Search size={18} className="text-[#1800ad]/60" />
              </div>
              <input
                type="text"
                placeholder="Search chapters and topics..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full pl-12 pr-4 py-3 md:py-3.5 bg-transparent border-2 border-[#1800ad]/30 rounded-full text-sm outline-none focus:border-[#1800ad] focus:ring-4 focus:ring-[#1800ad]/10 transition-all placeholder:text-[#1800ad]/50 font-semibold text-[#1800ad]"
              />
            </div>
          </header>

          {/* Chapters by Subject */}
          {isLoadingClasses ? (
            <div className="flex flex-col gap-12">
              {[1, 2].map(s => (
                <section key={s} className="flex flex-col gap-5">
                  <div className="h-8 w-48 bg-[#1800ad]/10 rounded-full animate-pulse"></div>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {[1, 2, 3].map(i => (
                      <div key={i} className="h-72 rounded-[40px] bg-[#1800ad]/10 animate-pulse border-2 border-[#1800ad]/10"></div>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          ) : classes.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center opacity-60 pt-12 pb-16">
              <BookOpen size={64} className="text-[#1800ad] mb-4 opacity-50" />
              <h3 className="text-xl font-bold text-[#1800ad]">No classes yet</h3>
              <p className="text-[#1800ad] mt-1">Join a class on the home page to start exploring.</p>
            </div>
          ) : (
            <div className="flex flex-col gap-12 pb-10 flex-1">
              {/* If loading chapters for the first time */}
              {isLoadingChapters && classes.every(c => !chaptersByClass[c.class_id]) ? (
                <div className="py-16 flex items-center justify-center gap-3 flex-1">
                  <div className="w-8 h-8 border-4 border-[#1800ad]/20 border-t-[#1800ad] rounded-full animate-spin"></div>
                  <span className="text-sm font-bold text-[#1800ad]/60 animate-pulse">Loading chapters...</span>
                </div>
              ) : filteredGroups.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center opacity-60 pt-12 pb-16">
                  <BookOpen size={64} className="text-[#1800ad] mb-4 opacity-50" />
                  <h3 className="text-xl font-bold text-[#1800ad]">No chapters found</h3>
                  <p className="text-[#1800ad] mt-1">Your teacher hasn't set up chapters yet, or nothing matches your search.</p>
                </div>
              ) : (
                filteredGroups.map(({ cls, chapters }) => (
                  <section key={cls.class_id} className="flex flex-col gap-5">
                    <div className="flex items-center gap-3 border-b-2 border-[#1800ad]/10 pb-3">
                      <h2 className="text-xl md:text-2xl font-black text-[#1800ad]">{cls.subject}</h2>
                      <span className="text-xs font-semibold text-[#1800ad]/60 bg-[#1800ad]/10 px-2.5 py-0.5 rounded-full">
                        {cls.display_name} · Grade {cls.grade}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 lg:gap-6">
                      {chapters.map(ch => (
                        <motion.div
                          key={ch.chapter_id}
                          whileHover={{ y: -4 }}
                          onClick={() => navigate(`/student/playground?class_id=${cls.class_id}&chapter_id=${ch.chapter_id}`)}
                          className="bg-[#1800ad] text-[#f6f4ee] p-6 md:p-8 rounded-[32px] md:rounded-[40px] flex flex-col justify-between gap-5 relative overflow-hidden group cursor-pointer shadow-lg border-2 border-[#1800ad] h-72"
                        >
                          <div className="absolute -top-24 -right-24 w-60 h-60 bg-[#f6f4ee]/10 rounded-full blur-2xl pointer-events-none group-hover:scale-110 transition-transform duration-700"></div>

                          <div className="flex flex-col h-full z-10 justify-between">
                            <div className="flex justify-between items-start w-full">
                              <span className="text-[#f6f4ee]/70 font-semibold uppercase tracking-widest text-xs md:text-sm">
                                Chapter {ch.sequence_number}
                              </span>
                              <span className={`px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-full border ${
                                ch.status === 'data_ready' ? 'bg-emerald-400/20 text-emerald-300 border-emerald-400/30' :
                                ch.status === 'active' ? 'bg-blue-400/20 text-blue-300 border-blue-400/30' :
                                'bg-[#f6f4ee]/15 text-[#f6f4ee]/80 border-[#f6f4ee]/20'
                              }`}>
                                {ch.asset_count} assets
                              </span>
                            </div>

                            <div className="mt-2 flex-grow">
                              <h3 className="text-xl md:text-2xl font-bold text-[#f6f4ee] leading-tight group-hover:text-amber-300 transition-colors">
                                {ch.title}
                              </h3>
                            </div>

                            <div className="mt-auto pt-4 border-t border-[#f6f4ee]/10 flex items-center justify-between w-full">
                              <span className="text-xs text-[#f6f4ee]/80 font-bold uppercase tracking-wider">
                                {ch.status}
                              </span>
                              <div className="flex items-center gap-1 text-[#f6f4ee] font-bold text-xs">
                                <span>Enter Chapter</span>
                                <ChevronRight size={14} />
                              </div>
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  </section>
                ))
              )}

            </div>
          )}

        </div>
      </main>
      {/* MODAL: Logout Confirmation */}
      <AnimatePresence>
        {isLogoutModalOpen && (
          <div className="fixed inset-0 z-55 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-[#f6f4ee] border-2 border-[#1800ad] rounded-[32px] shadow-2xl p-6 md:p-8 max-w-sm w-full font-montserrat text-[#1800ad] flex flex-col gap-4 relative"
            >
              <h2 className="text-xl md:text-2xl font-black text-center uppercase tracking-wide">Logout</h2>
              <p className="text-sm text-[#1800ad]/80 font-bold text-center -mt-2">Are you sure you want to log out of Mootion?</p>
              
              <div className="flex gap-3 mt-2">
                <button
                  type="button"
                  onClick={() => setIsLogoutModalOpen(false)}
                  className="w-1/2 py-3 bg-transparent border-2 border-[#1800ad] hover:bg-[#1800ad]/5 font-bold rounded-full text-center text-sm cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => api.logout()}
                  className="w-1/2 py-3 bg-red-600 border-2 border-red-600 hover:bg-red-700 text-white font-bold rounded-full text-center text-sm cursor-pointer"
                >
                  Logout
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
