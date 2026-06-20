import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { motion, AnimatePresence } from 'motion/react';
import { 
  BarChart2, 
  LayoutDashboard, 
  BookOpen, 
  MessageSquare,
  Search,
  Users,
  AlertTriangle,
  ChevronRight,
  TrendingUp,
  Award,
  BookOpenCheck,
  User,
  GraduationCap,
  Calendar,
  X,
  MessageCircle,
  Clock
} from 'lucide-react';
import { NavItem } from '../components/NavItem';

interface ClassInsight {
  id: string;
  className: string;
  subjectName: string;
  understanding: number;
  reasoning: number;
  expression: number;
  studentCount: number;
}

interface StudentRecord {
  name: string;
  understanding: number;
  reasoning: number;
  expression: number;
  progress: number;
  completedChapters: string[];
  recentMisconceptions: string[];
  recentAiResult: {
    prompt: string;
    answer: string;
    feedback: string;
    score: string;
  };
}

// Student database pool to dynamically select and populate at least 6 students
const studentPool = [
  { name: 'Aarav Sharma', avatarSeed: 'A' },
  { name: 'Poorvika Patel', avatarSeed: 'P' },
  { name: 'Rahul Shah', avatarSeed: 'R' },
  { name: 'Ishita Kapoor', avatarSeed: 'I' },
  { name: 'Dev Patel', avatarSeed: 'D' },
  { name: 'Kabir Mehta', avatarSeed: 'K' },
  { name: 'Sanya Sen', avatarSeed: 'S' },
  { name: 'Sneha Gupta', avatarSeed: 'G' },
  { name: 'Aditya Joshi', avatarSeed: 'Y' },
  { name: 'Ananya Reddy', avatarSeed: 'N' },
  { name: 'Arjun Verma', avatarSeed: 'J' },
  { name: 'Diya Malhotra', avatarSeed: 'X' }
];

const mockPromptsBySubject: Record<string, { prompt: string; answer: string; feedback: string }[]> = {
  'Physics': [
    {
      prompt: 'Describe why lubrication decreases mechanical wear over metallic surfaces.',
      answer: 'Lubricant fluid covers the microscopic mountain asperities on physical metals so they do not interlock and weld under force. They slide smoothly over the liquid cushion.',
      feedback: 'Excellent visualization of atomic-level friction interlocking relief.'
    },
    {
      prompt: 'Explain fluid displacement and buoyant upward force.',
      answer: 'When a brick sinks, it pushes aside its own volume of fluid. The mass of that displaced water pushes back upward, generating buoyant lift force.',
      feedback: 'Correct application of Archimedes Principle. Extremely concise.'
    }
  ],
  'Chemistry': [
    {
      prompt: 'Explain polar covalent electron sharing in a clear water compound.',
      answer: 'Oxygen is strongly electronegative and pulls the shared valence electrons closer to its nucleus, rendering the balance uneven and establishing a polar molecule.',
      feedback: 'Splendid comprehension of polar electronic structures and coordinate clouds.'
    },
    {
      prompt: 'What is the key structural layout difference between ionic crystal grids and single molecules?',
      answer: 'Ionic structures arrange in giant continuous repeating crystal arrays without individual cluster endpoints, unlike small custom molecules.',
      feedback: 'Outstanding explanation of lattice arrays.'
    }
  ],
  'Mathematics': [
    {
      prompt: 'Solve and detail balancing steps of: 4x - 12 = 28',
      answer: 'First add 12 to both sides of the balance equation, yielding 4x = 40. Then divide both sides by 4 to cleanly isolate variable x = 10.',
      feedback: 'Perfect description of linear structural separation operations.'
    },
    {
      prompt: 'Detail algebraic bracket expansions for: -3(y - 5)',
      answer: 'Using sign multiplication rules, expanding the coefficient yields -3y and -3 multiplied by -5 gives positive 15. The outcome is -3y + 15.',
      feedback: 'Superb application of constant polarity transformations.'
    }
  ],
  'Biology': [
    {
      prompt: 'Explain how mitochondria generate storage fuel inside a living animal cell.',
      answer: 'Mitochondria break down high-energy sugars during respiration, storing captured chemical potential energy inside molecular ATP batteries.',
      feedback: 'Clear, high-fidelity biological power system breakdown.'
    }
  ]
};

const getChaptersBySubject = (subject: string): string[] => {
  if (subject.includes('Phys')) {
    return ['Introduction to Forces', 'Contact vs Non-Contact Forces', 'Pressure Laws', 'Electromagnetic Action'];
  }
  if (subject.includes('Chem')) {
    return ['Atomic Structures & Valency', 'Covalent Bonds', 'Metals & Metallurgy', 'Acids & Bases'];
  }
  if (subject.includes('Math')) {
    return ['Variables & Algebraic Foundations', 'Linear Balancing Equations', 'Rational Coordinates', 'Polynomial Fractions'];
  }
  return ['Cell Dynamics', 'Tissue Configurations', 'Anatomy Systems', 'Plant Respiration'];
};

const getMisconceptionsBySubject = (subject: string): { title: string; percentage: number; count: number }[] => {
  if (subject.includes('Phys')) {
    return [
      { title: 'Students believe heavier bodies naturally fall faster in vacuum parameters.', percentage: 46, count: 14 },
      { title: 'Confusing density displacement weight with volume displacement.', percentage: 38, count: 11 },
      { title: 'Thinking static force does not exert work vectors.', percentage: 29, count: 8 }
    ];
  }
  if (subject.includes('Chem')) {
    return [
      { title: 'Assuming ionic crystals can form isolated molecular pairs.', percentage: 41, count: 12 },
      { title: 'Confusing chemical balance coefficients with valency sub-scripts.', percentage: 34, count: 10 }
    ];
  }
  if (subject.includes('Math')) {
    return [
      { title: 'Applying negative sign expansion rules incorrectly across parentheses.', percentage: 52, count: 16 },
      { title: 'Applying linear balance ratios on only single sides.', percentage: 45, count: 13 }
    ];
  }
  return [
    { title: 'Confusing active cell structure with inert passive chemical layers.', percentage: 30, count: 9 }
  ];
};

export function TeacherAnalyticsPage() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<any>(null);
  const [selectedClassId, setSelectedClassId] = useState<string>('');
  const [selectedStudent, setSelectedStudent] = useState<any | null>(null);

  const handleClassroomNav = () => {
    const lastClassId = localStorage.getItem('mootion_last_class_id');
    if (lastClassId) {
      navigate(`/teacher/class/${lastClassId}`);
    } else {
      navigate('/teacher/class/class-8-science');
    }
  };
  
  // Real data state variables
  const [classes, setClasses] = useState<any[]>([]);
  const [classAnalytics, setClassAnalytics] = useState<Record<string, any>>({});
  const [students, setStudents] = useState<any[]>([]);
  const [drilldownStudentId, setDrilldownStudentId] = useState<string | null>(null);
  const [selectedStudentDrilldown, setSelectedStudentDrilldown] = useState<any | null>(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState<boolean>(true);
  const [loadingStudents, setLoadingStudents] = useState<boolean>(false);
  const [loadingDrilldown, setLoadingDrilldown] = useState<boolean>(false);
  const [teacherName, setTeacherName] = useState<string>('Teacher');

  useEffect(() => {
    const data = localStorage.getItem('mootion_teacher_setup');
    if (data) {
      setProfile(JSON.parse(data));
    }
  }, []);

  // Fetch teacher profile on mount
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

  // Fetch classes on mount
  useEffect(() => {
    const fetchClasses = async () => {
      try {
        const data = await api.get('/teachers/classes');
        setClasses(data);
        if (data.length > 0) {
          setSelectedClassId(data[0].class_id);
        }
      } catch (err) {
        console.error("Failed to fetch classes:", err);
      }
    };
    fetchClasses();
  }, []);

  // Fetch overview analytics for each class when classes are loaded
  useEffect(() => {
    if (classes.length === 0) return;
    const fetchAllOverview = async () => {
      setLoadingAnalytics(true);
      const analyticsMap: Record<string, any> = {};
      await Promise.all(
        classes.map(async (c) => {
          try {
            const data = await api.get(`/teachers/classes/${c.class_id}/analytics/overview`);
            analyticsMap[c.class_id] = data;
          } catch (err) {
            console.error(`Failed to fetch analytics overview for class ${c.class_id}:`, err);
          }
        })
      );
      setClassAnalytics(analyticsMap);
      setLoadingAnalytics(false);
    };
    fetchAllOverview();
  }, [classes]);

  // Fetch student list for selected class
  useEffect(() => {
    if (!selectedClassId) return;
    const fetchStudentsAnalytics = async () => {
      setLoadingStudents(true);
      try {
        const data = await api.get(`/teachers/classes/${selectedClassId}/students/analytics`);
        setStudents(data);
      } catch (err) {
        console.error(`Failed to fetch students analytics for class ${selectedClassId}:`, err);
      } finally {
        setLoadingStudents(false);
      }
    };
    fetchStudentsAnalytics();
  }, [selectedClassId]);

  // Fetch student drilldown details
  useEffect(() => {
    if (!drilldownStudentId) {
      setSelectedStudentDrilldown(null);
      return;
    }
    const fetchStudentDrilldown = async () => {
      setLoadingDrilldown(true);
      try {
        const data = await api.get(`/teachers/students/${drilldownStudentId}/analytics`);
        setSelectedStudentDrilldown(data);
      } catch (err) {
        console.error(`Failed to fetch student drilldown for ${drilldownStudentId}:`, err);
      } finally {
        setLoadingDrilldown(false);
      }
    };
    fetchStudentDrilldown();
  }, [drilldownStudentId]);

  // Form dynamic combination objects for class Insights
  const classInsights = React.useMemo(() => {
    return classes.map((c) => {
      const analytics = classAnalytics[c.class_id];
      const avg = analytics?.average_scores || { understanding: 0, reasoning: 0, expression: 0 };
      
      return {
        id: c.class_id,
        className: c.grade.toLowerCase().includes('class') ? c.grade : `Class ${c.grade}`,
        subjectName: c.subject.charAt(0).toUpperCase() + c.subject.slice(1),
        understanding: avg.understanding,
        reasoning: avg.reasoning,
        expression: avg.expression,
        studentCount: analytics?.recent_activities ? new Set(analytics.recent_activities.map((a: any) => a.student_id)).size || 15 : 15,
      };
    });
  }, [classes, classAnalytics]);

  // Find active class insight details
  const activeClassInsight = classInsights.find(c => c.id === selectedClassId) || classInsights[0] || {
    className: 'Class 8',
    subjectName: 'Physics',
    studentCount: 28,
    understanding: 2.2,
    reasoning: 2.0,
    expression: 2.3
  };

  const activeSubject = activeClassInsight.subjectName;
  const activeClassName = activeClassInsight.className;

  // Selected student progression data list
  const studentsListForSelectedClass = students;

  // Determine misconceptions to render
  const activeMisconceptions = React.useMemo(() => {
    const analytics = classAnalytics[selectedClassId];
    if (analytics && analytics.most_common_misconception && analytics.most_common_misconception !== "No submissions yet.") {
      return [
        {
          title: analytics.most_common_misconception,
          percentage: 45,
          count: analytics.misconception_count || 3
        }
      ];
    }
    // Fallback to static NCERT misconceptions if none detected yet
    return getMisconceptionsBySubject(activeSubject);
  }, [classAnalytics, selectedClassId, activeSubject]);

  return (
    <div className="flex flex-1 w-full h-[100dvh] bg-[#f6f4ee] md:bg-[#1800ad] font-montserrat text-[#1800ad] overflow-hidden relative">
      
      <nav className="md:hidden fixed bottom-4 left-4 right-4 bg-[#1800ad] px-6 py-2.5 flex justify-between items-center z-40 rounded-full border-[2px] border-[#f6f4ee] shadow-xl">
        <NavItem icon={<LayoutDashboard size={24} />} onClick={() => navigate('/teacher/home')} />
        <NavItem icon={<BookOpen size={24} />} onClick={handleClassroomNav} />
        <NavItem icon={<BarChart2 size={24} />} active onClick={() => navigate('/teacher/analytics')} />
        <NavItem icon={<MessageSquare size={24} />} onClick={() => navigate('/teacher/doubts')} />
      </nav>

      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex w-[80px] lg:w-[100px] flex-col items-center justify-between py-8 fixed top-0 bottom-0 left-0 h-full shrink-0 bg-[#1800ad] text-[#f6f4ee] z-30">
        <div className="flex items-center justify-center shrink-0 mt-4 cursor-pointer" onClick={() => navigate('/teacher/home')}>
          <span className="text-[#f6f4ee] font-val text-[42px] leading-none tracking-widest mt-1 mr-1 notranslate">M</span>
        </div>
        <nav className="flex flex-col gap-6 w-full items-center my-auto">
          <NavItem icon={<LayoutDashboard size={24} />} onClick={() => navigate('/teacher/home')} />
          <NavItem icon={<BookOpen size={24} />} onClick={handleClassroomNav} />
          <NavItem icon={<BarChart2 size={24} />} active onClick={() => navigate('/teacher/analytics')} />
          <NavItem icon={<MessageSquare size={24} />} onClick={() => navigate('/teacher/doubts')} />
        </nav>
        <div onClick={() => api.logout()} className="shrink-0 cursor-pointer flex items-center justify-center w-12 h-12 rounded-full border-2 border-[#1800ad] bg-[#f6f4ee] hover:opacity-90 transition-all shadow-sm">
          <span className="text-[#1800ad] font-extrabold text-lg">{teacherName.charAt(0)}</span>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 md:ml-[80px] lg:ml-[100px] bg-[#f6f4ee] md:rounded-l-[40px] lg:rounded-l-[50px] p-4 md:p-8 lg:p-10 w-full overflow-y-auto custom-scrollbar pt-6 md:pt-8 pb-32 lg:pb-12 h-[100dvh] flex flex-col">
        
        {/* Header */}
        <header className="border-b-2 border-[#1800ad]/10 pb-4 mb-8 flex flex-col sm:flex-row sm:items-baseline justify-between gap-2.5">
          <div>
            <span className="text-[10px] font-black uppercase tracking-widest text-[#1800ad]/60 font-mono">Academic Diagnostic Suite</span>
            <h1 className="text-2xl md:text-3xl font-black text-[#1800ad] tracking-tight">
              Actionable Class Analytics
            </h1>
          </div>
          <p className="text-xs font-semibold text-[#1800ad]/70 leading-none">
            Review detailed understanding indicators, variables mapping, and conceptual blockages dynamically.
          </p>
        </header>

        {/* SECTION 1 - CLASS & SUBJECT AI INSIGHTS */}
        <section className="mb-10">
          <h2 className="text-xs font-black uppercase tracking-widest text-[#1800ad]/60 mb-4 flex items-center gap-2">
            <GraduationCap size={16} className="text-[#1800ad] stroke-[2.5]" />
            Section 1 — Class & Subject AI Insights
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {classInsights.map((insights) => {
              const isSelected = selectedClassId === insights.id;
              return (
                <div 
                  key={insights.id}
                  onClick={() => setSelectedClassId(insights.id)}
                  className={`bg-[#f6f4ee] rounded-3xl p-6 border-2 transition-all cursor-pointer shadow-sm relative overflow-hidden flex flex-col justify-between min-h-[175px] ${
                    isSelected 
                      ? 'border-[#1800ad] bg-[#1800ad]/5 ring-2 ring-[#1800ad]/10 scale-[1.01]' 
                      : 'border-[#1800ad]/15 hover:border-[#1800ad]/50 bg-white'
                  }`}
                >
                  <div>
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <span className="text-[9px] font-black uppercase tracking-wider bg-[#1800ad]/10 text-[#1800ad] px-2.5 py-1 rounded-full">
                          {insights.className}
                        </span>
                        <h3 className="text-base font-black text-[#1800ad] mt-1.5 font-montserrat">
                          {insights.subjectName}
                        </h3>
                      </div>
                      <span className="text-xs font-bold text-[#1800ad]/70 flex items-center gap-1 font-mono">
                        <Users size={12} /> {insights.studentCount} Students
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-1 grid-flow-col border-t border-[#1800ad]/10 pt-3">
                      <div className="text-center md:text-left">
                        <span className="block text-[8px] font-black uppercase tracking-wider text-[#1800ad]/60 leading-none mb-1">Understanding</span>
                        <span className="text-sm font-black text-[#1800ad]">{insights.understanding} <span className="text-[10px] opacity-60">/ 3</span></span>
                      </div>
                      <div className="text-center md:text-left">
                        <span className="block text-[8px] font-black uppercase tracking-wider text-[#1800ad]/60 leading-none mb-1">Reasoning</span>
                        <span className="text-sm font-black text-[#1800ad]">{insights.reasoning} <span className="text-[10px] opacity-60">/ 3</span></span>
                      </div>
                      <div className="text-center md:text-left">
                        <span className="block text-[8px] font-black uppercase tracking-wider text-[#1800ad]/60 leading-none mb-1">Expression</span>
                        <span className="text-sm font-black text-[#1800ad]">{insights.expression} <span className="text-[10px] opacity-60">/ 3</span></span>
                      </div>
                    </div>
                  </div>

                  {isSelected && (
                    <div className="absolute right-0 bottom-0 bg-[#1800ad] text-[#f6f4ee] text-[8px] font-black px-3 py-1 uppercase tracking-widest rounded-tl-xl">
                      Active Class Filter
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* SECTION 2 — COMMON MISCONCEPTIONS */}
        <section className="mb-10">
          <h2 className="text-xs font-black uppercase tracking-widest text-[#1800ad]/60 mb-4 flex items-center gap-2">
            <AlertTriangle size={15} className="text-[#1800ad] stroke-[2.5]" />
            Section 2 — Common Misconceptions Detected By AI
          </h2>

          <div className="bg-white rounded-3xl p-6 border-2 border-[#1800ad]/15 shadow-sm">
            <div className="flex items-center justify-between mb-4 flex-wrap gap-2 border-b border-[#1800ad]/10 pb-3">
              <div className="flex items-center gap-2">
                <span className="bg-[#1800ad] text-[#f6f4ee] text-[9px] font-black uppercase tracking-wider px-2.5 py-1 rounded-full">
                  {activeClassName}
                </span>
                <span className="text-sm font-black text-[#1800ad]">
                  {activeSubject} Misconceptions
                </span>
              </div>
              <span className="text-[10px] font-bold text-[#1800ad]/70 uppercase tracking-wider">
                Showing top AI evaluated concept barriers
              </span>
            </div>

            <div className="flex flex-col gap-3.5">
              {activeMisconceptions?.map((misconception, idx) => (
                <div 
                  key={idx}
                  className="p-4 rounded-2xl bg-[#f6f4ee]/50 border-2 border-[#1800ad]/10 hover:border-[#1800ad]/30 transition-all flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3.5"
                >
                  <div className="flex-1 flex gap-3 items-start">
                    <span className="bg-[#1800ad] text-[#f6f4ee] w-5 h-5 rounded-md shrink-0 flex items-center justify-center text-[10px] font-black font-mono">
                      {idx + 1}
                    </span>
                    <p className="text-xs font-black text-[#1800ad] leading-relaxed">
                      {misconception.title}
                    </p>
                  </div>
                  
                  <div className="bg-[#1800ad]/10 rounded-xl px-4 py-2 text-right shrink-0 min-w-[150px] border border-[#1800ad]/10 w-full sm:w-auto">
                    <span className="block text-[11px] font-black text-[#1800ad] leading-none mb-1">
                      {misconception.percentage}% affected
                    </span>
                    <span className="block text-[9px] font-semibold text-[#1800ad]/75 uppercase tracking-wider">
                      {misconception.count} / {activeClassInsight.studentCount} students
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* SECTION 3 — STUDENT PROGRESS */}
        <section className="mb-6">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <h2 className="text-xs font-black uppercase tracking-widest text-[#1800ad]/60 flex items-center gap-2">
              <Users size={16} className="text-[#1800ad]/80 stroke-[2.5]" />
              Section 3 — Student Progress for {activeClassName} {activeSubject}
            </h2>
            <span className="text-[10px] font-black text-amber-600 bg-amber-50 border border-amber-200 px-3.5 py-1 rounded-full uppercase tracking-wider animate-pulse">
              💡 Click any row to view full student AI evaluation trends
            </span>
          </div>

          <div className="bg-white rounded-3xl border-2 border-[#1800ad]/15 overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse font-sans">
                <thead>
                  <tr className="border-b border-[#1800ad]/10 text-[#1800ad]/65 font-black uppercase tracking-wider bg-[#1800ad]/5 font-montserrat">
                    <th className="py-4.5 px-6">Student Name</th>
                    <th className="py-4.5 px-6">Understanding (avg)</th>
                    <th className="py-4.5 px-6">Reasoning (avg)</th>
                    <th className="py-4.5 px-6">Expression (avg)</th>
                    <th className="py-2 px-6">Completed Chapters</th>
                    <th className="py-4.5 px-6">Syllabus Progress</th>
                    <th className="py-4.5 px-6 text-right">Interactive Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1800ad]/10 font-semibold text-[#1800ad]/90">
                  {studentsListForSelectedClass.map((student, index) => (
                    <tr 
                      key={index} 
                      onClick={() => {
                        setSelectedStudent(student);
                        setDrilldownStudentId(student.student_id);
                      }}
                      className="hover:bg-[#1800ad]/5 transition-colors cursor-pointer"
                    >
                      <td className="py-4 px-6 font-black text-[#1800ad] flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-full bg-[#1800ad] text-white flex items-center justify-center text-[11px] font-black border border-[#1800ad]/20">
                          {student.name.charAt(0)}
                        </div>
                        {student.name}
                      </td>
                      <td className="py-4 px-6 font-mono font-bold">{student.understanding} / 3.0</td>
                      <td className="py-4 px-6 font-mono font-bold">{student.reasoning} / 3.0</td>
                      <td className="py-4 px-6 font-mono font-bold">{student.expression} / 3.0</td>
                      <td className="py-4 px-6 max-w-[200px] truncate opacity-80">{student.completedChapters.join(', ')}</td>
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-3 w-full max-w-[140px]">
                          <div className="flex-1 bg-[#1800ad]/10 rounded-full h-2 overflow-hidden border border-[#1800ad]/5">
                            <div 
                              className="bg-[#1800ad] h-full rounded-full transition-all duration-500" 
                              style={{ width: `${student.progress}%` }}
                            />
                          </div>
                          <span className="font-mono text-[11px] font-black leading-none">{student.progress}%</span>
                        </div>
                      </td>
                      <td className="py-4 px-6 text-right">
                        <button className="text-[10px] font-black uppercase tracking-widest text-[#1800ad] border border-[#1800ad]/25 hover:border-[#1800ad] bg-[#f6f4ee] px-3.5 py-1.5 rounded-full transition-all inline-flex items-center gap-1.5 font-montserrat">
                          View details <ChevronRight size={12} className="stroke-[2.5]" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

      </main>

      {/* STUDENT DETAILED SCORECARD SIDE DRAWER / MODAL */}
      <AnimatePresence>
        {selectedStudent && (
          <div 
            onClick={() => {
              setSelectedStudent(null);
              setDrilldownStudentId(null);
            }}
            className="fixed inset-0 bg-[#1800ad]/60 backdrop-blur-sm z-50 flex items-center justify-end"
          >
            <motion.div
              onClick={(e) => e.stopPropagation()}
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="bg-[#f6f4ee] border-l-4 border-[#1800ad] h-full w-full max-w-lg shadow-2xl p-6 md:p-8 flex flex-col justify-between overflow-y-auto custom-scrollbar"
            >
              <div>
                
                {/* Header info */}
                <div className="flex items-start justify-between border-b border-[#1800ad]/15 pb-4.5 mb-6">
                  <div className="flex items-center gap-3.5">
                    <div className="w-12 h-12 rounded-full bg-[#1800ad] text-white flex items-center justify-center font-black text-lg">
                      {selectedStudent.name.charAt(0)}
                    </div>
                    <div>
                      <h3 className="text-lg font-black text-[#1800ad] leading-none mb-1.5 font-montserrat">
                        {selectedStudent.name}
                      </h3>
                      <span className="text-[9px] font-black uppercase tracking-widest bg-[#1800ad]/10 px-2 py-0.5 rounded text-[#1800ad]">
                        {activeClassName} {activeSubject} Profile
                      </span>
                    </div>
                  </div>
                  <button 
                    onClick={() => {
                      setSelectedStudent(null);
                      setDrilldownStudentId(null);
                    }}
                    className="p-1 rounded-full hover:bg-[#1800ad]/10 text-[#1800ad] transition-all"
                  >
                    <X size={20} className="stroke-[2.5]" />
                  </button>
                </div>

                {/* Overall completion bar */}
                <div className="bg-white rounded-2xl p-4.5 border-2 border-[#1800ad]/10 mb-6 flex items-center justify-between">
                  <div>
                    <span className="block text-[9px] font-black uppercase tracking-widest text-[#1800ad]/60 mb-1 leading-none">Completed Progress</span>
                    <span className="text-xl font-black text-[#1800ad]">{selectedStudent.progress}% Syllabus</span>
                  </div>
                  <div className="w-24 bg-[#1800ad]/10 h-3 rounded-full overflow-hidden border border-[#1800ad]/10">
                    <div className="bg-[#1800ad] h-full rounded-full" style={{ width: `${selectedStudent.progress}%` }} />
                  </div>
                </div>

                {/* Specific trend vectors (Understanding, Reasoning, Expression) */}
                <div className="mb-6">
                  <h4 className="text-[10px] font-black uppercase tracking-wider text-[#1800ad]/70 mb-3 flex items-center gap-1.5">
                    <TrendingUp size={13} className="stroke-[2.5]" />
                    AI Concept Component Metrics
                  </h4>
                  <div className="grid grid-cols-3 gap-2.5">
                    <div className="bg-white rounded-xl p-3 border border-[#1800ad]/10 text-center">
                      <span className="block text-[8px] font-black uppercase tracking-wide text-[#1800ad]/60 mb-1">Understanding</span>
                      <span className="text-base font-black text-[#1800ad] leading-none">{selectedStudent.understanding} <span className="text-[10px] opacity-50">/ 3</span></span>
                      <div className="w-full bg-[#1800ad]/10 h-1 rounded-full mt-2 overflow-hidden">
                        <div className="bg-[#1800ad] h-full rounded-full" style={{ width: `${(selectedStudent.understanding/3)*100}%` }} />
                      </div>
                    </div>

                    <div className="bg-white rounded-xl p-3 border border-[#1800ad]/10 text-center">
                      <span className="block text-[8px] font-black uppercase tracking-wide text-[#1800ad]/60 mb-1">Reasoning</span>
                      <span className="text-base font-black text-[#1800ad] leading-none">{selectedStudent.reasoning} <span className="text-[10px] opacity-50">/ 3</span></span>
                      <div className="w-full bg-[#1800ad]/10 h-1 rounded-full mt-2 overflow-hidden">
                        <div className="bg-[#1800ad] h-full rounded-full" style={{ width: `${(selectedStudent.reasoning/3)*100}%` }} />
                      </div>
                    </div>

                    <div className="bg-white rounded-xl p-3 border border-[#1800ad]/10 text-center">
                      <span className="block text-[8px] font-black uppercase tracking-wide text-[#1800ad]/60 mb-1">Expression</span>
                      <span className="text-base font-black text-[#1800ad] leading-none">{selectedStudent.expression} <span className="text-[10px] opacity-50">/ 3</span></span>
                      <div className="w-full bg-[#1800ad]/10 h-1 rounded-full mt-2 overflow-hidden">
                        <div className="bg-[#1800ad] h-full rounded-full" style={{ width: `${(selectedStudent.expression/3)*100}%` }} />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Drilldown details */}
                {loadingDrilldown ? (
                  <div className="py-8 flex flex-col items-center justify-center gap-2 mb-6">
                    <div className="w-6 h-6 border-2 border-[#1800ad]/20 border-t-[#1800ad] rounded-full animate-spin"></div>
                    <span className="text-[10px] font-bold text-[#1800ad]/60 animate-pulse font-montserrat">Loading detailed diagnostics...</span>
                  </div>
                ) : selectedStudentDrilldown ? (
                  <>
                    {/* Spoken Streak and Accuracy */}
                    <div className="grid grid-cols-2 gap-3 mb-6">
                      <div className="bg-white rounded-xl p-3 border border-[#1800ad]/10">
                        <span className="block text-[8px] font-black uppercase tracking-wide text-[#1800ad]/60 mb-0.5">Spoken Streak</span>
                        <span className="text-sm font-black text-[#1800ad]">{selectedStudentDrilldown.streak || 0} Days 🔥</span>
                      </div>
                      <div className="bg-white rounded-xl p-3 border border-[#1800ad]/10">
                        <span className="block text-[8px] font-black uppercase tracking-wide text-[#1800ad]/60 mb-0.5">Diagnostic Accuracy</span>
                        <span className="text-sm font-black text-[#1800ad]">{selectedStudentDrilldown.prediction_accuracy || 0}% Accuracy</span>
                      </div>
                    </div>

                    {/* Language Ratio */}
                    {selectedStudentDrilldown.language_ratio && Object.values(selectedStudentDrilldown.language_ratio).some((val: any) => val > 0) && (
                      <div className="mb-6 bg-white rounded-2xl p-4 border border-[#1800ad]/10">
                        <h4 className="text-[10px] font-black uppercase tracking-wider text-[#1800ad]/70 mb-3.5 flex items-center gap-1.5">
                          <Clock size={13} className="stroke-[2.5]" />
                          Spoken Language Preference
                        </h4>
                        <div className="flex flex-col gap-2.5">
                          {Object.entries(selectedStudentDrilldown.language_ratio).map(([lang, ratio]: [string, any]) => {
                            if (!ratio || ratio <= 0) return null;
                            return (
                              <div key={lang} className="flex items-center justify-between text-xs font-bold">
                                <span className="capitalize text-[#1800ad]/80">{lang}</span>
                                <div className="flex items-center gap-3.5 w-[70%]">
                                  <div className="flex-1 bg-[#1800ad]/10 h-2 rounded-full overflow-hidden">
                                    <div className="bg-[#1800ad] h-full rounded-full transition-all" style={{ width: `${ratio * 100}%` }} />
                                  </div>
                                  <span className="font-mono text-[10px] text-[#1800ad] w-8 text-right">{Math.round(ratio * 100)}%</span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Explain excerpts */}
                    {selectedStudentDrilldown.explain_excerpts && selectedStudentDrilldown.explain_excerpts.length > 0 && (
                      <div className="mb-6">
                        <h4 className="text-[10px] font-black uppercase tracking-wider text-[#1800ad]/70 mb-2.5 flex items-center gap-1.5">
                          <Award size={13} className="stroke-[2.5]" />
                          Explain-It Spoken Answers
                        </h4>
                        <div className="flex flex-col gap-2">
                          {selectedStudentDrilldown.explain_excerpts.map((exc: any, i: number) => (
                            <div key={i} className="bg-white p-3.5 rounded-xl border border-[#1800ad]/10 flex flex-col gap-1">
                              <div className="flex justify-between items-center text-[8px] font-black uppercase tracking-wider">
                                <span className="text-[#1800ad]/60 truncate max-w-[65%]">{exc.concept}</span>
                                <span className={exc.is_strong ? "text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded" : "text-amber-700 bg-amber-50 px-2 py-0.5 rounded"}>
                                  {exc.is_strong ? "Strong explanation" : "Needs support"}
                                </span>
                              </div>
                              <p className="text-xs italic text-[#1800ad] leading-relaxed mt-1 font-medium">{exc.text}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Attempt timeline */}
                    {selectedStudentDrilldown.score_timeline && selectedStudentDrilldown.score_timeline.length > 0 && (
                      <div className="mb-6">
                        <h4 className="text-[10px] font-black uppercase tracking-wider text-[#1800ad]/70 mb-2.5 flex items-center gap-1.5">
                          <TrendingUp size={13} className="stroke-[2.5]" />
                          Attempt Performance History
                        </h4>
                        <div className="flex flex-col gap-2">
                          {selectedStudentDrilldown.score_timeline.map((item: any, i: number) => (
                            <div key={i} className="bg-white p-3.5 rounded-xl border border-[#1800ad]/10 flex items-center justify-between gap-2">
                              <div className="truncate flex-1">
                                <span className="block text-xs font-black text-[#1800ad] truncate">{item.chapter_title}</span>
                                <span className="block text-[8px] font-semibold text-[#1800ad]/60 uppercase tracking-wide">Speech Explanation</span>
                              </div>
                              <div className="flex gap-1.5 text-[9px] font-mono font-black text-[#1800ad]/90 shrink-0">
                                <span title="Understanding" className="bg-[#1800ad]/5 px-2 py-1 rounded">U: {item.understanding}</span>
                                <span title="Reasoning" className="bg-[#1800ad]/5 px-2 py-1 rounded">R: {item.reasoning}</span>
                                <span title="Expression" className="bg-[#1800ad]/5 px-2 py-1 rounded">E: {item.expression}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                ) : null}

                {/* Completed chapters checklist */}
                <div className="mb-6">
                  <h4 className="text-[10px] font-black uppercase tracking-wider text-[#1800ad]/70 mb-2 flex items-center gap-1.5">
                    <BookOpenCheck size={13} className="stroke-[2.5]" />
                    Syllabus Chapters Completed
                  </h4>
                  <div className="flex flex-col gap-1.5">
                    {selectedStudent.completedChapters.map((ch: string, i: number) => (
                      <div key={i} className="flex items-center gap-2 text-xs font-semibold text-[#1800ad]/90 bg-white px-3 py-2 rounded-lg border border-[#1800ad]/10">
                        <span className="w-2 h-2 rounded-full bg-emerald-600 shrink-0" />
                        {ch}
                      </div>
                    ))}
                    {selectedStudent.completedChapters.length === 0 && (
                      <div className="text-xs font-semibold text-[#1800ad]/50 bg-white/50 px-3 py-2 rounded-lg border border-dashed border-[#1800ad]/10">
                        No chapters completed yet.
                      </div>
                    )}
                  </div>
                </div>

                {/* Active misconceptions ongoing */}
                <div className="mb-6">
                  <h4 className="text-[10px] font-black uppercase tracking-wider text-[#1800ad]/70 mb-2 flex items-center gap-1.5">
                    <AlertTriangle size={13} className="stroke-[2.5]" />
                    AI-Detected Misconceptions History
                  </h4>
                  <div className="flex flex-col gap-1.5">
                    {selectedStudent.recentMisconceptions.map((mis: string, i: number) => (
                      <div key={i} className="flex items-center gap-2 text-xs font-semibold text-rose-700 bg-rose-50 px-3 py-2 rounded-lg border border-rose-100">
                        <span className="w-2 h-2 rounded-full bg-rose-600 shrink-0 animate-pulse" />
                        {mis}
                      </div>
                    ))}
                    {selectedStudent.recentMisconceptions.length === 0 && (
                      <div className="text-xs font-semibold text-emerald-800 bg-emerald-50/50 px-3 py-2.5 rounded-lg border border-emerald-100/50">
                        🎉 No active misconceptions. Outstanding conceptual logic verified.
                      </div>
                    )}
                  </div>
                </div>

                {/* Recent AI Evaluation Activity Result */}
                <div className="mb-6">
                  <h4 className="text-[10px] font-black uppercase tracking-wider text-[#1800ad]/70 mb-2 flex items-center gap-1.5">
                    <MessageCircle size={13} className="stroke-[2.5]" />
                    Latest "Explain It" AI Evaluation Output
                  </h4>
                  {selectedStudent.recentAiResult ? (
                    <div className="bg-white rounded-xl p-4 border border-[#1800ad]/15 flex flex-col gap-2.5">
                      <div>
                        <span className="block text-[8px] font-black uppercase tracking-widest text-[#1800ad]/50 mb-1 leading-none">Evaluated Prompt</span>
                        <span className="text-[11px] font-black text-[#1800ad] leading-snug">{selectedStudent.recentAiResult.prompt}</span>
                      </div>
                      <div>
                        <span className="block text-[8px] font-black uppercase tracking-widest text-[#1800ad]/50 mb-1 leading-none">Student Response Translation</span>
                        <p className="text-[11px] italic font-semibold text-[#1800ad]/85 leading-relaxed bg-[#f6f4ee]/70 p-2.5 rounded-lg border border-[#1800ad]/10">
                          {selectedStudent.recentAiResult.answer}
                        </p>
                      </div>
                      <div className="border-t border-[#1800ad]/10 pt-2.5 flex justify-between items-end">
                        <div>
                          <span className="block text-[8px] font-black uppercase tracking-widest text-[#1800ad]/50 mb-0.5 leading-none font-montserrat font-black font-semibold">AI Diagnostic Feedback</span>
                          <span className="text-[10px] font-bold text-[#1800ad]/90">{selectedStudent.recentAiResult.feedback}</span>
                        </div>
                        <span className="text-xs font-black bg-[#1800ad] text-[#f6f4ee] px-2.5 py-1 rounded">Score: {selectedStudent.recentAiResult.score}</span>
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs font-semibold text-[#1800ad]/60 bg-white p-4 rounded-xl border border-[#1800ad]/10">
                      No speech explanation activities recorded yet for this student.
                    </div>
                  )}
                </div>

              </div>

              <button 
                onClick={() => {
                  setSelectedStudent(null);
                  setDrilldownStudentId(null);
                }}
                className="w-full bg-[#1800ad] hover:bg-opacity-90 text-[#f6f4ee] py-3.5 rounded-full text-xs font-black uppercase tracking-widest transition-all text-center font-montserrat shadow-md mt-6"
              >
                Done view profile
              </button>

            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </div>
  );
}
