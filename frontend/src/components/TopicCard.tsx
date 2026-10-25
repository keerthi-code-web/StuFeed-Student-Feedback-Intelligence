import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Quote, Sparkles, BookOpen, User, Building2 } from 'lucide-react';
import { TopicCluster } from '../types';
import { SentimentBadge } from './SentimentBadge';

interface Props {
  topic: TopicCluster;
}

export const TopicCard: React.FC<Props> = ({ topic }) => {
  const [expanded, setExpanded] = useState(false);

  const total = topic.comment_count;
  const posPct = total > 0 ? (topic.sentiment_distribution.positive / total) * 100 : 0;
  const negPct = total > 0 ? (topic.sentiment_distribution.negative / total) * 100 : 0;
  const neuPct = total > 0 ? (topic.sentiment_distribution.neutral / total) * 100 : 0;

  return (
    <div className="topic-item-card">
      <div className="topic-header">
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.35rem', flexWrap: 'wrap' }}>
            <Sparkles size={16} color="#D97706" />
            <h4 className="topic-title">{topic.topic_label}</h4>
            <span className="topic-count-pill">{total} {total === 1 ? 'comment' : 'comments'}</span>
          </div>
          
          <div className="tags-row">
            {topic.top_keywords && topic.top_keywords.map((kw, i) => (
              <span key={i} className="tag-pill accent">#{kw}</span>
            ))}
          </div>
        </div>

        {/* Sentiment Mini Bar */}
        <div style={{ minWidth: '180px', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
            <span>Pos: {topic.sentiment_distribution.positive}</span>
            <span>Neu: {topic.sentiment_distribution.neutral}</span>
            <span>Neg: {topic.sentiment_distribution.negative}</span>
          </div>
          <div style={{ height: '8px', display: 'flex', borderRadius: '4px', overflow: 'hidden', background: '#E4E4E7' }}>
            <div style={{ width: `${posPct}%`, background: '#16A34A' }} title={`Positive: ${topic.sentiment_distribution.positive}`} />
            <div style={{ width: `${neuPct}%`, background: '#6B7280' }} title={`Neutral: ${topic.sentiment_distribution.neutral}`} />
            <div style={{ width: `${negPct}%`, background: '#DC2626' }} title={`Negative: ${topic.sentiment_distribution.negative}`} />
          </div>
        </div>
      </div>

      {/* Representative Feedback Quote */}
      {topic.representative_comments && topic.representative_comments.length > 0 && (
        <div className="rep-comment-box">
          <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'flex-start' }}>
            <Quote size={14} style={{ flexShrink: 0, marginTop: '2px', color: '#64748B' }} />
            <div>
              <span style={{ fontWeight: 600, fontSize: '0.78rem', color: '#475569', display: 'block', marginBottom: '2px' }}>
                Representative Student Comment:
              </span>
              "{topic.representative_comments[0]}"
            </div>
          </div>
        </div>
      )}

      {/* Department, Subject & Instructor Context */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.5rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
          {topic.departments && topic.departments.map((dept, i) => (
            <span key={i} className="tag-pill accent" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontWeight: 600 }}>
              <Building2 size={12} /> {dept}
            </span>
          ))}
          {topic.subjects && topic.subjects.filter(s => s && s.trim()).map((sub, i) => (
            <span key={i} className="tag-pill" style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
              <BookOpen size={11} /> {sub}
            </span>
          ))}
          {topic.instructors && topic.instructors.filter(inst => inst && inst.trim()).map((inst, i) => (
            <span key={i} className="tag-pill" style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
              <User size={11} /> {inst}
            </span>
          ))}
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          style={{
            fontSize: '0.82rem',
            color: 'var(--primary-yellow-dark)',
            fontWeight: 600,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.25rem',
            padding: '0.25rem 0.6rem',
            borderRadius: '4px',
            background: 'var(--bg-yellow-light)',
          }}
        >
          {expanded ? (
            <>Hide Evidence ({topic.supporting_comments.length}) <ChevronUp size={14} /></>
          ) : (
            <>View Evidence ({topic.supporting_comments.length}) <ChevronDown size={14} /></>
          )}
        </button>
      </div>

      {/* Expanded Supporting Comments List */}
      {expanded && (
        <div style={{ marginTop: '1rem', borderTop: '1px solid var(--border-light)', paddingTop: '0.75rem' }}>
          <p style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
            Supporting Feedback Evidence ({topic.supporting_comments.length} comments in this semantic cluster):
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {topic.supporting_comments.map((sc) => (
              <div
                key={sc.id}
                style={{
                  background: '#FDFDFD',
                  border: '1px solid #E2E8F0',
                  borderRadius: '6px',
                  padding: '0.65rem 0.85rem',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  gap: '0.75rem',
                }}
              >
                <div style={{ flex: 1 }}>
                  <p style={{ fontSize: '0.88rem', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                    "{sc.feedback_text}"
                  </p>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    <strong>{sc.department_name}</strong>
                    {sc.subject_name && ` • ${sc.subject_name}`}
                    {sc.instructor_name && ` • ${sc.instructor_name}`}
                    {` • Rating: ${sc.rating}/5`}
                  </span>
                </div>
                <SentimentBadge
                  sentiment={sc.sentiment_label}
                  detail={sc.sentiment_detail}
                  confidence={sc.sentiment_confidence}
                  isMixed={sc.is_mixed}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
