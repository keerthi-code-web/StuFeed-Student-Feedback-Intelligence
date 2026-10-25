import React, { useState, useEffect, useCallback } from 'react';
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend
} from 'recharts';
import {
  Filter, Settings, Building2, BookOpen, User, Sparkles, ArrowRight, Layers
} from 'lucide-react';
import {
  OverviewMetrics, TopicCluster, Subject, Instructor, DepartmentsOverviewResponse
} from '../types';
import { TopicCard } from '../components/TopicCard';
import { AcademicManagementModal } from '../components/AcademicManagementModal';

interface Props {
  onNavigateToAllFeedback: () => void;
}

export const AdminDashboardPage: React.FC<Props> = ({ onNavigateToAllFeedback }) => {
  // Data state
  const [deptOverview, setDeptOverview] = useState<DepartmentsOverviewResponse | null>(null);
  const [metrics, setMetrics] = useState<OverviewMetrics | null>(null);
  const [topics, setTopics] = useState<TopicCluster[]>([]);
  const [instructorBreakdown, setInstructorBreakdown] = useState<any[]>([]);

  // Filter options state
  const [filterDepartment, setFilterDepartment] = useState<string>('');
  const [filterSubject, setFilterSubject] = useState<string>('');
  const [filterInstructor, setFilterInstructor] = useState<string>('');
  const [filterSentiment, setFilterSentiment] = useState<string>('');

  const [availableSubjects, setAvailableSubjects] = useState<Subject[]>([]);
  const [availableInstructors, setAvailableInstructors] = useState<Instructor[]>([]);

  // Academic Management Modal state
  const [isManagementOpen, setIsManagementOpen] = useState(false);
  const [managementTab, setManagementTab] = useState<'departments' | 'subjects' | 'instructors'>('departments');

  const [isLoading, setIsLoading] = useState(true);

  // 1. Fetch Department Overview
  const fetchDeptOverview = useCallback(async () => {
    try {
      const res = await fetch('/api/departments/overview');
      const data = await res.json();
      setDeptOverview(data);
    } catch (err) {
      console.error('Failed to load departments overview:', err);
    }
  }, []);

  // 2. Load subjects when filterDepartment changes
  useEffect(() => {
    if (!filterDepartment || filterDepartment === 'Other') {
      setAvailableSubjects([]);
      setFilterSubject('');
      setAvailableInstructors([]);
      setFilterInstructor('');
      return;
    }

    fetch(`/api/subjects?department_name=${encodeURIComponent(filterDepartment)}`)
      .then((res) => res.json())
      .then((data: Subject[]) => {
        setAvailableSubjects(data);
        // Clear filterSubject if no longer in the list
        if (filterSubject && !data.some((s) => s.name === filterSubject)) {
          setFilterSubject('');
        }
      })
      .catch((err) => console.error('Failed to load filtered subjects:', err));
  }, [filterDepartment]);

  // 3. Load instructors when filterSubject changes
  useEffect(() => {
    if (!filterDepartment || filterDepartment === 'Other') {
      setAvailableInstructors([]);
      setFilterInstructor('');
      return;
    }

    let url = `/api/instructors?department_name=${encodeURIComponent(filterDepartment)}`;
    if (filterSubject) {
      const subObj = availableSubjects.find((s) => s.name === filterSubject);
      if (subObj) {
        url += `&subject_id=${subObj.id}`;
      } else {
        url += `&subject_name=${encodeURIComponent(filterSubject)}`;
      }
    }

    fetch(url)
      .then((res) => res.json())
      .then((data: Instructor[]) => {
        setAvailableInstructors(data);
        if (filterInstructor && !data.some((i) => i.name === filterInstructor)) {
          setFilterInstructor('');
        }
      })
      .catch((err) => console.error('Failed to load filtered instructors:', err));
  }, [filterDepartment, filterSubject, availableSubjects]);

  // 4. Fetch filtered metrics, topics, and instructor breakdown
  const fetchFilteredData = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterDepartment) params.append('department_name', filterDepartment);
      if (filterSubject) params.append('subject_name', filterSubject);
      if (filterInstructor) params.append('instructor_name', filterInstructor);
      if (filterSentiment) params.append('sentiment_label', filterSentiment);

      const queryStr = params.toString() ? `?${params.toString()}` : '';

      const [metricsRes, topicsRes, breakdownRes] = await Promise.all([
        fetch(`/api/analytics/overview${queryStr}`),
        fetch(`/api/analytics/topics${queryStr}`),
        fetch(`/api/analytics/instructor-breakdown${filterDepartment ? `?department_name=${encodeURIComponent(filterDepartment)}` : ''}`),
      ]);

      const [metricsData, topicsData, breakdownData] = await Promise.all([
        metricsRes.json(),
        topicsRes.json(),
        breakdownRes.json(),
      ]);

      setMetrics(metricsData);
      setTopics(topicsData);
      setInstructorBreakdown(breakdownData);
    } catch (err) {
      console.error('Failed to fetch filtered analytics:', err);
    } finally {
      setIsLoading(false);
    }
  }, [filterDepartment, filterSubject, filterInstructor, filterSentiment]);

  useEffect(() => {
    fetchDeptOverview();
  }, [fetchDeptOverview]);

  useEffect(() => {
    fetchFilteredData();
  }, [fetchFilteredData]);

  const handleDataChanged = () => {
    fetchDeptOverview();
    fetchFilteredData();
  };

  const total = metrics?.total_submissions || 0;
  const posCount = metrics?.sentiment_counts.positive || 0;
  const negCount = metrics?.sentiment_counts.negative || 0;
  const neuCount = metrics?.sentiment_counts.neutral || 0;
  const mixedCount = metrics?.sentiment_counts.mixed || 0;

  const posPct = total > 0 ? Math.round((posCount / total) * 100) : 0;
  const negPct = total > 0 ? Math.round((negCount / total) * 100) : 0;
  const neuPct = total > 0 ? Math.round((neuCount / total) * 100) : 0;

  const pieData = [
    { name: 'Positive', value: posCount, color: '#16A34A' },
    { name: 'Neutral', value: neuCount, color: '#6B7280' },
    { name: 'Negative', value: negCount, color: '#DC2626' },
  ].filter((d) => d.value > 0);

  const ratingChartData = metrics
    ? [
        { rating: '1 Star', count: metrics.rating_distribution[1] || 0 },
        { rating: '2 Stars', count: metrics.rating_distribution[2] || 0 },
        { rating: '3 Stars', count: metrics.rating_distribution[3] || 0 },
        { rating: '4 Stars', count: metrics.rating_distribution[4] || 0 },
        { rating: '5 Stars', count: metrics.rating_distribution[5] || 0 },
      ]
    : [];

  const isOtherSelected = filterDepartment === 'Other';

  return (
    <div>
      {/* Page Title & Management Header */}
      <div className="dash-header" style={{ marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.85rem', fontWeight: 700 }}>Administrator Intelligence Dashboard</h2>
        </div>

        <div style={{ display: 'flex', gap: '0.65rem' }}>
          <button
            className="btn-primary"
            onClick={() => {
              setManagementTab('departments');
              setIsManagementOpen(true);
            }}
            style={{ padding: '0.55rem 1rem', fontSize: '0.88rem' }}
          >
            <Settings size={15} />
            <span>Manage Academic Structure</span>
          </button>
        </div>
      </div>

      {/* 6.1 DEPARTMENT OVERVIEW CARDS */}
      <section style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Building2 size={18} color="var(--primary-yellow-dark)" />
            <span>Academic Departments & Feedback Status</span>
          </h3>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Real counts derived from stored records
          </span>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '1rem',
        }}>
          {deptOverview?.departments.map((dept) => (
            <div
              key={dept.id}
              onClick={() => {
                setFilterDepartment(filterDepartment === dept.name ? '' : dept.name);
              }}
              style={{
                background: '#FFFFFF',
                border: filterDepartment === dept.name ? '2px solid var(--primary-yellow)' : '1px solid var(--border-light)',
                borderTop: '4px solid var(--primary-yellow)',
                borderRadius: '10px',
                padding: '1.1rem 1.25rem',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                boxShadow: filterDepartment === dept.name ? 'var(--shadow-md)' : 'var(--shadow-sm)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                <h4 style={{ fontSize: '0.98rem', fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.3 }}>
                  {dept.name}
                </h4>
                {dept.code && (
                  <span className="tag-pill" style={{ fontWeight: 700, fontSize: '0.72rem' }}>
                    {dept.code}
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', gap: '1rem', fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '0.75rem' }}>
                <div>
                  <span style={{ fontWeight: 700, color: 'var(--text-primary)', display: 'block', fontSize: '1.1rem' }}>
                    {dept.subject_count}
                  </span>
                  <span>Active Subjects</span>
                </div>
                <div>
                  <span style={{ fontWeight: 700, color: 'var(--text-primary)', display: 'block', fontSize: '1.1rem' }}>
                    {dept.instructor_count}
                  </span>
                  <span>Instructors</span>
                </div>
                <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
                  <span style={{ fontWeight: 700, color: '#B45309', display: 'block', fontSize: '1.1rem' }}>
                    {dept.feedback_count}
                  </span>
                  <span>Feedback</span>
                </div>
              </div>
            </div>
          ))}

          {/* Special "Other" Card */}
          {deptOverview?.other && (
            <div
              onClick={() => {
                setFilterDepartment(filterDepartment === 'Other' ? '' : 'Other');
              }}
              style={{
                background: '#FFFFFF',
                border: filterDepartment === 'Other' ? '2px solid #854D0E' : '1px solid var(--border-light)',
                borderTop: '4px solid #854D0E',
                borderRadius: '10px',
                padding: '1.1rem 1.25rem',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                boxShadow: filterDepartment === 'Other' ? 'var(--shadow-md)' : 'var(--shadow-sm)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                <div>
                  <h4 style={{ fontSize: '0.98rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    Other
                  </h4>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    General Institutional Feedback
                  </p>
                </div>
                <span className="tag-pill accent" style={{ fontWeight: 700, fontSize: '0.72rem' }}>
                  Institutional
                </span>
              </div>
              <div style={{ display: 'flex', gap: '0.8rem', fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.75rem', alignItems: 'center' }}>
                <div>
                  <span style={{ fontWeight: 700, color: 'var(--text-primary)', display: 'block', fontSize: '1.1rem' }}>
                    {deptOverview.other.total_submissions}
                  </span>
                  <span>Total</span>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', marginLeft: 'auto', fontSize: '0.78rem' }}>
                  <span style={{ color: '#16A34A', fontWeight: 600 }}>Pos: {deptOverview.other.positive}</span>
                  <span style={{ color: '#4B5563', fontWeight: 600 }}>Neu: {deptOverview.other.neutral}</span>
                  <span style={{ color: '#DC2626', fontWeight: 600 }}>Neg: {deptOverview.other.negative}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* 6.2 DEPENDENT FILTERS */}
      <div className="filter-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Filter size={16} color="var(--primary-yellow-dark)" />
            <span style={{ fontSize: '0.92rem', fontWeight: 700 }}>Dependent Analytics Filters</span>
          </div>
          {(filterDepartment || filterSubject || filterInstructor || filterSentiment) && (
            <button
              onClick={() => {
                setFilterDepartment('');
                setFilterSubject('');
                setFilterInstructor('');
                setFilterSentiment('');
              }}
              style={{ fontSize: '0.78rem', color: '#B45309', fontWeight: 600 }}
            >
              Reset All Filters
            </button>
          )}
        </div>

        <div className="filter-grid">
          {/* 1. Department */}
          <div>
            <label className="form-label" style={{ fontSize: '0.78rem' }}>Department</label>
            <select
              className="form-select"
              value={filterDepartment}
              onChange={(e) => {
                setFilterDepartment(e.target.value);
                setFilterSubject('');
                setFilterInstructor('');
              }}
            >
              <option value="">All Departments</option>
              {deptOverview?.departments.map((d) => (
                <option key={d.id} value={d.name}>{d.name}</option>
              ))}
              <option value="Other">Other (General Institutional)</option>
            </select>
          </div>

          {/* 2. Subject (hidden/disabled if Other) */}
          <div>
            <label className="form-label" style={{ fontSize: '0.78rem' }}>Subject</label>
            <select
              className="form-select"
              value={filterSubject}
              onChange={(e) => {
                setFilterSubject(e.target.value);
                setFilterInstructor('');
              }}
              disabled={isOtherSelected}
            >
              <option value="">All Subjects {filterDepartment && !isOtherSelected ? `(${availableSubjects.length})` : ''}</option>
              {availableSubjects.map((s) => (
                <option key={s.id} value={s.name}>{s.name}</option>
              ))}
            </select>
          </div>

          {/* 3. Instructor (hidden/disabled if Other) */}
          <div>
            <label className="form-label" style={{ fontSize: '0.78rem' }}>Instructor</label>
            <select
              className="form-select"
              value={filterInstructor}
              onChange={(e) => setFilterInstructor(e.target.value)}
              disabled={isOtherSelected}
            >
              <option value="">All Instructors {availableInstructors.length > 0 ? `(${availableInstructors.length})` : ''}</option>
              {availableInstructors.map((i) => (
                <option key={i.id} value={i.name}>{i.name}</option>
              ))}
            </select>
          </div>

          {/* 4. Sentiment */}
          <div>
            <label className="form-label" style={{ fontSize: '0.78rem' }}>Sentiment</label>
            <select
              className="form-select"
              value={filterSentiment}
              onChange={(e) => setFilterSentiment(e.target.value)}
            >
              <option value="">All Sentiments</option>
              <option value="Positive">Positive Only</option>
              <option value="Neutral">Neutral Only</option>
              <option value="Negative">Negative Only</option>
            </select>
          </div>
        </div>
      </div>

      {/* 6.3 FOUR KPI CARDS */}
      <section className="stats-grid">
        <div className="stat-card accent-yellow">
          <div className="stat-title">Total Feedback Submissions</div>
          <div className="stat-value">{total}</div>
          <div className="stat-sub">
            {filterDepartment ? `Filtered for ${filterDepartment}` : 'Across all academic & institutional categories'}
          </div>
        </div>

        <div className="stat-card accent-green">
          <div className="stat-title">Positive Sentiment</div>
          <div className="stat-value" style={{ color: '#16A34A' }}>
            {posCount} <span style={{ fontSize: '1rem', fontWeight: 600 }}>({posPct}%)</span>
          </div>
          <div className="stat-sub">High instructional satisfaction & praise</div>
        </div>

        <div className="stat-card accent-red">
          <div className="stat-title">Negative Sentiment</div>
          <div className="stat-value" style={{ color: '#DC2626' }}>
            {negCount} <span style={{ fontSize: '1rem', fontWeight: 600 }}>({negPct}%)</span>
          </div>
          <div className="stat-sub">Actionable student concerns & feedback</div>
        </div>

        <div className="stat-card accent-grey">
          <div className="stat-title">Neutral & Mixed Sentiment</div>
          <div className="stat-value" style={{ color: '#4B5563' }}>
            {neuCount} <span style={{ fontSize: '1rem', fontWeight: 600 }}>({neuPct}%)</span>
          </div>
          <div className="stat-sub">
            Includes <strong>{mixedCount}</strong> mixed contrastive clauses
          </div>
        </div>
      </section>

      {/* 6.4 CHARTS: Sentiment Distribution & Rating Breakdown */}
      <section className="charts-grid">
        <div className="chart-card">
          <h3>Sentiment Distribution</h3>
          {pieData.length > 0 ? (
            <div style={{ height: '240px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <RechartsTooltip />
                  <Legend verticalAlign="bottom" height={36} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div style={{ height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9CA3AF' }}>
              No sentiment data available for this selection
            </div>
          )}
        </div>

        <div className="chart-card">
          <h3>Rating Breakdown</h3>
          <div style={{ height: '240px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={ratingChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                <XAxis dataKey="rating" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <RechartsTooltip />
                <Bar dataKey="count" fill="#EAB308" radius={[4, 4, 0, 0]} name="Submissions" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      {/* 6.5 INSTRUCTOR SENTIMENT BREAKDOWN */}
      {!isOtherSelected && instructorBreakdown.length > 0 && (
        <section style={{ marginBottom: '2.5rem' }}>
          <div className="section-title-wrap">
            <div>
              <h3 className="section-title">Instructor Sentiment Breakdown</h3>
              <p className="section-subtitle">Real feedback counts and sentiment proportions per instructor.</p>
            </div>
          </div>

          <div className="table-container">
            <table className="styled-table">
              <thead>
                <tr>
                  <th>Instructor Name</th>
                  <th>Department</th>
                  <th>Total Submissions</th>
                  <th>Positive</th>
                  <th>Neutral / Mixed</th>
                  <th>Negative</th>
                  <th>Avg Rating</th>
                </tr>
              </thead>
              <tbody>
                {instructorBreakdown.map((item, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 600 }}>{item.instructor_name}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{item.department}</td>
                    <td style={{ fontWeight: 700 }}>{item.total_feedback}</td>
                    <td>
                      <span style={{ color: '#16A34A', fontWeight: 600 }}>{item.positive}</span>
                    </td>
                    <td>
                      <span style={{ color: '#4B5563', fontWeight: 600 }}>{item.neutral}</span>
                      {item.mixed > 0 && (
                        <span style={{ fontSize: '0.75rem', color: '#B45309', marginLeft: '4px' }}>
                          ({item.mixed} mixed)
                        </span>
                      )}
                    </td>
                    <td>
                      <span style={{ color: '#DC2626', fontWeight: 600 }}>{item.negative}</span>
                    </td>
                    <td>
                      {item.total_feedback > 0 ? (
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px', fontWeight: 600 }}>
                          ★ {item.average_rating}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* 6.6 TOPIC INTELLIGENCE & SEMANTIC CLUSTERS */}
      <section style={{ marginBottom: '2.5rem' }}>
        <div className="section-title-wrap">
          <div>
            <h3 className="section-title">Topic Intelligence & Semantic Clusters</h3>
          </div>
          <span className="tag-pill accent" style={{ padding: '0.3rem 0.75rem', fontSize: '0.82rem' }}>
            {topics.length} {topics.length === 1 ? 'Topic Discovered' : 'Recurring Topics Discovered'}
          </span>
        </div>

        {topics.length === 0 ? (
          <div className="empty-state" style={{ padding: '2rem' }}>
            <p>No feedback clusters found for the current selection.</p>
          </div>
        ) : (
          <div className="topic-list">
            {topics.map((topic) => (
              <TopicCard key={topic.cluster_id} topic={topic} />
            ))}
          </div>
        )}
      </section>

      {/* 6.7 VIEW ALL FEEDBACK BUTTON */}
      <section style={{ textAlign: 'center', padding: '1.5rem 0 3rem 0' }}>
        <button
          className="btn-primary"
          onClick={onNavigateToAllFeedback}
          style={{
            padding: '0.9rem 2rem',
            fontSize: '1rem',
            boxShadow: '0 4px 6px -1px rgba(234, 179, 8, 0.4)',
          }}
        >
          <span>View Total Feedback Received</span>
          <ArrowRight size={18} />
        </button>
      </section>

      {/* Academic Structure Management Modal */}
      <AcademicManagementModal
        isOpen={isManagementOpen}
        onClose={() => setIsManagementOpen(false)}
        onDataChanged={handleDataChanged}
        initialTab={managementTab}
      />
    </div>
  );
};
