import React from 'react';
import { MessageSquareText, LayoutDashboard } from 'lucide-react';

interface Props {
  onNavigate: (tab: 'student' | 'admin') => void;
}

export const HomePage: React.FC<Props> = ({ onNavigate }) => {
  return (
    <div style={{ padding: '2rem 0' }}>
      {/* Retained Hero Container */}
      <section className="hero-section" style={{ maxWidth: '850px', margin: '0 auto', padding: '3.5rem 2rem' }}>
        <div className="hero-pill">
          Student Feedback Intelligence Platform
        </div>
        <h1 className="hero-title" style={{ marginBottom: '1.25rem' }}>
          Academic Feedback Intelligence
        </h1>
        <p className="hero-subtitle" style={{ marginBottom: '2.5rem' }}>
          Turn student feedback into clear sentiment insights and recurring topics.
        </p>

        <div className="hero-actions">
          <button className="btn-primary" onClick={() => onNavigate('student')}>
            <MessageSquareText size={18} />
            <span>Submit Student Feedback</span>
          </button>
          <button className="btn-secondary" onClick={() => onNavigate('admin')}>
            <LayoutDashboard size={18} />
            <span>Enter Admin Dashboard</span>
          </button>
        </div>
      </section>
    </div>
  );
};
