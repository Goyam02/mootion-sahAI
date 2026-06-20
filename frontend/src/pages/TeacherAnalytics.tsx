import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { 
  BarChart2, 
  LayoutDashboard, 
  BookOpen, 
  MessageSquare,
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  AlertTriangle,
  Award,
  Users
} from 'lucide-react';
import { NavItem } from '../components/NavItem';
import { ChatbotFab } from '../components/ChatbotFab';

interface WeakestStudent {
  student_id: string;
  full_name: string;
  score: number;
}

interface ClassOverviewItem {
  chapter_id: string;
  chapter_title?: string;
  avg_score: number;
  student_count: number;
  weakest_students: WeakestStudent[];
}

interface ClusterStudent {
  student_id: string;
  full_name: string;
}

interface ClusterGroup {
  id: string;
  class_id: string;
  chapter_id: string;
  chapter_title?: string;
  cluster_label: 'struggling' | 'average' | 'strong';
  avg_score: number;
  students: ClusterStudent[];
  computed_at: string;
}

export function TeacherAnalytics() {
  const { classId } = useParams<{ classId: string }>();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<ClassOverviewItem[]>([]);
  const [clusters, setClusters] = useState<ClusterGroup[]>([]);
  const [chapters, setChapters] = useState<any[]>([]);
  const [classInfo, setClassInfo] = useState<any>(null);
  
  // Sorting state for overview table
  const [sortAsc, setSortAsc] = useState<boolean>(true);
  
  // Expanded state for cluster rows
  const [expandedChapterId, setExpandedChapterId] = useState<string | null>(null);
  
  // Recomputing loader state per chapter
  const [recomputingId, setRecomputingId] = useState<string | null>(null);

  const loadData = async () => {
    if (!classId) return;
    try {
      setLoading(true);
      
      // 1. Fetch class summary list to find current classroom name
      const classes = await api.get('/teachers/classes');
      const currentClass = classes.find((c: any) => c.class_id === classId || c.id === classId);
      setClassInfo(currentClass || { display_name: "Classroom" });

      // 2. Fetch classroom chapters
      const fetchedChapters = await api.get(`/teachers/classes/${classId}/chapters`);
      setChapters(fetchedChapters);

      // 3. Fetch Overview
      const overviewData: ClassOverviewItem[] = await api.get(`/api/analytics/class/${classId}/overview`);
      
      // 4. Fetch Clusters
      const clustersData: ClusterGroup[] = await api.get(`/api/analytics/class/${classId}/clusters`);

      // Resolve chapter titles
      const resolvedOverview = overviewData.map(item => {
        const matched = fetchedChapters.find((ch: any) => ch.chapter_id === item.chapter_id);
        return {
          ...item,
          chapter_title: matched ? matched.title : `Chapter ${item.chapter_id.substring(0, 8)}`
        };
      });

      const resolvedClusters = clustersData.map(item => {
        const matched = fetchedChapters.find((ch: any) => ch.chapter_id === item.chapter_id);
        return {
          ...item,
          chapter_title: matched ? matched.title : `Chapter ${item.chapter_id.substring(0, 8)}`
        };
      });

      // Sort overview initially by average score ascending
      resolvedOverview.sort((a, b) => a.avg_score - b.avg_score);

      setOverview(resolvedOverview);
      setClusters(resolvedClusters);
    } catch (err) {
      console.error("Error loading classroom analytics:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [classId]);

  const toggleSort = () => {
    const nextSort = !sortAsc;
    setSortAsc(nextSort);
    const sorted = [...overview].sort((a, b) => {
      return nextSort ? a.avg_score - b.avg_score : b.avg_score - a.avg_score;
    });
    setOverview(sorted);
  };

  const toggleChapterExpand = (chapterId: string) => {
    setExpandedChapterId(prev => prev === chapterId ? null : chapterId);
  };

  const handleRecomputeClusters = async (chapterId: string) => {
    if (!classId) return;
    try {
      setRecomputingId(chapterId);
      // Calls POST /api/analytics/class/{classId}/compute-clusters with chapter_id
      await api.post(`/api/analytics/class/${classId}/compute-clusters`, {
        chapter_id: chapterId
      });
      
      // Reload clusters and overview details
      const freshClusters: ClusterGroup[] = await api.get(`/api/analytics/class/${classId}/clusters`);
      const resolvedClusters = freshClusters.map(item => {
        const matched = chapters.find((ch: any) => ch.chapter_id === item.chapter_id);
        return {
          ...item,
          chapter_title: matched ? matched.title : `Chapter ${item.chapter_id.substring(0, 8)}`
        };
      });
      setClusters(resolvedClusters);
      alert("Successfully recomputed student clusters!");
    } catch (err: any) {
      console.error("Failed to compute clusters:", err);
      alert(err.detail || "Error recomputing clusters. Minimum of 3 students with scores required.");
    } finally {
      setRecomputingId(null);
    }
  };

  // Group clusters by chapter to show one row per chapter
  const clusterGroupsByChapter = React.useMemo(() => {
    const map: Record<string, { chapter_title: string; struggling: ClusterStudent[]; average: ClusterStudent[]; strong: ClusterStudent[] }> = {};
    clusters.forEach(c => {
      const chapId = c.chapter_id;
      if (!map[chapId]) {
        map[chapId] = {
          chapter_title: c.chapter_title || `Chapter ${chapId.substring(0, 8)}`,
          struggling: [],
          average: [],
          strong: []
        };
      }
      if (c.cluster_label === 'struggling') {
        map[chapId].struggling = c.students || [];
      } else if (c.cluster_label === 'average') {
        map[chapId].average = c.students || [];
      } else if (c.cluster_label === 'strong') {
        map[chapId].strong = c.students || [];
      }
    });
    return Object.entries(map).map(([chapter_id, val]) => ({
      chapter_id,
      ...val
    }));
  }, [clusters]);

  if (loading) {
    return (
      <div className="flex-1 w-full bg-[#1800ad] h-screen flex flex-col items-center justify-center text-[#f6f4ee]">
        <div className="relative flex items-center justify-center">
          <span className="absolute animate-ping w-16 h-16 rounded-full bg-white/20"></span>
          <div className="w-12 h-12 border-4 border-white/20 border-t-white rounded-full animate-spin"></div>
        </div>
        <h2 className="text-xl font-bold tracking-wide mt-4 animate-pulse">Loading Classroom Analytics...</h2>
      </div>
    );
  }

  return (
    <div className="flex flex-1 w-full h-[100dvh] bg-[#1800ad] font-montserrat text-[#1800ad] overflow-hidden relative">
      <ChatbotFab context={`Teacher is reviewing class-level understanding metrics on analytics dashboard`} />
      
      {/* Teacher Sidebar */}
      <aside className="hidden md:flex w-[80px] lg:w-[100px] flex-col items-center justify-between py-8 fixed top-0 bottom-0 left-0 h-full shrink-0 bg-[#1800ad] text-[#f6f4ee] z-30">
        <div className="flex items-center justify-center mt-4 cursor-pointer" onClick={() => navigate('/')}>
          <span className="text-[#f6f4ee] font-val text-[42px] leading-none tracking-widest mt-1 mr-1">M</span>
        </div>
        <nav className="flex flex-col gap-6 w-full items-center my-auto">
          <NavItem icon={<LayoutDashboard size={24} />} onClick={() => navigate('/teacher/home')} />
          <NavItem icon={<BookOpen size={24} />} onClick={() => navigate(classId ? `/teacher/class/${classId}` : '/teacher/home')} />
          <NavItem icon={<BarChart2 size={24} />} active onClick={() => navigate(classId ? `/teacher/analytics/${classId}` : '/teacher/analytics')} />
          <NavItem icon={<MessageSquare size={24} />} onClick={() => navigate('/teacher/doubts')} />
        </nav>
        <div onClick={() => api.logout()} className="shrink-0 cursor-pointer flex items-center justify-center group w-12 h-12 rounded-full border-2 border-[#1800ad] bg-[#f6f4ee] relative">
          <span className="text-[#1800ad] font-bold text-lg">T</span>
        </div>
      </aside>

      <main className="flex-1 md:ml-[80px] lg:ml-[100px] bg-[#f6f4ee] md:rounded-l-[40px] p-5 md:p-8 flex flex-col overflow-hidden h-[100dvh]">
        
        {/* Top Header */}
        <header className="shrink-0 mb-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate(classId ? `/teacher/class/${classId}` : '/teacher/home')} className="p-2 border-2 border-[#1800ad]/10 rounded-full text-[#1800ad] hover:bg-[#1800ad]/5 transition-colors">
              <ArrowLeft size={20} />
            </button>
            <div className="flex flex-col text-left">
              <span className="text-[#1800ad]/60 font-bold text-xs uppercase tracking-wider">{classInfo?.display_name} • {classInfo?.subject}</span>
              <h1 className="text-xl md:text-2xl font-black text-[#1800ad] leading-none mt-1">Classroom Diagnostics & Analytics</h1>
            </div>
          </div>
        </header>

        {/* Scrollable Diagnostics Workspace */}
        <div className="flex-1 overflow-y-auto custom-scrollbar flex flex-col gap-8 pr-1 pb-10 min-h-0">
          
          {/* 1. Class Overview Card */}
          <section className="bg-white rounded-[32px] p-6 border-2 border-[#1800ad]/10 shadow-sm text-left flex flex-col gap-4">
            <div className="flex justify-between items-center pb-2 border-b border-[#1800ad]/10">
              <div className="flex items-center gap-2">
                <Award size={22} className="text-[#1800ad]" />
                <h2 className="text-lg font-black text-[#1800ad] uppercase tracking-wide">Class Overview</h2>
              </div>
              <button 
                onClick={toggleSort}
                className="px-4 py-1.5 bg-[#1800ad]/15 hover:bg-[#1800ad]/25 rounded-full font-extrabold text-[11px] uppercase tracking-wider transition-colors flex items-center gap-1.5"
              >
                Sort by Avg Score {sortAsc ? '▲ (Weakest First)' : '▼ (Strongest First)'}
              </button>
            </div>

            {overview.length === 0 ? (
              <div className="py-8 text-center italic text-[#1800ad]/50 font-bold">
                No student explanation scores logged for this classroom yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-[#1800ad]/15 text-[#1800ad]/75 font-mono uppercase text-[10px] tracking-wider">
                      <th className="py-3 px-4 font-black">Chapter</th>
                      <th className="py-3 px-4 font-black text-center">Avg Score</th>
                      <th className="py-3 px-4 font-black text-center">Students Attempted</th>
                      <th className="py-3 px-4 font-black">Weakest Students</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overview.map((item, idx) => (
                      <tr key={idx} className="border-b border-[#1800ad]/5 hover:bg-[#f6f4ee]/30 transition-colors">
                        <td className="py-3.5 px-4 font-black text-[#1800ad]">{item.chapter_title}</td>
                        <td className="py-3.5 px-4 text-center">
                          <span className={`px-3 py-1 rounded-full font-black text-xs ${
                            item.avg_score >= 7.5 ? 'bg-emerald-50 text-emerald-800' : item.avg_score >= 5.0 ? 'bg-amber-50 text-amber-800' : 'bg-rose-50 text-rose-800'
                          }`}>
                            {item.avg_score}/10
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-center font-bold text-[#1800ad]/80">{item.student_count} students</td>
                        <td className="py-3.5 px-4">
                          <div className="flex flex-wrap gap-1.5">
                            {item.weakest_students.map((st, sidx) => (
                              <button
                                key={sidx}
                                onClick={() => navigate(`/teacher/student/${st.student_id}/scores`)}
                                className="bg-rose-50 hover:bg-rose-100 border border-rose-100 text-rose-900 rounded-lg px-2.5 py-1 text-[10.5px] font-bold flex items-center gap-1 transition-all hover:scale-102"
                                title="Click to view student scores log"
                              >
                                {st.full_name} ({st.score})
                              </button>
                            ))}
                            {item.weakest_students.length === 0 && <span className="text-gray-400 italic">None logged</span>}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* 2 & 3. Student Clusters Section */}
          <section className="bg-white rounded-[32px] p-6 border-2 border-[#1800ad]/10 shadow-sm text-left flex flex-col gap-4">
            <div className="flex items-center gap-2 pb-2 border-b border-[#1800ad]/10">
              <Users size={22} className="text-[#1800ad]" />
              <h2 className="text-lg font-black text-[#1800ad] uppercase tracking-wide">Conceptual Student Clusters</h2>
            </div>
            
            <p className="text-xs text-[#1800ad]/75 font-semibold leading-relaxed max-w-2xl">
              Student clusters are computed using machine learning KMeans ($k=3$) groupings. Below, you can audit chapter performance groupings or recompute them as new student scores are added.
            </p>

            {clusterGroupsByChapter.length === 0 ? (
              <div className="py-8 text-center italic text-[#1800ad]/50 font-bold flex flex-col items-center gap-4">
                <span>No student cluster records computed yet. Select a chapter below to compute.</span>
                <div className="flex flex-wrap gap-2 justify-center">
                  {chapters.map((ch: any) => (
                    <button
                      key={ch.chapter_id}
                      onClick={() => handleRecomputeClusters(ch.chapter_id)}
                      disabled={recomputingId !== null}
                      className="px-4 py-2 bg-[#1800ad] hover:bg-[#1800ad]/90 text-white rounded-full font-bold text-xs uppercase tracking-wider disabled:opacity-50 transition-colors"
                    >
                      {recomputingId === ch.chapter_id ? "Computing..." : `Compute: ${ch.title}`}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                {clusterGroupsByChapter.map(group => {
                  const isExpanded = expandedChapterId === group.chapter_id;
                  const isRecomputing = recomputingId === group.chapter_id;

                  return (
                    <div 
                      key={group.chapter_id}
                      className="border-2 border-[#1800ad]/5 rounded-[22px] overflow-hidden bg-[#f6f4ee]/20 hover:bg-[#f6f4ee]/30 transition-shadow flex flex-col"
                    >
                      <div className="p-4 md:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                        
                        {/* Title and stats summary */}
                        <div 
                          onClick={() => toggleChapterExpand(group.chapter_id)}
                          className="flex-1 cursor-pointer flex flex-col text-left justify-start min-w-0"
                        >
                          <span className="font-extrabold text-[9px] text-[#1800ad]/40 uppercase tracking-widest font-mono">Conceptual Cluster Grid</span>
                          <h4 className="font-bold text-base text-[#1800ad] truncate leading-tight mt-1">
                            {group.chapter_title}
                          </h4>
                        </div>

                        {/* Cluster Tag Summary */}
                        <div className="flex items-center gap-3 shrink-0 flex-wrap">
                          <span className="bg-rose-50 border border-rose-100 text-rose-800 px-3 py-1 rounded-full text-[10.5px] font-black uppercase font-mono">
                            🔴 Struggling ({group.struggling.length})
                          </span>
                          <span className="bg-amber-50 border border-amber-100 text-amber-800 px-3 py-1 rounded-full text-[10.5px] font-black uppercase font-mono">
                            🟡 Average ({group.average.length})
                          </span>
                          <span className="bg-emerald-50 border border-emerald-100 text-emerald-800 px-3 py-1 rounded-full text-[10.5px] font-black uppercase font-mono">
                            🟢 Strong ({group.strong.length})
                          </span>
                        </div>

                        {/* Control Actions */}
                        <div className="flex items-center gap-3 shrink-0 border-l border-[#1800ad]/10 pl-4">
                          <button
                            type="button"
                            onClick={() => handleRecomputeClusters(group.chapter_id)}
                            disabled={isRecomputing || recomputingId !== null}
                            className="p-2 bg-[#1800ad]/10 hover:bg-[#1800ad]/20 text-[#1800ad] rounded-full transition-colors flex items-center justify-center shrink-0"
                            title="Recompute chapter clusters"
                          >
                            <RefreshCw size={16} className={isRecomputing ? 'animate-spin' : ''} />
                          </button>
                          
                          <button 
                            type="button"
                            onClick={() => toggleChapterExpand(group.chapter_id)}
                            className="p-1 hover:bg-[#1800ad]/5 rounded-full text-[#1800ad]/60"
                          >
                            {isExpanded ? <ChevronUp size={22} /> : <ChevronDown size={22} />}
                          </button>
                        </div>
                      </div>

                      {/* Expanded Section: showing student names inside each cluster */}
                      {isExpanded && (
                        <div className="border-t border-[#1800ad]/10 bg-white p-5 flex flex-col md:flex-row gap-4 text-left">
                          
                          {/* Struggling */}
                          <div className="flex-1 bg-rose-50/40 border border-rose-100 rounded-2xl p-4 flex flex-col gap-2.5">
                            <span className="font-extrabold text-[10px] text-rose-800 uppercase tracking-widest font-mono border-b border-rose-100 pb-1 flex items-center justify-between">
                              <span>🔴 Struggling</span>
                              <span>{group.struggling.length}</span>
                            </span>
                            <div className="flex flex-col gap-1.5">
                              {group.struggling.map(st => (
                                <button
                                  key={st.student_id}
                                  onClick={() => navigate(`/teacher/student/${st.student_id}/scores`)}
                                  className="w-full text-left bg-white hover:bg-rose-50 border border-rose-50 hover:border-rose-100 rounded-xl px-3 py-2 text-xs font-bold text-rose-950 transition-all flex justify-between items-center shadow-sm"
                                  title="View student scores profile"
                                >
                                  <span>{st.full_name}</span>
                                  <span className="text-[10px] text-rose-500 opacity-60">Audit →</span>
                                </button>
                              ))}
                              {group.struggling.length === 0 && <span className="text-xs text-neutral-400 italic">No students in this cluster.</span>}
                            </div>
                          </div>

                          {/* Average */}
                          <div className="flex-1 bg-amber-50/40 border border-amber-100 rounded-2xl p-4 flex flex-col gap-2.5">
                            <span className="font-extrabold text-[10px] text-amber-800 uppercase tracking-widest font-mono border-b border-amber-100 pb-1 flex items-center justify-between">
                              <span>🟡 Average</span>
                              <span>{group.average.length}</span>
                            </span>
                            <div className="flex flex-col gap-1.5">
                              {group.average.map(st => (
                                <button
                                  key={st.student_id}
                                  onClick={() => navigate(`/teacher/student/${st.student_id}/scores`)}
                                  className="w-full text-left bg-white hover:bg-amber-50 border border-amber-50 hover:border-amber-100 rounded-xl px-3 py-2 text-xs font-bold text-amber-950 transition-all flex justify-between items-center shadow-sm"
                                  title="View student scores profile"
                                >
                                  <span>{st.full_name}</span>
                                  <span className="text-[10px] text-amber-500 opacity-60">Audit →</span>
                                </button>
                              ))}
                              {group.average.length === 0 && <span className="text-xs text-neutral-400 italic">No students in this cluster.</span>}
                            </div>
                          </div>

                          {/* Strong */}
                          <div className="flex-1 bg-emerald-50/40 border border-emerald-100 rounded-2xl p-4 flex flex-col gap-2.5">
                            <span className="font-extrabold text-[10px] text-emerald-800 uppercase tracking-widest font-mono border-b border-emerald-100 pb-1 flex items-center justify-between">
                              <span>🟢 Strong</span>
                              <span>{group.strong.length}</span>
                            </span>
                            <div className="flex flex-col gap-1.5">
                              {group.strong.map(st => (
                                <button
                                  key={st.student_id}
                                  onClick={() => navigate(`/teacher/student/${st.student_id}/scores`)}
                                  className="w-full text-left bg-white hover:bg-emerald-50 border border-emerald-50 hover:border-emerald-100 rounded-xl px-3 py-2 text-xs font-bold text-emerald-950 transition-all flex justify-between items-center shadow-sm"
                                  title="View student scores profile"
                                >
                                  <span>{st.full_name}</span>
                                  <span className="text-[10px] text-emerald-500 opacity-60">Audit →</span>
                                </button>
                              ))}
                              {group.strong.length === 0 && <span className="text-xs text-neutral-400 italic">No students in this cluster.</span>}
                            </div>
                          </div>

                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* Trigger recomputation for any other chapter in the classroom */}
          <section className="bg-white rounded-[32px] p-6 border-2 border-[#1800ad]/10 shadow-sm text-left flex flex-col gap-3">
            <h3 className="font-bold text-xs uppercase tracking-widest text-[#1800ad]/60 ml-1">Manual Action Board</h3>
            <span className="text-xs font-semibold text-[#1800ad]/75">Manually recalculate clusters for any syllabus chapter:</span>
            <div className="flex flex-wrap gap-2.5 mt-1">
              {chapters.map((ch: any) => {
                const isRecomputing = recomputingId === ch.chapter_id;
                return (
                  <button
                    key={ch.chapter_id}
                    onClick={() => handleRecomputeClusters(ch.chapter_id)}
                    disabled={recomputingId !== null}
                    className="px-4 py-2 bg-white hover:bg-[#1800ad]/5 border border-[#1800ad]/20 text-[#1800ad] rounded-xl font-bold text-xs uppercase tracking-wider transition-all disabled:opacity-50 flex items-center gap-1.5 shadow-sm"
                  >
                    <RefreshCw size={12} className={isRecomputing ? 'animate-spin' : ''} />
                    {isRecomputing ? "Computing..." : ch.title}
                  </button>
                );
              })}
            </div>
          </section>

        </div>
      </main>
    </div>
  );
}
