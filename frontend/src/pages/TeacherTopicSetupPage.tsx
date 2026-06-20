import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'motion/react';
import { 
  ArrowLeft, 
  LayoutDashboard, 
  BookOpen, 
  BarChart2, 
  MessageSquare,
  CheckCircle2, 
  Loader2, 
  Flame, 
  Calendar,
  FileText,
  Users,
  Library,
  Search,
  X,
  Zap,
  Clock,
  Play,
  HelpCircle,
  Sliders,
  AlertCircle,
  Check,
  Sparkles
} from 'lucide-react';
import { NavItem } from '../components/NavItem';
import { api } from '../lib/api';
const INTERACTIVE_ASSIGNMENT_TYPES = [
  { type: 'explain_ai', label: 'Explain It', icon: 'HelpCircle', desc: 'Student explains a topic to a curious 10-year-old AI, testing their understanding through teaching.', color: 'bg-purple-100 text-purple-800 border-purple-300' },
  { type: 'predict_ai', label: 'Predict It', icon: 'Sliders', desc: 'Student predicts outcomes of scientific experiments before seeing the result, building hypothesis skills.', color: 'bg-blue-100 text-blue-800 border-blue-300' },
  { type: 'spot_it', label: 'Spot It', icon: 'AlertCircle', desc: 'Student identifies real-world applications of scientific concepts through riddles and scenarios.', color: 'bg-amber-100 text-amber-800 border-amber-300' },
  { type: 'interactive_quiz', label: 'Interactive Quiz', icon: 'HelpCircle', desc: 'Timed interactive quiz that tests knowledge with engaging multiple-choice questions.', color: 'bg-rose-100 text-rose-800 border-rose-300' },
];

export const getSketchfabEmbedUrl = (url: string | null | undefined): string => {
  if (!url) return '';
  if (url.includes('/embed')) return url;
  if (url.includes('sketchfab.com')) {
    const parts = url.split('/');
    const filteredParts = parts.filter(Boolean);
    const lastPart = filteredParts[filteredParts.length - 1];
    const uidMatch = lastPart.match(/([a-f0-9]{32})/i);
    if (uidMatch) {
      return `https://sketchfab.com/models/${uidMatch[1]}/embed`;
    }
    if (/^[a-f0-9]{32}$/i.test(lastPart)) {
      return `https://sketchfab.com/models/${lastPart}/embed`;
    }
  }
  return url;
};

export function TeacherTopicSetupPage() {
  const { classId, chapterId, topicId } = useParams<{ classId: string; chapterId: string; topicId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as { payload_json?: any, external_url?: string } | null;

  const [resolvedChapter, setResolvedChapter] = useState<any | null>(null);
  const [activeTopic, setActiveTopic] = useState<any | null>(null);
  const [topicAssets, setTopicAssets] = useState<any[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [isLoadingChapter, setIsLoadingChapter] = useState(true);
  const [resolvedClass, setResolvedClass] = useState<any | null>(null);
  const [activeAsset, setActiveAsset] = useState<any | null>(() => {
    // If state is passed via navigate, initialize activeAsset immediately for smoother transitions
    if (state && (state.payload_json !== undefined || state.external_url !== undefined)) {
      return {
        asset_id: topicId,
        asset_type: '', // Will be updated by API response
        title: 'Loading...',
        description: 'Loading details...',
        generation_status: 'ready',
        external_url: state.external_url || null,
        payload_json: state.payload_json || {}
      };
    }
    return null;
  });
  const [interactiveStatuses, setInteractiveStatuses] = useState<Record<string, 'idle' | 'generating' | 'ready' | 'failed'>>({});
  const [interactiveErrors, setInteractiveErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!classId || !chapterId || !topicId) return;
    const loadChapterAndAsset = async () => {
      setIsLoadingChapter(true);
      try {
        // Fetch and resolve the class metadata
        try {
          const classes = await api.get('/teachers/classes');
          const rawId = (classId || '').toLowerCase().trim();
          
          const normalizeGrade = (g: any): string => {
            if (g === null || g === undefined) return '';
            const str = String(g).trim().toLowerCase();
            const digits = str.replace(/\D/g, '');
            return digits || str;
          };

          const normalizeSubject = (s: any): string => {
            if (s === null || s === undefined) return '';
            return String(s).trim().toLowerCase().replace(/[\s\-_]+/g, ' ');
          };

          let parsedGrade = '';
          let parsedSubject = '';

          const matchedClass = classes.find((c: any) => {
            if (c.class_id && c.class_id.toLowerCase() === rawId) {
              parsedGrade = c.grade;
              parsedSubject = c.subject;
              return true;
            }

            const parts = rawId.split('-');
            const classIdx = parts.indexOf('class');
            let gradeVal = '';
            if (classIdx !== -1 && parts[classIdx + 1]) {
              gradeVal = parts[classIdx + 1];
            } else {
              const match = rawId.match(/\d+/);
              if (match) gradeVal = match[0];
            }
            const subjectPart = parts
              .filter((p) => p !== 'class' && p !== gradeVal)
              .join(' ');

            parsedGrade = gradeVal;
            parsedSubject = subjectPart;

            const classGradeNormalized = normalizeGrade(c.grade);
            const targetGradeNormalized = normalizeGrade(gradeVal);

            const classSubjectNormalized = normalizeSubject(c.subject);
            const targetSubjectNormalized = normalizeSubject(subjectPart);

            if (classGradeNormalized === targetGradeNormalized && classSubjectNormalized === targetSubjectNormalized) {
              return true;
            }

            const numericGrade = parseInt(targetGradeNormalized, 10);
            if (
              !isNaN(numericGrade) &&
              numericGrade >= 6 &&
              numericGrade <= 10 &&
              classGradeNormalized === targetGradeNormalized &&
              classSubjectNormalized === 'science' &&
              ['physics', 'chemistry', 'biology'].includes(targetSubjectNormalized)
            ) {
              return true;
            }

            return false;
          });

          if (matchedClass) {
            setResolvedClass(matchedClass);
          }
        } catch (classErr) {
          console.error("Failed to load class details:", classErr);
        }

        const data = await api.get(`/teachers/classes/${classId}/chapters/${chapterId}`);
        setResolvedChapter(data);
        console.log("Fetched chapter details in activity subpage:", data);
        const topic = data?.topics?.find((t: any) => t.topic_id === topicId);
        if (topic) {
          setActiveTopic(topic);
          const assets = [...(topic.assets || [])].sort((a: any, b: any) => {
            const order = ['concept_video', 'simulation', 'three_d_model'];
            return order.indexOf(a.asset_type) - order.indexOf(b.asset_type);
          });
          setTopicAssets(assets);
          const initialAsset = assets[0] || null;
          setSelectedAssetId(initialAsset?.asset_id || null);
          setActiveAsset(initialAsset);
          console.log("Fetched active topic details in activity subpage:", topic);
        } else if (data && data.assets) {
          const asset = data.assets.find((a: any) => a.asset_id === topicId);
          setActiveTopic(null);
          setTopicAssets([]);
          setSelectedAssetId(asset?.asset_id || null);
          setActiveAsset(asset);
          console.log("Fetched active asset details in activity subpage:", asset);
        }
      } catch (err) {
        console.error("Failed to fetch chapter/asset details:", err);
      } finally {
        setIsLoadingChapter(false);
      }
    };
    loadChapterAndAsset();
  }, [classId, chapterId, topicId]);

  // Console log asset render
  if (activeAsset) {
    console.log("Rendering asset details on activity subpage:", activeAsset);
  }

  const activeChapterName = resolvedChapter ? resolvedChapter.title : 'Loading...';
  const activeChapterNumber = resolvedChapter ? `Ch-${resolvedChapter.sequence_number}` : 'Ch-01';
  const activeTopicTitle = activeTopic ? activeTopic.title : (activeAsset ? activeAsset.title : 'Loading...');
  const activeTopicNumber = activeTopic ? `Topic ${activeTopic.sequence_number + 1}` : (activeAsset ? activeAsset.asset_type.replace('_', ' ') : '01');

  const [isSuccessModalOpen, setIsSuccessModalOpen] = useState(false);
  const [assignedItemTitle, setAssignedItemTitle] = useState('');
  const [assignmentNotes, setAssignmentNotes] = useState('');
  const [assignmentDeadline, setAssignmentDeadline] = useState('2026-06-25');
  const [publishing, setPublishing] = useState(false);
  const [success, setSuccess] = useState(false);
  const [assignError, setAssignError] = useState<string | null>(null);

  // Content Library states
  const [showLibrary, setShowLibrary] = useState(false);
  const [libraryTargetAsset, setLibraryTargetAsset] = useState<any | null>(null);
  const [libraryItems, setLibraryItems] = useState<any[]>([]);
  const [libraryLoading, setLibraryLoading] = useState(false);
  const [librarySearch, setLibrarySearch] = useState('');
  const [libraryPreview, setLibraryPreview] = useState<string | null>(null);
  const [adopting, setAdopting] = useState<string | null>(null);

  const openLibrary = async (asset: any) => {
    if (!resolvedClass) return;
    setLibraryTargetAsset(asset);
    setShowLibrary(true);
    setLibraryLoading(true);
    setLibraryPreview(null);
    try {
      const items = await api.get(
        `/teachers/library/assets?asset_type=concept_video&grade=${resolvedClass.grade}&subject=${resolvedClass.subject}`
      );
      setLibraryItems(items || []);
    } catch (err) {
      console.error("Failed to load library items:", err);
    } finally {
      setLibraryLoading(false);
    }
  };

  const handleAdoptFromLibrary = async (libraryAssetId: string) => {
    if (!classId || !chapterId || !libraryTargetAsset) return;
    setAdopting(libraryAssetId);
    try {
      const updatedAsset = await api.post(
        `/teachers/library/classes/${classId}/chapters/${chapterId}/assets/${libraryTargetAsset.asset_id}/adopt`,
        { library_asset_id: libraryAssetId }
      );
      updateTopicAsset(updatedAsset.asset || updatedAsset);
      setShowLibrary(false);
    } catch (err) {
      console.error("Failed to adopt library asset:", err);
    } finally {
      setAdopting(null);
    }
  };

  const mapAssetTypeToAssignmentType = (assetType: string): string => {
    switch (assetType) {
      case 'concept_video': return 'video';
      case 'simulation': return 'simulation';
      case 'three_d_model': return 'model';
      case 'quiz': return 'quiz';
      case 'explain_it': return 'explain_ai';
      case 'predict_it': return 'predict_ai';
      case 'spot_it': return 'spot_it';
      case 'connect_it': return 'connect_it';
      default: return assetType;
    }
  };

  const handlePublishAssignment = async () => {
    if (!classId || !chapterId || !activeAsset) return;
    setPublishing(true);
    setAssignError(null);
    try {
      const assignmentType = mapAssetTypeToAssignmentType(activeAsset.asset_type);
      await api.post(`/teachers/classes/${classId}/assignments`, {
        chapter_id: chapterId,
        assignment_type: assignmentType,
        title: activeAsset.title,
        instructions: assignmentNotes,
      });
      setSuccess(true);
      // Wait 1.5s then navigate back to chapter setup page
      setTimeout(() => {
        setIsSuccessModalOpen(false);
        navigate(`/teacher/chapter-setup/${classId}/${chapterId}`);
      }, 1500);
    } catch (err: any) {
      console.error("Failed to create assignment:", err);
      setAssignError(err?.detail || err?.message || 'Failed to create assignment. Please try again.');
    } finally {
      setPublishing(false);
    }
  };

  const [regenText, setRegenText] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState<string>('english');
  const [generationEndsAt, setGenerationEndsAt] = useState<number | null>(null);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const isGenerating = generationEndsAt !== null;
  const selectedAsset = activeAsset;

  // Check if payload_json is empty or minimal (scaffolding only)
  const isMinimalOrPlaceholder = 
    !activeTopic && (!activeAsset ||
    !activeAsset.payload_json ||
    Object.keys(activeAsset.payload_json).length === 0 ||
    (activeAsset.generation_status !== 'ready' && activeAsset.payload_json.placeholder === true) ||
    (activeAsset.asset_type === 'quiz' && !activeAsset.payload_json.questions && !activeAsset.payload_json.quiz) ||
    (['explain_it', 'predict_it', 'spot_it', 'connect_it'].includes(activeAsset.asset_type) && !activeAsset.payload_json.instructions));

  const updateTopicAsset = (nextAsset: any) => {
    setSelectedAssetId(nextAsset.asset_id);
    setActiveAsset(nextAsset);
    setGenerationEndsAt(null);
    setGenerationError(null);
    if (activeTopic) {
      setTopicAssets(prev => prev.map(asset => asset.asset_id === nextAsset.asset_id ? nextAsset : asset));
    }
  };

  const handleGenerateSelectedAsset = async () => {
    if (!activeTopic || !selectedAsset || !classId || !chapterId) return;

    setGenerationError(null);
    const estimatedSeconds = selectedAsset.asset_type === 'concept_video' ? 180 : selectedAsset.asset_type === 'simulation' ? 75 : 45;
    setGenerationEndsAt(Date.now() + estimatedSeconds * 1000);

    try {
      const response = await api.post(`/teachers/classes/${classId}/chapters/${chapterId}/topics/${activeTopic.topic_id}/assets/${selectedAsset.asset_id}/generate`, {
        instructions: regenText.trim() || null,
        language: selectedLanguage,
      });
      const generatedAsset = response.asset || response;
      updateTopicAsset(generatedAsset);
      setRegenText('');
      setGenerationEndsAt(null);
    } catch (err: any) {
      console.error('Failed to generate topic asset:', err);
      setGenerationError(err?.detail || err?.message || 'Generation failed.');
      setGenerationEndsAt(null);
    }
  };

  return (
    <div className="flex flex-1 w-full bg-[#1800ad] font-montserrat text-[#1800ad] relative">
      
      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex w-[80px] lg:w-[100px] flex-col items-center justify-between py-8 fixed top-0 bottom-0 left-0 h-full shrink-0 bg-[#1800ad] text-[#f6f4ee] z-30 font-montserrat">
        <div className="flex items-center justify-center shrink-0 mt-4 cursor-pointer" onClick={() => navigate('/')}>
          <span className="text-[#f6f4ee] font-val text-[42px] leading-none tracking-widest mt-1 mr-1">M</span>
        </div>

        <nav className="flex flex-col gap-6 w-full items-center my-auto">
          <NavItem icon={<LayoutDashboard size={24} />} onClick={() => navigate('/teacher/home')} />
          <NavItem icon={<BookOpen size={24} />} active onClick={() => navigate(`/teacher/class/${classId}`)} />
          <NavItem icon={<BarChart2 size={24} />} onClick={() => navigate(classId ? `/teacher/analytics/${classId}` : '/teacher/analytics')} />
          <NavItem icon={<MessageSquare size={24} />} onClick={() => navigate('/teacher/doubts')} />
        </nav>

        <div onClick={() => api.logout()} className="shrink-0 cursor-pointer flex items-center justify-center w-12 h-12 rounded-full border-2 border-[#1800ad] bg-[#f6f4ee] hover:opacity-90 transition-all shadow-sm">
          <span className="text-[#1800ad] font-montserrat font-black text-lg">P</span>
        </div>
      </aside>

      {/* Main Container */}
      <main className="flex-1 md:ml-[80px] lg:ml-[100px] bg-[#f6f4ee] md:rounded-l-[40px] lg:rounded-l-[50px] p-5 md:pl-10 lg:pl-12 xl:pl-16 md:pr-8 lg:pr-10 w-full relative flex flex-col font-montserrat min-h-[100dvh]">
        <div className="max-w-[1300px] w-full mx-auto flex-1 flex flex-col">
          {/* Back Link Header */}
          <div className="flex items-center gap-3 mb-6 shrink-0">
            <button 
              onClick={() => navigate(`/teacher/chapter-setup/${classId}/${chapterId}`)}
              className="p-2 border-2 border-[#1800ad] rounded-full text-[#1800ad] hover:bg-[#1800ad]/10 transition-all font-montserrat flex items-center justify-center"
            >
              <ArrowLeft size={16} className="stroke-[3]" />
            </button>
            <span className="text-xs font-bold uppercase tracking-wider opacity-85">
              Back to Chapter Setup
            </span>
          </div>

        {/* Dynamic Topic Context Area */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-6 mb-8 border-b-2 border-[#1800ad]/15 shrink-0">
          <div>
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <span className="text-[10px] font-black uppercase tracking-widest bg-[#1800ad] text-[#f6f4ee] px-3 py-1 rounded-full">
                {activeChapterNumber} • {activeTopicNumber}
              </span>
              <span className="text-[10px] font-bold text-[#1800ad] bg-[#1800ad]/10 px-3 py-1 rounded-full uppercase tracking-wider">
                {activeChapterName}
              </span>
            </div>
            <h1 className="text-3xl md:text-4xl font-black text-[#1800ad] tracking-tight">
              {activeTopicTitle}
            </h1>
          </div>
        </div>

        {activeTopic && topicAssets.length > 0 && (
          <div className="mb-6 flex flex-col gap-3">
            <span className="text-xs font-black uppercase tracking-widest text-[#1800ad]/65">Topic Resources</span>
            <div className="flex flex-wrap gap-2">
              {topicAssets.map((asset) => (
                <button
                  key={asset.asset_id}
                  onClick={() => updateTopicAsset(asset)}
                  className={`px-3.5 py-2 rounded-full border text-[11px] font-black uppercase tracking-wider transition-all ${
                    selectedAssetId === asset.asset_id
                      ? 'bg-[#1800ad] text-[#f6f4ee] border-[#1800ad]'
                      : 'bg-white text-[#1800ad] border-[#1800ad]/20 hover:bg-[#1800ad]/5'
                  }`}
                >
                  {asset.title}
                </button>
              ))}
            </div>
          </div>
        )}

        {isLoadingChapter || !activeAsset ? (
          <div className="flex flex-col items-center justify-center min-h-[50vh] text-[#1800ad] flex-1">
            <Loader2 className="w-12 h-12 animate-spin mb-4" />
            <span className="text-xs font-bold uppercase tracking-widest animate-pulse">Loading activity details...</span>
          </div>
        ) : (
          <div className="w-full flex-1 flex flex-col gap-6">
            
            {/* Header / Meta */}
            <div className="bg-[#1800ad]/5 p-6 rounded-[28px] border-2 border-[#1800ad]/15 flex flex-col sm:flex-row sm:items-start justify-between gap-4">
              <div className="flex-1">
                <span className="text-[10px] font-black uppercase tracking-wider text-[#1800ad]/60 mb-1.5 block animate-pulse font-mono">
                  {activeAsset.asset_type.replace('_', ' ')} Resource
                </span>
                <h2 className="text-xl sm:text-2xl font-black text-[#1800ad] leading-tight">
                  {activeAsset.title}
                </h2>
                <p className="text-xs sm:text-sm text-[#1800ad]/80 font-semibold mt-2 leading-relaxed">
                  {activeAsset.description}
                </p>
              </div>
              <button
                onClick={() => {
                  setAssignedItemTitle(activeAsset.title);
                  setAssignmentNotes(`Hey students! Please complete this interactive topic resource on "${activeAsset.title}".`);
                  setSuccess(false);
                  setAssignError(null);
                  setIsSuccessModalOpen(true);
                }}
                className="shrink-0 bg-[#1800ad] text-[#f6f4ee] hover:bg-amber-300 hover:text-[#1800ad] px-6 py-3 rounded-full text-xs font-black uppercase tracking-widest transition-all shadow-md flex items-center gap-1.5 h-fit self-end sm:self-start"
              >
                <CheckCircle2 size={13} className="stroke-[3]" /> Assign to Class
              </button>
            </div>

            {/* Content Section */}
            <div className="bg-white p-6 rounded-[28px] border-2 border-[#1800ad]/15 flex flex-col gap-4">
              <h3 className="text-sm font-black uppercase tracking-widest text-[#1800ad] border-b border-[#1800ad]/10 pb-2">
                Content
              </h3>

              {activeTopic && selectedAsset && (
                <div className="bg-[#1800ad]/5 p-4 rounded-[24px] border border-[#1800ad]/10 flex flex-col gap-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-[10px] font-black uppercase tracking-wider text-[#1800ad]/60">Generation Workspace</div>
                      <div className="text-sm font-black text-[#1800ad]">{selectedAsset.title}</div>
                    </div>
                    <span className={`px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-wider ${selectedAsset.generation_status === 'ready' ? 'bg-emerald-100 text-emerald-800' : isGenerating ? 'bg-amber-100 text-amber-800 animate-pulse' : 'bg-gray-100 text-gray-700'}`}>
                      {selectedAsset.generation_status === 'ready' ? 'Ready' : isGenerating ? 'Generating...' : 'Not set up yet'}
                    </span>
                  </div>

                  <textarea
                    value={regenText}
                    onChange={(e) => setRegenText(e.target.value)}
                    rows={3}
                    placeholder="Optional: add teacher notes, examples, or style guidance..."
                    className="w-full bg-[#f6f4ee] text-[#1800ad] placeholder-[#1800ad]/40 border border-[#1800ad]/20 p-3 rounded-xl text-xs font-semibold focus:outline-none focus:border-[#1800ad] resize-none"
                  />

                  <div className="flex items-center justify-between gap-3 flex-wrap">
                    <label className="text-[10px] font-black uppercase tracking-wider text-[#1800ad]/65">
                      Target Video/Audio Language
                    </label>
                    <select
                      value={selectedLanguage}
                      onChange={(e) => setSelectedLanguage(e.target.value)}
                      className="bg-[#f6f4ee] text-[#1800ad] text-xs font-bold border border-[#1800ad]/20 px-3 py-1.5 rounded-xl outline-none focus:border-[#1800ad] cursor-pointer"
                    >
                      <option value="english">English</option>
                      <option value="hindi">Hindi (हिंदी)</option>
                      <option value="gujarati">Gujarati (ગુજરાતી)</option>
                      <option value="marathi">Marathi (मराठी)</option>
                      <option value="telugu">Telugu (తెలుగు)</option>
                      <option value="tamil">Tamil (தமிழ்)</option>
                      <option value="bengali">Bengali (বাংলা)</option>
                    </select>
                  </div>

                  {generationError && (
                    <div className="text-[11px] font-bold text-rose-600">{generationError}</div>
                  )}

                  <div className="flex items-center justify-between gap-3 flex-wrap">
                    <div className="text-[10px] font-black uppercase tracking-wider text-[#1800ad]/65">
                      {isGenerating ? `Expected time left: ${Math.max(0, Math.ceil((generationEndsAt! - now) / 1000))}s` : 'Generation ETA depends on asset type'}
                    </div>
                    <div className="flex items-center gap-2">
                      {selectedAsset.asset_type === 'concept_video' && (
                        <button
                          type="button"
                          onClick={() => openLibrary(selectedAsset)}
                          disabled={isGenerating}
                          className={`px-3.5 py-2 border rounded-full text-[11px] font-black flex items-center gap-1 leading-none transition-all ${
                            isGenerating
                              ? 'border-gray-200 text-gray-400 cursor-not-allowed'
                              : 'border-[#1800ad]/40 text-[#1800ad] hover:bg-[#1800ad]/5'
                          }`}
                          title="Pick from shared content library"
                        >
                          <Library size={11} /> Library
                        </button>
                      )}
                      <button
                        onClick={handleGenerateSelectedAsset}
                        disabled={isGenerating}
                        className="px-4 py-2 rounded-full bg-[#1800ad] text-[#f6f4ee] text-[11px] font-black uppercase tracking-widest flex items-center gap-1 disabled:opacity-60 disabled:cursor-not-allowed"
                      >
                        {isGenerating ? 'Generating...' : selectedAsset.generation_status === 'ready' ? 'Regenerate' : 'Generate'}
                      </button>
                    </div>
                  </div>
                </div>
              )}
              
              {isMinimalOrPlaceholder ? (
                <p className="text-xs sm:text-sm text-[#1800ad]/60 font-semibold italic">
                  Content is being prepared by your teacher.
                </p>
              ) : (
                <div className="flex flex-col gap-4">
                  {/* Detailed renderer for Quiz payload */}
                  {activeAsset.asset_type === 'quiz' && (activeAsset.payload_json.questions || activeAsset.payload_json.quiz) && (
                    <div className="flex flex-col gap-4">
                      <p className="text-xs text-[#1800ad]/80 font-bold uppercase tracking-wider">Generated Assessment Questions:</p>
                      {(activeAsset.payload_json.questions || activeAsset.payload_json.quiz).map((q: any, i: number) => (
                        <div key={i} className="bg-[#1800ad]/5 p-4 rounded-xl border border-[#1800ad]/10 flex flex-col gap-2">
                          <span className="text-xs font-black text-[#1800ad]">Question {i + 1}: {q.question || q.questionText}</span>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-1">
                            {q.options && q.options.map((opt: string, optIdx: number) => (
                              <div 
                                key={optIdx} 
                                className={`px-4 py-2 border rounded-full text-xs font-semibold ${
                                  optIdx === q.correctAnswer || opt === q.correctAnswer
                                    ? 'border-emerald-500 bg-emerald-50 text-emerald-800' 
                                    : 'border-[#1800ad]/20 text-[#1800ad]/80'
                                }`}
                              >
                                {opt}
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                    {/* Detailed renderer for explain_it, predict_it, spot_it, connect_it */}
                    {['explain_it', 'predict_it', 'spot_it', 'connect_it'].includes(activeAsset.asset_type) && (
                      <div className="text-xs text-[#1800ad]/85 font-semibold leading-relaxed flex flex-col gap-3">
                        {activeAsset.payload_json.instructions ? (
                          <div className="bg-[#1800ad]/5 p-4 rounded-xl border border-[#1800ad]/10">
                            <span className="block text-[10px] font-black uppercase tracking-wider text-[#1800ad]/60 mb-1">Pedagogical Instructions:</span>
                            <p className="text-xs sm:text-sm text-[#1800ad] whitespace-pre-wrap">{activeAsset.payload_json.instructions}</p>
                          </div>
                        ) : (
                          Object.keys(activeAsset.payload_json).filter(k => k !== 'placeholder' && k !== 'chapter_id' && k !== 'asset_type' && k !== 'provider' && k !== 'integration_target').map((key) => {
                            const val = activeAsset.payload_json[key];
                            if (typeof val === 'object') return null;
                            return (
                              <div key={key} className="flex justify-between items-center border-b border-[#1800ad]/5 py-1">
                                <span className="capitalize font-bold text-[#1800ad]/60">{key.replace('_', ' ')}:</span>
                                <span className="text-[#1800ad] font-extrabold">{String(val)}</span>
                              </div>
                            );
                          })
                        )}
                      </div>
                    )}

                    {/* General payload fallback list for other asset types if any */}
                    {!['quiz', 'explain_it', 'predict_it', 'spot_it', 'connect_it'].includes(activeAsset.asset_type) && (
                      <div className="text-xs text-[#1800ad]/85 font-semibold leading-relaxed flex flex-col gap-3">
                        {Object.keys(activeAsset.payload_json).filter(k => k !== 'placeholder' && k !== 'chapter_id' && k !== 'asset_type' && k !== 'provider' && k !== 'integration_target').map((key) => {
                          const val = activeAsset.payload_json[key];
                          if (typeof val === 'object') return null;
                          return (
                            <div key={key} className="flex justify-between items-center border-b border-[#1800ad]/5 py-1">
                              <span className="capitalize font-bold text-[#1800ad]/60">{key.replace('_', ' ')}:</span>
                              <span className="text-[#1800ad] font-extrabold">{String(val)}</span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Embedded Viewport / Link Section */}
              {activeAsset.external_url && (
                <div className="bg-white p-6 rounded-[28px] border-2 border-[#1800ad]/15 flex flex-col gap-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#1800ad]/10 pb-2">
                    <h3 className="text-sm font-black uppercase tracking-widest text-[#1800ad]">
                      Interactive Live Preview
                    </h3>
                    <a 
                      href={activeAsset.external_url} 
                      target="_blank" 
                      rel="noreferrer" 
                      className="text-xs font-bold text-[#1800ad] hover:underline flex items-center gap-1"
                    >
                      Open in new tab &rarr;
                    </a>
                  </div>

                  <div className="w-full bg-[#1800ad]/5 rounded-2xl overflow-hidden relative border-2 border-[#1800ad] shadow-inner animate-fadeIn" style={{ height: '450px' }}>
                    {activeAsset.asset_type === 'concept_video' ? (
                      activeAsset.external_url.includes('youtube.com') || activeAsset.external_url.includes('youtu.be') ? (
                        <iframe
                          src={activeAsset.external_url.replace('watch?v=', 'embed/')}
                          title="Video Player"
                          allowFullScreen
                          className="w-full h-full border-0"
                        />
                      ) : (
                        <video 
                          src={activeAsset.external_url} 
                          controls 
                          className="w-full h-full object-contain bg-black" 
                        />
                      )
                    ) : activeAsset.asset_type === 'simulation' ? (
                      <iframe
                        src={activeAsset.external_url}
                        title="Simulation Embed"
                        allowFullScreen
                        className="w-full h-full border-0"
                        style={{ background: '#ffffff' }}
                      />
                    ) : activeAsset.asset_type === 'three_d_model' ? (
                      <iframe
                        src={getSketchfabEmbedUrl(activeAsset.external_url)}
                        title="3D Model Viewer"
                        allowFullScreen
                        className="w-full h-full border-0"
                        style={{ background: '#ffffff' }}
                      />
                    ) : (
                      <iframe
                        src={activeAsset.external_url}
                        title="Asset Viewport"
                        allowFullScreen
                        className="w-full h-full border-0"
                        style={{ background: '#ffffff' }}
                      />
                    )}
                  </div>
                </div>
              )}

              {/* ─── Interactive Modes Section ─── */}
              <div className="border-t-2 border-[#1800ad]/15 pt-6">
                <h2 className="text-base font-black text-[#1800ad] tracking-tight mb-1">
                  AI Interactive Modes
                </h2>
                <p className="text-[11px] font-semibold opacity-75 mb-4">
                  Click any mode to generate and assign an AI-powered interactive activity to the class.
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                  {INTERACTIVE_ASSIGNMENT_TYPES.map((mode) => {
                    const status = interactiveStatuses[mode.type] || 'idle';
                    const isGenerating = status === 'generating';
                    const isReady = status === 'ready';
                    const isFailed = status === 'failed';
                    const errorMsg = interactiveErrors[mode.type];
                    return (
                      <div
                        key={mode.type}
                        className={`border-2 rounded-[20px] p-4 flex flex-col gap-3 transition-all ${
                          isReady
                            ? 'border-emerald-400 bg-emerald-50/50'
                            : isFailed
                            ? 'border-rose-300 bg-rose-50/50'
                            : 'border-[#1800ad]/15 bg-[#f6f4ee] hover:border-[#1800ad]/40'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className={`p-2 rounded-xl ${isReady ? 'bg-emerald-500 text-white' : 'bg-[#1800ad]/5 text-[#1800ad] border border-[#1800ad]/15'}`}>
                            {mode.icon === 'HelpCircle' && <HelpCircle size={16} />}
                            {mode.icon === 'Sliders' && <Sliders size={16} />}
                            {mode.icon === 'AlertCircle' && <AlertCircle size={16} />}
                          </span>
                          {isReady && (
                            <span className="text-[10px] font-black text-emerald-600 bg-emerald-100 px-2 py-0.5 rounded-full">Assigned</span>
                          )}
                          {isFailed && (
                            <span className="text-[10px] font-black text-rose-600 bg-rose-100 px-2 py-0.5 rounded-full">Failed</span>
                          )}
                        </div>
                        <div>
                          <h3 className="font-black text-xs text-[#1800ad] mb-0.5">{mode.label}</h3>
                          <p className="text-[10px] font-semibold text-[#1800ad]/70 leading-relaxed">{mode.desc}</p>
                        </div>
                        <button
                          type="button"
                          disabled={isGenerating || isReady}
                          onClick={async () => {
                            if (isGenerating || isReady || !classId || !chapterId) return;
                            setInteractiveStatuses(prev => ({ ...prev, [mode.type]: 'generating' }));
                            setInteractiveErrors(prev => { const n = { ...prev }; delete n[mode.type]; return n; });
                            try {
                              await api.post(`/teachers/classes/${classId}/assignments`, {
                                chapter_id: chapterId,
                                assignment_type: mode.type,
                                title: `${mode.label} - ${activeTopicTitle}`,
                                instructions: null,
                              });
                              setInteractiveStatuses(prev => ({ ...prev, [mode.type]: 'ready' }));
                            } catch (err: any) {
                              setInteractiveStatuses(prev => ({ ...prev, [mode.type]: 'failed' }));
                              setInteractiveErrors(prev => ({ ...prev, [mode.type]: err?.detail || err?.message || 'Failed to create assignment.' }));
                            }
                          }}
                          className={`w-full py-2.5 rounded-xl text-[11px] font-black uppercase tracking-wider flex items-center justify-center gap-2 transition-all ${
                            isGenerating
                              ? 'bg-amber-100 text-amber-700 cursor-not-allowed'
                              : isReady
                              ? 'bg-emerald-100 text-emerald-700 cursor-not-allowed'
                              : 'bg-[#1800ad] text-[#f6f4ee] hover:bg-[#1800ad]/90 cursor-pointer'
                          }`}
                        >
                          {isGenerating ? (
                            <><div className="w-3.5 h-3.5 border-2 border-t-amber-700 border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin" /> Generating...</>
                          ) : isReady ? (
                            <><Check size={12} className="stroke-[3]" /> Assigned ✓</>
                          ) : (
                            <><Zap size={12} /> Generate & Assign</>
                          )}
                        </button>
                        {errorMsg && <p className="text-[10px] font-bold text-rose-600">{errorMsg}</p>}
                      </div>
                    );
                  })}
                </div>
              </div>

            </div>
          )}
        </div>
      </main>

      {/* SUCCESS CELEBRATION ASSIGNMENT MODAL WITH CONFIG NOTES */}
      <AnimatePresence>
        {isSuccessModalOpen && (
          <div className="fixed inset-0 bg-[#1800ad]/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-[#f6f4ee] rounded-[32px] p-6 lg:p-8 max-w-lg w-full border-2 border-[#1800ad] text-[#1800ad] font-montserrat relative shadow-2xl"
            >
              
              {success ? (
                <>
                  <div className="w-14 h-14 rounded-full bg-emerald-500/10 text-emerald-600 flex items-center justify-center mx-auto mb-4 border-2 border-emerald-500/40 animate-pulse">
                    <CheckCircle2 size={32} className="stroke-[2.5]" />
                  </div>

                  <h3 className="text-xl font-black tracking-tight text-[#1800ad] text-center mb-1 leading-snug">
                    Material Assigned Successfully!
                  </h3>
                  
                  <p className="text-xs text-center text-[#1800ad]/75 font-semibold mb-6 uppercase tracking-wider">
                    Student group notified on dashboard
                  </p>

                  <div className="flex flex-col gap-2.5">
                    <button
                      onClick={() => {
                        setIsSuccessModalOpen(false);
                        navigate(`/teacher/chapter-setup/${classId}/${chapterId}`);
                      }}
                      className="w-full bg-[#1800ad] hover:bg-amber-300 hover:text-[#1800ad] text-[#f6f4ee] py-3.5 rounded-full text-xs font-extrabold uppercase tracking-widest active:scale-95 transition-all text-center font-montserrat shadow-md"
                    >
                      Return to Chapter Setup
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <h3 className="text-xl font-black tracking-tight text-[#1800ad] mb-2 leading-snug">
                    Assign to Class
                  </h3>
                  <p className="text-xs font-semibold opacity-75 mb-6">
                    Configure assignment details for your students.
                  </p>

                  <div className="bg-[#1800ad]/5 rounded-2xl p-4 flex flex-col gap-3.5 mb-6 border border-[#1800ad]/10">
                    <div className="flex items-center gap-2">
                      <Flame className="text-[#1800ad] stroke-[2.5] shrink-0" size={16} />
                      <div>
                        <span className="block text-[9px] font-black uppercase tracking-widest leading-none text-[#1800ad]/60">Assigned Resource</span>
                        <span className="block text-xs font-extrabold text-[#1800ad] mt-0.5">{assignedItemTitle}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 border-t border-[#1800ad]/10 pt-3">
                      <Calendar className="text-[#1800ad] stroke-[2.5] shrink-0" size={18} />
                      <div className="flex-1">
                        <span className="block text-[9px] font-black uppercase tracking-widest leading-none text-[#1800ad]/60 mb-1">Set Assessment Deadline</span>
                        <input
                          type="date"
                          value={assignmentDeadline}
                          onChange={(e) => setAssignmentDeadline(e.target.value)}
                          className="bg-[#f6f4ee] text-[#1800ad] border-2 border-[#1800ad]/25 hover:border-[#1800ad] focus:border-[#1800ad] px-3 py-1.5 text-xs font-bold rounded-lg focus:outline-none w-full font-montserrat"
                        />
                      </div>
                    </div>

                    <div className="border-t border-[#1800ad]/10 pt-3">
                      <span className="block text-[9px] font-black uppercase tracking-widest leading-none text-[#1800ad]/60 mb-1.5 flex items-center gap-1">
                        <FileText size={11} /> Teacher Instructions Notes
                      </span>
                      <textarea
                        rows={2.5}
                        value={assignmentNotes}
                        onChange={(e) => setAssignmentNotes(e.target.value)}
                        className="w-full bg-[#f6f4ee] text-[#1800ad] placeholder-[#1800ad]/40 border border-[#1800ad]/20 p-2.5 rounded-lg text-[11px] font-semibold focus:outline-none focus:border-[#1800ad] font-montserrat resize-none"
                      />
                    </div>
                  </div>

                  {assignError && (
                    <div className="mb-4 text-xs font-bold text-rose-600">
                      {assignError}
                    </div>
                  )}

                  <div className="flex gap-4">
                    <button
                      type="button"
                      disabled={publishing}
                      onClick={() => setIsSuccessModalOpen(false)}
                      className="flex-1 py-3.5 border-2 border-[#1800ad] rounded-full text-xs font-black uppercase tracking-wider text-center"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      disabled={publishing}
                      onClick={handlePublishAssignment}
                      className="flex-1 bg-[#1800ad] hover:bg-[#1800ad]/90 text-white rounded-full py-3.5 text-xs font-black uppercase tracking-widest text-center flex items-center justify-center gap-2"
                    >
                      {publishing ? (
                        <>
                          <div className="w-4 h-4 border-2 border-t-white border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin" />
                          <span>Publishing...</span>
                        </>
                      ) : (
                        <span>Publish</span>
                      )}
                    </button>
                  </div>
                </>
              )}

            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* ───────────────────────────────────────────────────────────────
           CONTENT LIBRARY MODAL
      ─────────────────────────────────────────────────────────────── */}
      <AnimatePresence>
        {showLibrary && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-[#1800ad]/50 z-[60] flex items-center justify-center p-4 animate-fadeIn"
            onClick={() => setShowLibrary(false)}
          >
            <motion.div
              initial={{ scale: 0.95, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 20 }}
              onClick={e => e.stopPropagation()}
              className="bg-[#f6f4ee] rounded-[32px] border-2 border-[#1800ad] w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden font-montserrat"
            >
              {/* Header */}
              <div className="flex items-start justify-between p-7 pb-4 border-b border-[#1800ad]/15 shrink-0">
                <div>
                  <div className="flex items-center gap-2.5 mb-1">
                    <div className="p-2 bg-[#1800ad] rounded-xl">
                      <Library size={16} className="text-[#f6f4ee]" />
                    </div>
                    <h2 className="text-2xl font-black text-[#1800ad] tracking-tight">Content Library</h2>
                    <span className="text-[10px] font-black uppercase tracking-widest px-2.5 py-1 bg-emerald-100 text-emerald-700 border border-emerald-200 rounded-full">
                      Free • No generation cost
                    </span>
                  </div>
                  <p className="text-xs font-semibold text-[#1800ad]/65 ml-11">
                    Pick a ready-made video for <span className="font-black text-[#1800ad]">{libraryTargetAsset?.title}</span> — same curriculum, zero wait time.
                  </p>
                </div>
                <button
                  onClick={() => setShowLibrary(false)}
                  className="p-2 border-2 border-[#1800ad]/20 rounded-full hover:bg-[#1800ad]/5 transition-colors shrink-0"
                >
                  <X size={16} className="text-[#1800ad]" />
                </button>
              </div>

              {/* Search bar */}
              <div className="px-7 py-4 shrink-0">
                <div className="relative">
                  <Search size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#1800ad]/50" />
                  <input
                    type="text"
                    placeholder="Search by topic, chapter, subject..."
                    value={librarySearch}
                    onChange={e => setLibrarySearch(e.target.value)}
                    className="w-full pl-11 pr-4 py-3 bg-white border-2 border-[#1800ad]/20 rounded-2xl text-sm font-semibold text-[#1800ad] placeholder:text-[#1800ad]/35 outline-none focus:border-[#1800ad]/50 transition-colors"
                  />
                </div>
              </div>

              {/* Items grid */}
              <div className="flex-1 overflow-y-auto px-7 pb-7">
                {libraryLoading ? (
                  <div className="flex flex-col items-center justify-center py-20 gap-4">
                    <div className="w-10 h-10 rounded-full border-4 border-t-[#1800ad] border-r-transparent border-b-transparent border-l-transparent animate-spin" />
                    <p className="text-xs font-black uppercase tracking-wider text-[#1800ad]/50">Loading library...</p>
                  </div>
                ) : (() => {
                  const needle = librarySearch.toLowerCase();
                  const filtered = libraryItems.filter(item => {
                    if (!needle) return true;
                    return `${item.title} ${item.chapter_title} ${item.subject} ${item.grade}`.toLowerCase().includes(needle);
                  });

                  if (filtered.length === 0) {
                    return (
                      <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
                        <Library size={40} className="text-[#1800ad]/20" />
                        <p className="text-sm font-black text-[#1800ad]/40">
                          {librarySearch ? 'No videos match your search.' : 'No ready videos in the library yet.'}
                        </p>
                        <p className="text-xs font-semibold text-[#1800ad]/30 max-w-xs">
                          Videos appear here once any teacher generates them for a matching curriculum topic.
                        </p>
                      </div>
                    );
                  }

                  return (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                      {filtered.map(item => {
                        const isAdopting = adopting === item.asset_id;
                        const isPreviewing = libraryPreview === item.asset_id;
                        return (
                          <motion.div
                            key={item.asset_id}
                            layout
                            className="bg-white border-2 border-[#1800ad]/10 rounded-[20px] overflow-hidden flex flex-col hover:border-[#1800ad]/40 hover:shadow-md transition-all"
                          >
                            {/* Video thumbnail / preview */}
                            <div
                              className="relative bg-[#1800ad]/5 h-36 flex items-center justify-center cursor-pointer group overflow-hidden"
                              onClick={() => setLibraryPreview(isPreviewing ? null : item.asset_id)}
                            >
                              {isPreviewing && item.external_url ? (
                                <video
                                  src={item.external_url}
                                  controls
                                  autoPlay
                                  className="w-full h-full object-cover"
                                />
                              ) : (
                                <>
                                  <div className="absolute inset-0 bg-gradient-to-br from-[#1800ad]/10 to-[#1800ad]/5" />
                                  <div className="relative z-10 flex flex-col items-center gap-2">
                                    <div className="w-12 h-12 rounded-full bg-[#1800ad] flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
                                      <Play size={18} className="text-[#f6f4ee] ml-1" />
                                    </div>
                                    <span className="text-[10px] font-black uppercase tracking-wider text-[#1800ad]/60">Click to preview</span>
                                  </div>
                                </>
                              )}
                            </div>

                            {/* Card body */}
                            <div className="p-4 flex flex-col gap-2 flex-1">
                              <div className="flex items-start justify-between gap-2">
                                <h4 className="text-sm font-black text-[#1800ad] leading-tight line-clamp-2">{item.title}</h4>
                              </div>

                              <div className="flex flex-wrap gap-1.5">
                                <span className="text-[10px] font-black px-2 py-0.5 bg-[#1800ad]/8 text-[#1800ad] rounded-full">
                                  Grade {item.grade}
                                </span>
                                <span className="text-[10px] font-black px-2 py-0.5 bg-[#1800ad]/8 text-[#1800ad] rounded-full">
                                  {item.subject}
                                </span>
                              </div>

                              <p className="text-[11px] font-semibold text-[#1800ad]/60 leading-snug">
                                Chapter: {item.chapter_title}
                              </p>

                              {item.last_generated_at && (
                                <p className="text-[10px] font-semibold text-[#1800ad]/40 flex items-center gap-1">
                                  <Clock size={10} />
                                  {new Date(item.last_generated_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                                </p>
                              )}

                              {/* Use This button */}
                              <button
                                id={`library-adopt-${item.asset_id}`}
                                onClick={() => handleAdoptFromLibrary(item.asset_id)}
                                disabled={isAdopting || !!adopting}
                                className="mt-auto w-full py-2.5 rounded-xl bg-[#1800ad] text-[#f6f4ee] text-[11px] font-black uppercase tracking-wider flex items-center justify-center gap-2 hover:bg-[#1800ad]/90 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                              >
                                {isAdopting ? (
                                  <>
                                    <div className="w-3.5 h-3.5 rounded-full border-2 border-t-white border-r-transparent border-b-transparent border-l-transparent animate-spin" />
                                    Applying...
                                  </>
                                ) : (
                                  <>
                                    <Zap size={12} /> Use This Video
                                  </>
                                )}
                              </button>
                            </div>
                          </motion.div>
                        );
                      })}
                    </div>
                  );
                })()}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
}
