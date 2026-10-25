import React from 'react';
import { MessageSquare, Search, MessageSquareText, LayoutDashboard, Home } from 'lucide-react';

interface Props {
  currentTab: 'home' | 'student' | 'admin' | 'all-feedback';
  setCurrentTab: (tab: 'home' | 'student' | 'admin' | 'all-feedback') => void;
}

export const Navbar: React.FC<Props> = ({ currentTab, setCurrentTab }) => {
  return (
    <header className="navbar">
      <div className="navbar-inner">
        <div className="nav-brand" onClick={() => setCurrentTab('home')}>
          <div className="brand-icon" title="StuFeed - Feedback Analysis & Discovery">
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <MessageSquare size={19} strokeWidth={2.4} />
              <Search
                size={11}
                strokeWidth={3}
                style={{
                  position: 'absolute',
                  bottom: -2,
                  right: -3,
                  backgroundColor: 'var(--primary-yellow)',
                  borderRadius: '50%',
                  padding: '1px',
                }}
              />
            </div>
          </div>
          <div className="brand-text">
            <h1>StuFeed</h1>
            <p>Student Feedback Intelligence Platform</p>
          </div>
        </div>

        <nav className="nav-links">
          <button
            className={`nav-btn ${currentTab === 'home' ? 'active' : ''}`}
            onClick={() => setCurrentTab('home')}
          >
            <Home size={16} />
            <span>Home</span>
          </button>

          <button
            className={`nav-btn ${currentTab === 'student' ? 'active' : ''}`}
            onClick={() => setCurrentTab('student')}
          >
            <MessageSquareText size={16} />
            <span>Student Feedback</span>
          </button>

          <button
            className={`nav-btn ${currentTab === 'admin' || currentTab === 'all-feedback' ? 'active' : ''}`}
            onClick={() => setCurrentTab('admin')}
          >
            <LayoutDashboard size={16} />
            <span>Admin Dashboard</span>
          </button>
        </nav>
      </div>
    </header>
  );
};
