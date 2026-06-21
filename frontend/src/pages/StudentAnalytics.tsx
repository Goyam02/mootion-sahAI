import React, { useState, useEffect } from 'react';
import { LogoutModal } from '../components/LogoutModal';
import { 
  LayoutDashboard, 
  CheckSquare, 
  Gamepad2, 
  BarChart2, 
  ArrowLeft,
  Award,
  Calendar,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  MessageSquare
} from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../lib/api';
import { NavItem } from '../components/NavItem';
import { ChatbotFab } from '../components/ChatbotFab';
import { 
  Radar, 
  RadarChart, 
  PolarGrid, 
  PolarAngleAxis, 
  PolarRadiusAxis, 
  ResponsiveContainer, 
  Legend,
  Tooltip
} from 'recharts';

interface ScoreAttempt {
  id: string;
  transcript: string;
  clarity_score: number;
  accuracy_score: number;
  depth_score: number;
  overall_score: number;
  llm_feedback: string;
  gaps?: string[] | null;
  attempt_number: number;
  created_at: string;
}

interface ChapterGroup {
  chapter_id: string;
  chapter_title?: string;
  scores: ScoreAttempt[];
  trend: 'improving' | 'stable' | 'declining';
}

export function StudentAnalytics() {
  const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);
  const navigate = useNavigate();
  const { studentId } = useParams<{ studentId: string }>();
  const isReadOnly = !!studentId;

  const [loading, setLoading] = useState(true);
  const [studentInfo, setStudentInfo] = useState<any>(null);
  const [analyticsData, setAnalyticsData] = useState<ChapterGroup[]>([]);
  const [expandedChapterId, setExpandedChapterId] = useState<string | null>(null);

  useEffect(() => {
    async function loadAnalytics() {
      try {
        setLoading(true);
        let activeStudentId = studentId;

        // 1. Fetch student info
        if (isReadOnly) {
          try {
            const drillData = await api.get(`/teachers/students/${studentId}/analytics`);
            setStudentInfo({
              full_name: drillData.student_name || 'Student Detail'
            });
          } catch (e) {
            console.error("Could not fetch student drill data:", e);
            setStudentInfo({ full_name: 'Student Detail' });
          }
        } else {
          const me = await api.get('/students/me');
          setStudentInfo(me);
          if (me) activeStudentId = me.user_id || me.id;
        }

        if (activeStudentId) {
          // 2. Fetch scores
          const scoresData: ChapterGroup[] = await api.get(`/api/analytics/student/${activeStudentId}/scores`);
          
          // 3. Resolve chapter titles dynamically
          const resolvedData = await Promise.all(
            scoresData.map(async (group) => {
              try {
                const classes = isReadOnly 
                  ? await api.get('/teachers/classes')
                  : await api.get('/students/classes');

                if (classes && classes.length > 0) {
                  const classId = classes[0].class_id || classes[0].id;
                  const chapters = isReadOnly
                    ? await api.get(`/teachers/classes/${classId}/chapters`)
                    : await api.get(`/students/classes/${classId}/chapters`);

                  const matched = chapters.find((ch: any) => ch.chapter_id === group.chapter_id);
                  if (matched) {
                    return { ...group, chapter_title: matched.title };
                  }
                }
              } catch (e) {
                console.warn("Could not resolve chapter title:", e);
              }
              return { ...group, chapter_title: `Chapter ${group.chapter_id.substring(0, 8)}` };
            })
          );

          setAnalyticsData(resolvedData);
        }
      } catch (err) {
        console.error("Error loading analytics:", err);
      } finally {
        setLoading(false);
      }
    }
    loadAnalytics();
  }, [studentId]);

  const getTrendIconAndColor = (group: ChapterGroup) => {
    if (group.scores.length < 2) return { arrow: '→', color: 'text-blue-500 bg-blue-50' };
    const latest = group.scores[group.scores.length - 1].overall_score;
    const prev = group.scores[group.scores.length - 2].overall_score;
    if (latest > prev) {
      return { arrow: '↑', color: 'text-emerald-600 bg-emerald-50' };
    } else if (latest < prev) {
      return { arrow: '↓', color: 'text-rose-600 bg-rose-50' };
    }
    return { arrow: '→', color: 'text-blue-500 bg-blue-50' };
  };

  const getProgressBarColor = (score: number) => {
    if (score > 7) return 'bg-emerald-500';
    if (score >= 4) return 'bg-amber-500';
    return 'bg-rose-500';
  };

  // 1. Radar Chart Data Prep
  const radarData = analyticsData.map(group => {
    const latest = group.scores[group.scores.length - 1] || { overall_score: 0, clarity_score: 0, accuracy_score: 0, depth_score: 0 };
    return {
      chapter_name: group.chapter_title || `Ch ${group.chapter_id.substring(0, 5)}`,
      overall_score: latest.overall_score,
      clarity: latest.clarity_score,
      accuracy: latest.accuracy_score,
      depth: latest.depth_score
    };
  });

  // 2. "Your Weakest Topics" - Bottom 3 chapters by overall_score
  const weakestTopics = [...analyticsData]
    .map(group => {
      const latest = group.scores[group.scores.length - 1];
      return {
        ...group,
        latestScore: latest ? latest.overall_score : 0
      };
    })
    .sort((a, b) => a.latestScore - b.latestScore)
    .slice(0, 3);

  const toggleChapterExpand = (chapterId: string) => {
    setExpandedChapterId(prev => prev === chapterId ? null : chapterId);
  };

  if (loading) {
    return (
      <div className="flex-1 w-full bg-[#1800ad] h-screen flex flex-col items-center justify-center text-[#f6f4ee]">
        <div className="relative flex items-center justify-center">
          <span className="absolute animate-ping w-16 h-16 rounded-full bg-white/20"></span>
          <div className="w-12 h-12 border-4 border-white/20 border-t-white rounded-full animate-spin"></div>
        </div>
        <h2 className="text-xl font-bold tracking-wide mt-4 animate-pulse">
          {isReadOnly ? "Loading Student Analytics (Teacher View)..." : "Loading Analytics Board..."}
        </h2>
      </div>
    );
  }

  return (
    <div className="flex flex-1 w-full h-[100dvh] bg-[#1800ad] font-montserrat text-[#1800ad] overflow-hidden relative">
      <ChatbotFab context={isReadOnly ? "Teacher is viewing student analytics report" : "User is viewing their student analytics history dashboard"} />
      
      {/* Sidebar */}
      <aside className="hidden md:flex w-[80px] lg:w-[100px] flex-col items-center justify-between py-8 fixed top-0 bottom-0 left-0 h-full shrink-0 bg-[#1800ad] text-[#f6f4ee] z-30">
        <div className="flex items-center justify-center mt-4 cursor-pointer" onClick={() => navigate('/')}>
          <span className="text-[#f6f4ee] font-val text-[42px] leading-none tracking-widest mt-1 mr-1">M</span>
        </div>
        <nav className="flex flex-col gap-6 w-full items-center my-auto">
          {isReadOnly ? (
            <>
              <NavItem icon={<LayoutDashboard size={24} />} onClick={() => navigate('/teacher/home')} />
              <NavItem icon={<BarChart2 size={24} />} active onClick={() => navigate('/teacher/analytics')} />
              <NavItem icon={<MessageSquare size={24} />} onClick={() => navigate('/teacher/doubts')} />
            </>
          ) : (
            <>
              <NavItem icon={<LayoutDashboard size={24} />} onClick={() => navigate('/student/home')} />
              <NavItem icon={<CheckSquare size={24} />} onClick={() => navigate('/student/tasks')} />

              <NavItem icon={<Gamepad2 size={24} />} onClick={() => navigate('/student/playground')} />
              <NavItem icon={<BarChart2 size={24} />} active onClick={() => navigate('/student/analytics')} />
            </>
          )}
        </nav>
        <div onClick={() => setIsLogoutModalOpen(true)} className="shrink-0 cursor-pointer flex items-center justify-center w-12 h-12 rounded-full bg-[#f6f4ee]">
          <span className="text-[#1800ad] font-bold text-lg">
            {isReadOnly ? 'T' : (studentInfo?.full_name?.charAt(0).toUpperCase() || 'S')}
          </span>
        </div>
      </aside>

      <main className="flex-1 md:ml-[80px] lg:ml-[100px] bg-[#f6f4ee] md:rounded-l-[40px] p-5 md:p-8 flex flex-col overflow-hidden h-[100dvh]">
        
        {/* Header Section */}
        <header className="shrink-0 mb-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => {
                if (isReadOnly) {
                  navigate(-1);
                } else {
                  navigate('/student/home');
                }
              }} 
              className="p-2 border-2 border-[#1800ad]/10 rounded-full text-[#1800ad] hover:bg-[#1800ad]/5 transition-colors"
            >
              <ArrowLeft size={20} />
            </button>
            <div className="flex flex-col text-left">
              <span className="text-[#1800ad]/60 font-bold text-xs uppercase tracking-wider">
                {isReadOnly ? "Teacher View Mode" : "Student Profile Analytics"}
              </span>
              <h1 className="text-xl md:text-2xl font-black text-[#1800ad] leading-none mt-1">
                {isReadOnly ? `Understanding Scores: ${studentInfo?.full_name}` : "My Understanding Scores"}
              </h1>
            </div>
          </div>
          {studentInfo && (
            <div className="bg-[#1800ad]/5 border border-[#1800ad]/10 px-4 py-2 rounded-2xl flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-[#1800ad] text-white font-black text-sm flex items-center justify-center">
                {isReadOnly ? 'T' : studentInfo.full_name?.charAt(0).toUpperCase()}
              </div>
              <span className="text-xs font-black text-[#1800ad]">
                {isReadOnly ? `Reviewing ${studentInfo.full_name}` : studentInfo.full_name}
              </span>
            </div>
          )}
        </header>

        {analyticsData.length === 0 ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="max-w-md bg-white border-2 border-[#1800ad]/10 rounded-[32px] p-8 text-center flex flex-col items-center gap-4 shadow-md">
              <div className="p-4 bg-amber-500/10 text-amber-600 rounded-full">
                <AlertTriangle size={36} />
              </div>
              <h3 className="text-xl font-bold text-[#1800ad]">No Understanding Scores Yet!</h3>
              <p className="text-xs text-[#1800ad]/70 leading-relaxed font-medium">
                {isReadOnly 
                  ? "This student hasn't logged any concept scores yet. Once they speak or explain science concepts, their analysis history will display here."
                  : "You haven't completed any explain-to-Mootion lessons yet. Go to your tasks, complete a learning activity, and explain concepts to start logging analytics!"}
              </p>
              {!isReadOnly && (
                <button 
                  onClick={() => navigate('/student/tasks')}
                  className="mt-2 px-6 py-2.5 bg-[#1800ad] hover:bg-[#1800ad]/90 text-white font-bold text-xs uppercase tracking-widest rounded-full shadow"
                >
                  Go to Tasks
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col lg:flex-row overflow-hidden gap-6 min-h-0 pb-4">
            
            {/* Left side: Chapter cards list + Weakest Topics */}
            <div className="w-full lg:w-7/12 flex flex-col gap-5 overflow-y-auto custom-scrollbar pr-2 min-h-0">
              
              {/* Chapter-wise Score Cards */}
              <div className="flex flex-col gap-3">
                <h3 className="font-bold text-xs uppercase tracking-widest text-[#1800ad]/60 ml-1 text-left">Chapter Breakdown</h3>
                
                {analyticsData.map(group => {
                  const isExpanded = expandedChapterId === group.chapter_id;
                  const latestScore = group.scores[group.scores.length - 1];
                  const { arrow, color } = getTrendIconAndColor(group);

                  return (
                    <div 
                      key={group.chapter_id} 
                      className="bg-white border-2 border-[#1800ad]/10 rounded-[24px] overflow-hidden shadow-sm hover:shadow transition-shadow flex flex-col"
                    >
                      {/* Collapsed Header click area */}
                      <div 
                        onClick={() => toggleChapterExpand(group.chapter_id)}
                        className="p-4 md:p-5 flex items-center justify-between cursor-pointer"
                      >
                        <div className="flex flex-col text-left pr-4 min-w-0">
                          <span className="font-extrabold text-[9px] text-[#1800ad]/50 uppercase tracking-widest font-mono">
                            {group.scores.length} Attempt{group.scores.length > 1 ? 's' : ''}
                          </span>
                          <h4 className="font-bold text-base text-[#1800ad] truncate leading-tight mt-1">
                            {group.chapter_title}
                          </h4>
                        </div>
                        
                        <div className="flex items-center gap-4 shrink-0">
                          <div className="flex flex-col items-end">
                            <span className="text-[9px] font-extrabold text-[#1800ad]/40 uppercase tracking-widest font-mono">Latest Score</span>
                            <span className="font-black text-base text-[#1800ad]">{latestScore.overall_score}/10</span>
                          </div>
                          
                          <span className={`w-8 h-8 rounded-full font-black text-sm flex items-center justify-center ${color}`}>
                            {arrow}
                          </span>

                          {isExpanded ? <ChevronUp size={20} className="text-[#1800ad]/60" /> : <ChevronDown size={20} className="text-[#1800ad]/60" />}
                        </div>
                      </div>

                      {/* Expanded Section showing all attempts */}
                      {isExpanded && (
                        <div className="border-t border-[#1800ad]/10 bg-[#f6f4ee]/20 p-5 flex flex-col gap-4 text-left">
                          {group.scores.map((attempt) => (
                            <div key={attempt.id} className="bg-white border border-[#1800ad]/10 rounded-2xl p-4 flex flex-col gap-3 shadow-inner">
                              <div className="flex justify-between items-center">
                                <span className="bg-[#1800ad] text-white text-[9px] font-black uppercase tracking-wider px-2 rounded-full font-mono">
                                  Attempt #{attempt.attempt_number}
                                </span>
                                <span className="text-[10px] text-[#1800ad]/40 font-bold font-mono">
                                  {new Date(attempt.created_at).toLocaleDateString(undefined, { 
                                    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' 
                                  })}
                                </span>
                              </div>

                              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 items-center">
                                <div className="bg-[#1800ad]/5 border border-[#1800ad]/5 rounded-xl p-3 text-center">
                                  <span className="text-[9px] font-extrabold text-[#1800ad]/50 uppercase tracking-widest font-mono block">Overall</span>
                                  <span className="text-lg font-black text-[#1800ad]">{attempt.overall_score}/10</span>
                                </div>
                                <div className="sm:col-span-3 flex flex-col gap-1.5">
                                  {/* Clarity */}
                                  <div className="flex flex-col gap-0.5">
                                    <div className="flex justify-between text-[9px] font-bold text-[#1800ad]/80">
                                      <span>Clarity</span>
                                      <span>{attempt.clarity_score}/10</span>
                                    </div>
                                    <div className="w-full bg-[#1800ad]/10 h-1 rounded-full overflow-hidden">
                                      <div className={`h-full ${getProgressBarColor(attempt.clarity_score)}`} style={{ width: `${attempt.clarity_score * 10}%` }}></div>
                                    </div>
                                  </div>
                                  {/* Accuracy */}
                                  <div className="flex flex-col gap-0.5">
                                    <div className="flex justify-between text-[9px] font-bold text-[#1800ad]/80">
                                      <span>Accuracy</span>
                                      <span>{attempt.accuracy_score}/10</span>
                                    </div>
                                    <div className="w-full bg-[#1800ad]/10 h-1 rounded-full overflow-hidden">
                                      <div className={`h-full ${getProgressBarColor(attempt.accuracy_score)}`} style={{ width: `${attempt.accuracy_score * 10}%` }}></div>
                                    </div>
                                  </div>
                                  {/* Depth */}
                                  <div className="flex flex-col gap-0.5">
                                    <div className="flex justify-between text-[9px] font-bold text-[#1800ad]/80">
                                      <span>Depth</span>
                                      <span>{attempt.depth_score}/10</span>
                                    </div>
                                    <div className="w-full bg-[#1800ad]/10 h-1 rounded-full overflow-hidden">
                                      <div className={`h-full ${getProgressBarColor(attempt.depth_score)}`} style={{ width: `${attempt.depth_score * 10}%` }}></div>
                                    </div>
                                  </div>
                                </div>
                              </div>

                              {attempt.llm_feedback && (
                                <p className="text-xs italic bg-neutral-50 text-neutral-600 p-2.5 rounded-lg border border-neutral-100 mt-1">
                                  "{attempt.llm_feedback}"
                                </p>
                              )}
                              
                              {attempt.gaps && attempt.gaps.length > 0 && (
                                <div className="mt-2 bg-rose-50/50 border border-rose-100 p-2.5 rounded-lg flex flex-col gap-1.5">
                                  <span className="text-[10px] font-black uppercase tracking-wider text-rose-800 flex items-center gap-1.5">
                                    <AlertTriangle size={12} />
                                    Misconceptions / Gaps
                                  </span>
                                  <ul className="flex flex-col gap-1 list-disc pl-4">
                                    {attempt.gaps.map((gap, i) => (
                                      <li key={i} className="text-xs text-rose-900 font-medium">
                                        {gap}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Weakest Topics Section */}
              <div className="bg-rose-50 border-2 border-rose-200 rounded-[28px] p-5 md:p-6 text-left shadow-sm flex flex-col gap-3.5 shrink-0 mt-2">
                <div className="flex items-center gap-2 text-rose-800">
                  <AlertTriangle className="stroke-[2.5]" size={20} />
                  <h3 className="text-base font-black uppercase tracking-wider font-mono">
                    {isReadOnly ? "Weakest Topics for Student" : "Your Weakest Topics"}
                  </h3>
                </div>
                <p className="text-xs text-rose-950/80 font-semibold leading-relaxed">
                  {isReadOnly 
                    ? "These topics represent the chapters where this student has the lowest overall scores. Review their learning feedback on expand."
                    : "These topics have the lowest latest conceptual understanding scores. Double tap them on your homepage to review details and re-explain concepts to Mootion!"}
                </p>
                <div className="flex flex-col gap-2.5">
                  {weakestTopics.map(group => (
                    <div 
                      key={group.chapter_id} 
                      className="bg-white border border-rose-100 rounded-xl p-3 flex items-center justify-between shadow-inner"
                    >
                      <h4 className="font-bold text-xs text-rose-950 truncate max-w-[75%]">
                        {group.chapter_title}
                      </h4>
                      <span className="font-black text-xs text-rose-700 bg-rose-100 px-3 py-1 rounded-full shrink-0">
                        {group.latestScore}/10
                      </span>
                    </div>
                  ))}
                </div>
              </div>

            </div>

            {/* Right side: Radar Chart */}
            <div className="flex-1 bg-white border-2 border-[#1800ad]/10 rounded-[32px] p-5 flex flex-col min-h-0 shadow-sm overflow-hidden justify-between">
              <div className="flex flex-col text-left shrink-0">
                <span className="text-[10px] font-extrabold text-[#1800ad]/50 uppercase tracking-widest font-mono">Conceptual Strengths Map</span>
                <h3 className="text-lg font-black text-[#1800ad] mt-0.5 leading-snug">Latest Scoring Radar</h3>
              </div>

              {/* Responsive Container for Recharts RadarChart */}
              <div className="flex-1 w-full min-h-[280px] lg:min-h-0 py-4 flex items-center justify-center">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart cx="50%" cy="50%" outerRadius="75%" data={radarData}>
                    <PolarGrid stroke="#1800ad/20" />
                    <PolarAngleAxis dataKey="chapter_name" tick={{ fill: '#1800ad', fontSize: 10, fontWeight: '700' }} />
                    <PolarRadiusAxis angle={30} domain={[0, 10]} tick={{ fill: '#1800ad' }} />
                    <Radar 
                      name="Overall Score" 
                      dataKey="overall_score" 
                      stroke="#1800ad" 
                      fill="#1800ad" 
                      fillOpacity={0.15} 
                    />
                    <Radar 
                      name="Clarity" 
                      dataKey="clarity" 
                      stroke="#10b981" 
                      fill="#10b981" 
                      fillOpacity={0.05} 
                    />
                    <Radar 
                      name="Accuracy" 
                      dataKey="accuracy" 
                      stroke="#f59e0b" 
                      fill="#f59e0b" 
                      fillOpacity={0.05} 
                    />
                    <Radar 
                      name="Depth" 
                      dataKey="depth" 
                      stroke="#ec4899" 
                      fill="#ec4899" 
                      fillOpacity={0.05} 
                    />
                    <Tooltip contentStyle={{ borderRadius: '12px', borderColor: '#1800ad/10' }} />
                    <Legend wrapperStyle={{ fontSize: 10, fontWeight: '700' }} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>

              <div className="text-[10px] text-center font-bold text-[#1800ad]/60 shrink-0 border-t border-[#1800ad]/10 pt-3">
                * Based on the latest explanation scores across science topics
              </div>

            </div>

          </div>
        )}
      </main>
      {/* MODAL: Logout Confirmation */}
      <LogoutModal isOpen={isLogoutModalOpen} onClose={() => setIsLogoutModalOpen(false)} />
    </div>
  );
}
