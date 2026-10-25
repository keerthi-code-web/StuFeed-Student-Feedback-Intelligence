import React, { useState, useEffect } from 'react';
import { ArrowLeft, Inbox, Star } from 'lucide-react';
import { FeedbackSubmission } from '../types';
import { SentimentBadge } from '../components/SentimentBadge';

interface Props {
  onBackToDashboard: () => void;
}

export const AllFeedbackPage: React.FC<Props> = ({ onBackToDashboard }) => {
  const [feedbackList, setFeedbackList] = useState<FeedbackSubmission[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetch('/api/feedback?limit=500')
      .then((res) => res.json())
      .then((data: FeedbackSubmission[]) => setFeedbackList(data))
      .catch((err) => console.error('Failed to load all feedback:', err))
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.75rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <button
            className="btn-secondary"
            onClick={onBackToDashboard}
            style={{ marginBottom: '0.75rem', padding: '0.45rem 0.85rem', fontSize: '0.85rem' }}
          >
            <ArrowLeft size={15} />
            <span>Back to Dashboard</span>
          </button>
          <h2 style={{ fontSize: '1.75rem', fontWeight: 700 }}>All Feedback Received</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem' }}>
            Complete historical record of submitted course and institutional evaluations with NLP classifications.
          </p>
        </div>

        <span style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-muted)' }}>
          Total Submissions: {feedbackList.length}
        </span>
      </div>

      {feedbackList.length === 0 && !isLoading ? (
        <div className="empty-state">
          <div className="empty-icon">
            <Inbox size={48} />
          </div>
          <h3>No Feedback Submissions Recorded</h3>
          <p>
            No student feedback records exist in the database. As students submit course or institutional evaluations, they will appear here.
          </p>
        </div>
      ) : (
        <div className="table-container">
          <table className="styled-table">
            <thead>
              <tr>
                <th>Department</th>
                <th>Subject</th>
                <th>Instructor</th>
                <th>Rating</th>
                <th>NLP Sentiment</th>
                <th>Confidence</th>
                <th>Original Written Feedback</th>
                <th>Submission Time</th>
              </tr>
            </thead>
            <tbody>
              {feedbackList.map((item) => (
                <tr key={item.id}>
                  <td style={{ fontWeight: 600, minWidth: '160px' }}>
                    <span className="tag-pill accent" style={{ fontWeight: 600 }}>
                      {item.department_name}
                    </span>
                  </td>
                  <td style={{ minWidth: '150px' }}>
                    {item.is_other || !item.subject_name ? (
                      <span style={{ color: 'var(--text-muted)' }}>—</span>
                    ) : (
                      item.subject_name
                    )}
                  </td>
                  <td style={{ minWidth: '140px' }}>
                    {item.is_other || !item.instructor_name ? (
                      <span style={{ color: 'var(--text-muted)' }}>—</span>
                    ) : (
                      item.instructor_name
                    )}
                  </td>
                  <td>
                    <span style={{ fontWeight: 700, color: '#B45309', display: 'inline-flex', alignItems: 'center', gap: '2px' }}>
                      ★ {item.rating}
                    </span>
                  </td>
                  <td style={{ minWidth: '120px' }}>
                    <SentimentBadge
                      sentiment={item.sentiment_label}
                      detail={item.sentiment_detail}
                      confidence={item.sentiment_confidence}
                      isMixed={item.is_mixed}
                      showConfidence={false}
                    />
                  </td>
                  <td style={{ minWidth: '80px', fontWeight: 600, fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                    {Math.round(item.sentiment_confidence * 100)}%
                  </td>
                  <td style={{ minWidth: '280px', color: 'var(--text-primary)' }}>
                    "{item.feedback_text}"
                  </td>
                  <td style={{ whiteSpace: 'nowrap', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    {new Date(item.created_at).toLocaleDateString()} {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
