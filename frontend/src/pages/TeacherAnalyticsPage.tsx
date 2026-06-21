import React, { useState, useEffect } from 'react';
import { LogoutModal } from '../components/LogoutModal';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { 
  BarChart2, 
  LayoutDashboard, 
  BookOpen, 
  MessageSquare,
  Users
} from 'lucide-react';
import { NavItem } from '../components/NavItem';

export function TeacherAnalyticsPage() {
  const [isLogoutModalOpen, setIsLogoutModalOpen] = useState(false);
  const [teacherName, setTeacherName] = useState<string>('Teacher');
  const navigate = useNavigate();

  useEffect(() => {
    const fetchTeacherProfile = async () => {
      try {
        const user = await api.get('/teachers/me');
        if (user && user.full_name) {
          setTeacherName(user.full_name);
        }
      } catch (err) {
        console.error('Failed to fetch teacher profile:', err);
      }
    };
    fetchTeacherProfile();
  }, []);

  return (
    <div className="flex flex-1 w-full h-[100dvh] bg-[#1800ad] font-montserrat text-[#1800ad] overflow-hidden relative">

      {/* Mobile Bottom Navigation Bar */}
      <nav className="md:hidden fixed bottom-4 left-4 right-4 bg-[#1800ad] px-6 py-2.5 flex justify-between items-center z-40 rounded-full border-[2px] border-[#f6f4ee] shadow-xl font-montserrat">
        <NavItem icon={<LayoutDashboard size={24} />} onClick={() => navigate('/teacher/home')} />
        <NavItem icon={<BookOpen size={24} />} onClick={() => navigate('/teacher/home')} />
        <NavItem icon={<BarChart2 size={24} />} active onClick={() => navigate('/teacher/analytics')} />
        <NavItem icon={<MessageSquare size={24} />} onClick={() => navigate('/teacher/doubts')} />
        <div
          onClick={() => setIsLogoutModalOpen(true)}
          className="shrink-0 cursor-pointer flex items-center justify-center w-8 h-8 rounded-full border border-[#f6f4ee] bg-[#f6f4ee] hover:opacity-90 transition-opacity"
        >
          <span className="text-[#1800ad] font-bold text-xs">
            {teacherName ? teacherName[0].toUpperCase() : 'T'}
          </span>
        </div>
      </nav>

      {/* Teacher Sidebar — Desktop Only */}
      <aside className="hidden md:flex w-[80px] lg:w-[100px] flex-col items-center justify-between py-8 fixed top-0 bottom-0 left-0 h-full shrink-0 bg-[#1800ad] text-[#f6f4ee] z-30">
        <div className="flex items-center justify-center mt-4 cursor-pointer" onClick={() => navigate('/')}>
          <span className="text-[#f6f4ee] font-val text-[42px] leading-none tracking-widest mt-1 mr-1">M</span>
        </div>
        <nav className="flex flex-col gap-6 w-full items-center my-auto">
          <NavItem icon={<LayoutDashboard size={24} />} onClick={() => navigate('/teacher/home')} />
          <NavItem icon={<BookOpen size={24} />} onClick={() => navigate('/teacher/home')} />
          <NavItem icon={<BarChart2 size={24} />} active onClick={() => navigate('/teacher/analytics')} />
          <NavItem icon={<MessageSquare size={24} />} onClick={() => navigate('/teacher/doubts')} />
        </nav>
        <div onClick={() => setIsLogoutModalOpen(true)} className="shrink-0 cursor-pointer flex items-center justify-center group w-12 h-12 rounded-full border-2 border-[#1800ad] bg-[#f6f4ee] relative">
          <span className="text-[#1800ad] font-bold text-lg">
            {teacherName ? teacherName[0].toUpperCase() : 'T'}
          </span>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 md:ml-[80px] lg:ml-[100px] bg-[#f6f4ee] md:rounded-l-[40px] p-5 md:p-8 flex flex-col overflow-y-auto h-[100dvh]">

        <header className="shrink-0 mb-8 lg:mb-10 flex flex-col gap-2">
          <h1 className="text-3xl md:text-3xl lg:text-4xl font-bold tracking-tight text-[#1800ad]">Analytics</h1>
          <p className="text-[#1800ad]/70 font-medium">Classroom Insights &amp; Progress</p>
        </header>

        {/* Empty State Body */}
        <div className="flex-1 flex flex-col items-center justify-center pb-24 md:pb-8 text-center max-w-2xl mx-auto w-full">
          <div className="w-28 h-28 bg-white rounded-full flex items-center justify-center shadow-lg mb-8 border-2 border-[#1800ad]/10">
            <Users size={56} className="text-[#1800ad]/30" />
          </div>
          <h2 className="text-2xl md:text-3xl font-black text-[#1800ad] mb-4">You don't have any classes set up yet</h2>
          <p className="text-[#1800ad]/70 text-base font-semibold mb-8 leading-relaxed">
            Create your first class to invite students and start tracking their conceptual understanding, misconceptions, and learning progress.
          </p>
          <button 
            onClick={() => navigate('/teacher/home')}
            className="px-8 py-4 bg-[#1800ad] text-white font-extrabold rounded-full hover:scale-105 transition-all shadow-lg text-sm"
          >
            Go to Dashboard to Setup
          </button>
        </div>
      </main>

      {/* MODAL: Logout Confirmation */}
      <LogoutModal isOpen={isLogoutModalOpen} onClose={() => setIsLogoutModalOpen(false)} />
    </div>
  );
}
