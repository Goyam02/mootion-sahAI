import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { User, Language } from './types';
import { api } from './api';
import { LanguageToggle } from './components/LanguageToggle';

// Page Imports
import { Login } from './pages/auth/Login';
import { OAuthCallback } from './pages/auth/OAuthCallback';
import { TeacherOnboarding } from './pages/teacher/TeacherOnboarding';
import { TeacherHome } from './pages/teacher/TeacherHome';
import { ClassView } from './pages/teacher/ClassView';
import { ChapterSetup } from './pages/teacher/ChapterSetup';
import { BroadcastMode } from './pages/teacher/BroadcastMode';
import { TeacherAnalytics } from './pages/teacher/TeacherAnalytics';
import { DoubtDashboard } from './pages/teacher/DoubtDashboard';

import { StudentOnboarding } from './pages/student/StudentOnboarding';
import { StudentHome } from './pages/student/StudentHome';
import { MyTasks } from './pages/student/MyTasks';
import { ActivitySession } from './pages/student/ActivitySession';
import { DoubtFlow } from './pages/student/DoubtFlow';
import { StudentExplore } from './pages/student/StudentExplore';
import { PlaygroundMode } from './pages/student/PlaygroundMode';
import { SimulationGenerator } from './pages/student/SimulationGenerator';
import { StudentProfile } from './pages/student/StudentProfile';

const App: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentLanguage, setCurrentLanguage] = useState<Language>('english');

  // Check auth status on load
  useEffect(() => {
    async function checkAuth() {
      const token = localStorage.getItem('mootion_token');
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const u = await api.getCurrentUser();
        setUser(u);
        setCurrentLanguage(u.preferred_language);
      } catch (e) {
        console.error('Session expired', e);
        localStorage.removeItem('mootion_token');
        localStorage.removeItem('mootion_role');
      } finally {
        setLoading(false);
      }
    }
    checkAuth();
  }, []);

  const handleLoginSuccess = (loggedInUser: User) => {
    setUser(loggedInUser);
    setCurrentLanguage(loggedInUser.preferred_language);
  };

  const handleLogout = async () => {
    await api.logout();
    setUser(null);
    navigate('/');
  };

  const handleLanguageChange = (lang: Language) => {
    setCurrentLanguage(lang);
    if (user) {
      setUser(prev => prev ? { ...prev, preferred_language: lang } : null);
    }
  };

  // Hide the global language toggle when in Broadcast Mode
  const isBroadcast = location.pathname.includes('/broadcast');

  if (loading) {
    return (
      <div className="min-h-screen bg-[#07070c] flex flex-col items-center justify-center text-slate-100 relative">
        <span className="w-10 h-10 border-4 border-violet-500/20 border-t-violet-500 rounded-full animate-spin" />
        <span className="text-xs text-slate-500 mt-3 font-bold uppercase tracking-wider animate-pulse">
          Booting Mootion Core...
        </span>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Global Background light shapes and grids */}
      <div className="fixed inset-0 bg-[#07070c] z-0" />
      <div className="grid-overlay" />
      <div className="ambient-light" />
      
      {/* Global Floating Language Selection Toggle */}
      {!isBroadcast && (
        <div className="fixed top-6 right-6 z-50 animate-fade-in">
          <LanguageToggle 
            currentLanguage={currentLanguage} 
            onLanguageChange={handleLanguageChange} 
          />
        </div>
      )}

      {/* Primary Routes */}
      <Routes>
        <Route 
          path="/" 
          element={
            user ? (
              user.onboarding_completed ? (
                <Navigate to={user.role === 'teacher' ? '/teacher/home' : '/student/home'} replace />
              ) : (
                <Navigate to={user.role === 'teacher' ? '/teacher/onboarding' : '/student/onboarding'} replace />
              )
            ) : (
              <Login onLoginSuccess={handleLoginSuccess} />
            )
          } 
        />
        <Route 
          path="/auth/google/callback" 
          element={<OAuthCallback onLoginSuccess={handleLoginSuccess} />} 
        />

        {/* TEACHER FLOW */}
        <Route 
          path="/teacher/onboarding" 
          element={
            user?.role === 'teacher' 
              ? <TeacherOnboarding onOnboardingComplete={handleLoginSuccess} /> 
              : <Navigate to="/" replace />
          } 
        />
        <Route 
          path="/teacher/home" 
          element={
            user?.role === 'teacher' 
              ? <TeacherHome user={user} onLogout={handleLogout} onLanguageChange={handleLanguageChange} /> 
              : <Navigate to="/" replace />
          } 
        />
        <Route 
          path="/teacher/class/:classId" 
          element={user?.role === 'teacher' ? <ClassView /> : <Navigate to="/" replace />} 
        />
        <Route 
          path="/teacher/class/:classId/chapter/:chapterId/setup" 
          element={user?.role === 'teacher' ? <ChapterSetup /> : <Navigate to="/" replace />} 
        />
        <Route 
          path="/teacher/class/:classId/broadcast" 
          element={user?.role === 'teacher' ? <BroadcastMode /> : <Navigate to="/" replace />} 
        />
        <Route 
          path="/teacher/analytics" 
          element={user?.role === 'teacher' ? <TeacherAnalytics /> : <Navigate to="/" replace />} 
        />
        <Route 
          path="/teacher/doubts" 
          element={user?.role === 'teacher' ? <DoubtDashboard /> : <Navigate to="/" replace />} 
        />

        {/* STUDENT FLOW */}
        <Route 
          path="/student/onboarding" 
          element={
            user?.role === 'student' 
              ? <StudentOnboarding onOnboardingComplete={handleLoginSuccess} /> 
              : <Navigate to="/" replace />
          } 
        />
        <Route 
          path="/student/home" 
          element={
            user?.role === 'student' 
              ? <StudentHome user={user} onLogout={handleLogout} /> 
              : <Navigate to="/" replace />
          } 
        />
        <Route 
          path="/student/tasks" 
          element={user?.role === 'student' ? <MyTasks /> : <Navigate to="/" replace />} 
        />
        <Route 
          path="/student/class/:classId/task/:taskId" 
          element={user?.role === 'student' ? <ActivitySession /> : <Navigate to="/" replace />} 
        />
        <Route 
          path="/student/doubt" 
          element={user?.role === 'student' ? <DoubtFlow /> : <Navigate to="/" replace />} 
        />
        <Route 
          path="/student/explore" 
          element={user?.role === 'student' ? <StudentExplore /> : <Navigate to="/" replace />} 
        />
        <Route 
          path="/student/playground" 
          element={user?.role === 'student' ? <PlaygroundMode /> : <Navigate to="/" replace />} 
        />
        <Route 
          path="/student/simulate" 
          element={user?.role === 'student' ? <SimulationGenerator /> : <Navigate to="/" replace />} 
        />
        <Route 
          path="/student/profile" 
          element={
            user?.role === 'student' 
              ? <StudentProfile user={user} onLogout={handleLogout} onLanguageChange={handleLanguageChange} /> 
              : <Navigate to="/" replace />
          } 
        />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
};

export default App;
