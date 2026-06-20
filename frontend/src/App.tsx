import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { LandingPage } from './pages/LandingPage';
import { OnboardingPage } from './pages/OnboardingPage';
import { StudentLoginPage } from './pages/StudentLoginPage';
import { StudentSignupPage } from './pages/StudentSignupPage';
import { StudentHomePage } from './pages/StudentHomePage';
import { StudentTasksPage } from './pages/StudentTasksPage';
import { StudentTaskActivityPage } from './pages/StudentTaskActivityPage';
import { StudentExplorePage } from './pages/StudentExplorePage';
import { StudentPlaygroundPage } from './pages/StudentPlaygroundPage';
import { StudentAnalytics } from './pages/StudentAnalytics';


// Teacher Imports
import { TeacherLoginPage } from './pages/TeacherLoginPage';
import { TeacherOnboardingPage } from './pages/TeacherOnboardingPage';
import { TeacherDashboardPage } from './pages/TeacherDashboardPage';
import { TeacherClassViewPage } from './pages/TeacherClassViewPage';
import { TeacherChapterSetupPage } from './pages/TeacherChapterSetupPage';
import { TeacherBroadcastPage } from './pages/TeacherBroadcastPage';
import { TeacherAnalyticsPage } from './pages/TeacherAnalyticsPage';
import { TeacherAnalytics } from './pages/TeacherAnalytics';
import { TeacherDoubtsPage } from './pages/TeacherDoubtsPage';
import { TeacherTopicSetupPage } from './pages/TeacherTopicSetupPage';

// Route Guards
import { ProtectedRoute, LoginRoute } from './components/ProtectedRoute';

// NotFound Page
import { NotFoundPage } from './app/not-found';

// Gesture Navigation
import { GestureNavigation } from './components/GestureNavigation';

export default function App() {
  return (
    <BrowserRouter>
      <GestureNavigation />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/login" element={<LoginRoute><StudentLoginPage /></LoginRoute>} />
        <Route path="/login/student" element={<LoginRoute><StudentLoginPage /></LoginRoute>} />
        <Route path="/signup/student" element={<StudentSignupPage />} />
        
        {/* Protected Student Routes */}
        <Route path="/student/home" element={<ProtectedRoute allowedRole="student"><StudentHomePage /></ProtectedRoute>} />
        <Route path="/student/tasks" element={<ProtectedRoute allowedRole="student"><StudentTasksPage /></ProtectedRoute>} />
        <Route path="/student/task/:taskId" element={<ProtectedRoute allowedRole="student"><StudentTaskActivityPage /></ProtectedRoute>} />
        <Route path="/student/explore" element={<ProtectedRoute allowedRole="student"><StudentExplorePage /></ProtectedRoute>} />
        <Route path="/student/explore/:subjectCode/:chapterId" element={<ProtectedRoute allowedRole="student"><StudentExplorePage /></ProtectedRoute>} />
        <Route path="/student/playground" element={<ProtectedRoute allowedRole="student"><StudentPlaygroundPage /></ProtectedRoute>} />
        <Route path="/student/analytics" element={<ProtectedRoute allowedRole="student"><StudentAnalytics /></ProtectedRoute>} />

        {/* Protected Teacher Routes */}
        <Route path="/teacher/login" element={<LoginRoute><TeacherLoginPage /></LoginRoute>} />
        <Route path="/teacher/onboarding" element={<TeacherOnboardingPage />} />
        <Route path="/teacher/home" element={<ProtectedRoute allowedRole="teacher"><TeacherDashboardPage /></ProtectedRoute>} />
        <Route path="/teacher/class/:id" element={<ProtectedRoute allowedRole="teacher"><TeacherClassViewPage /></ProtectedRoute>} />
        <Route path="/teacher/chapter-setup/:classId/:chapterId" element={<ProtectedRoute allowedRole="teacher"><TeacherChapterSetupPage /></ProtectedRoute>} />
        <Route path="/teacher/topic-setup/:classId/:chapterId/:topicId" element={<ProtectedRoute allowedRole="teacher"><TeacherTopicSetupPage /></ProtectedRoute>} />
        <Route path="/teacher/broadcast" element={<ProtectedRoute allowedRole="teacher"><TeacherBroadcastPage /></ProtectedRoute>} />
        <Route path="/teacher/analytics" element={<ProtectedRoute allowedRole="teacher"><TeacherAnalyticsPage /></ProtectedRoute>} />
        <Route path="/teacher/analytics/:classId" element={<ProtectedRoute allowedRole="teacher"><TeacherAnalytics /></ProtectedRoute>} />
        <Route path="/teacher/student/:studentId/scores" element={<ProtectedRoute allowedRole="teacher"><StudentAnalytics /></ProtectedRoute>} />
        <Route path="/teacher/doubts" element={<ProtectedRoute allowedRole="teacher"><TeacherDoubtsPage /></ProtectedRoute>} />

        {/* Student login route */}
        <Route path="/student/login" element={<LoginRoute><StudentLoginPage /></LoginRoute>} />

        {/* Catch-all unmatched routes */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}
