import React, { useState } from 'react';
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
  const navigate = useNavigate();

  return (
    <div className="flex h-screen bg-[#f6f4ee] font-montserrat">
      {/* Sidebar Navigation */}
      <nav className="w-16 md:w-64 bg-[#1800ad] text-white flex flex-col transition-all duration-300">
        <div className="h-16 flex items-center justify-center md:justify-start md:px-6 font-extrabold text-xl tracking-tight border-b border-white/10 shrink-0">
          <span className="md:hidden">M</span>
          <span className="hidden md:inline">Mootion</span>
        </div>
        <div className="flex-1 py-6 flex flex-col gap-2 px-3">
          <NavItem icon={<LayoutDashboard size={20} />} label="Dashboard" onClick={() => navigate('/teacher/dashboard')} />
          <NavItem icon={<BarChart2 size={20} />} label="Analytics" active onClick={() => navigate('/teacher/analytics')} />
          <NavItem icon={<BookOpen size={20} />} label="Curriculum" onClick={() => navigate('/teacher/dashboard')} />
          <NavItem icon={<MessageSquare size={20} />} label="Doubt Board" onClick={() => navigate('/teacher/doubts')} />
        </div>
        <div className="p-4 border-t border-white/10 flex flex-col items-center">
          <div onClick={() => setIsLogoutModalOpen(true)} className="shrink-0 cursor-pointer flex items-center justify-center w-12 h-12 rounded-full bg-[#f6f4ee]">
            <span className="text-[#1800ad] font-extrabold text-xl">
              T
            </span>
          </div>
          <span className="hidden md:block mt-2 text-sm font-semibold opacity-80">Log Out</span>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-y-auto">
        {/* Top Header */}
        <header className="h-24 px-8 flex items-end pb-4 border-b border-[#1800ad]/10 shrink-0">
          <div>
            <h1 className="text-3xl font-black text-[#1800ad]">Analytics</h1>
            <p className="text-[#1800ad]/60 font-semibold mt-1">Classroom Insights & Progress</p>
          </div>
        </header>

        {/* Empty State Body */}
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center max-w-2xl mx-auto">
          <div className="w-32 h-32 bg-white rounded-full flex items-center justify-center shadow-lg mb-8">
            <Users size={64} className="text-[#1800ad]/30" />
          </div>
          <h2 className="text-3xl font-black text-[#1800ad] mb-4">You don't have any classes set up yet</h2>
          <p className="text-[#1800ad]/70 text-lg font-semibold mb-8">
            Create your first class to invite students and start tracking their conceptual understanding, misconceptions, and learning progress.
          </p>
          <button 
            onClick={() => navigate('/teacher/dashboard')}
            className="px-8 py-4 bg-[#1800ad] text-white font-extrabold rounded-full hover:scale-105 transition-all shadow-lg"
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
