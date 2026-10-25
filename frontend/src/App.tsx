import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { HomePage } from './pages/HomePage';
import { StudentFeedbackPage } from './pages/StudentFeedbackPage';
import { AdminDashboardPage } from './pages/AdminDashboardPage';
import { AllFeedbackPage } from './pages/AllFeedbackPage';

export function App() {
  const [currentTab, setCurrentTab] = useState<'home' | 'student' | 'admin' | 'all-feedback'>('home');

  useEffect(() => {
    const handleLocation = () => {
      const path = window.location.pathname;
      if (path === '/student') {
        setCurrentTab('student');
      } else if (path === '/admin') {
        setCurrentTab('admin');
      } else if (path === '/all-feedback') {
        setCurrentTab('all-feedback');
      } else {
        setCurrentTab('home');
      }
    };

    handleLocation();
    window.addEventListener('popstate', handleLocation);
    return () => window.removeEventListener('popstate', handleLocation);
  }, []);

  const navigateTo = (tab: 'home' | 'student' | 'admin' | 'all-feedback') => {
    setCurrentTab(tab);
    const targetPath = tab === 'home' ? '/' : `/${tab}`;
    window.history.pushState({}, '', targetPath);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="app-container">
      <Navbar currentTab={currentTab} setCurrentTab={navigateTo} />

      <main className="main-content">
        {currentTab === 'home' && <HomePage onNavigate={navigateTo} />}
        {currentTab === 'student' && <StudentFeedbackPage />}
        {currentTab === 'admin' && (
          <AdminDashboardPage onNavigateToAllFeedback={() => navigateTo('all-feedback')} />
        )}
        {currentTab === 'all-feedback' && (
          <AllFeedbackPage onBackToDashboard={() => navigateTo('admin')} />
        )}
      </main>

      <footer className="footer" style={{ padding: '1.5rem', textAlign: 'center', borderTop: '1px solid var(--border-light)', backgroundColor: '#FFFFFF' }}>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', fontWeight: 500 }}>
          “Every voice matters. Every insight creates an opportunity to improve.”
        </p>
      </footer>
    </div>
  );
}

export default App;
