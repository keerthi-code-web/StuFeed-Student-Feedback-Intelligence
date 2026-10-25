
import React, { useCallback, useEffect, useState } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
} from 'recharts';
import {
  Filter,
  Settings,
  Building2,
  ArrowRight,
} from 'lucide-react';

import {
  OverviewMetrics,
  TopicCluster,
  Subject,
  Instructor,
  DepartmentsOverviewResponse,
} from '../types';

import { TopicCard } from '../components/TopicCard';
import { AcademicManagementModal } from '../components/AcademicManagementModal';


interface Props {
  onNavigateToAllFeedback: () => void;
}

interface InstructorBreakdownItem {
  instructor_name: string;
  department: string;
  total_feedback: number;
  positive: number;
  negative: number;
  neutral: number;
  mixed: number;
  average_rating: number;
}

const semesterOptions = Array.from(
  { length: 8 },
  (_, index) => index + 1
);

async function parseResponse(response: Response) {
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      typeof data.detail === 'string'
        ? data.detail
        : `Request failed with status ${response.status}.`
    );
  }

  return data;
}

export const AdminDashboardPage: React.FC<Props> = ({
  onNavigateToAllFeedback,
}) => {
  const [deptOverview, setDeptOverview] =
    useState<DepartmentsOverviewResponse | null>(null);

  const [metrics, setMetrics] = useState<OverviewMetrics | null>(null);
  const [topics, setTopics] = useState<TopicCluster[]>([]);
  const [instructorBreakdown, setInstructorBreakdown] =
    useState<InstructorBreakdownItem[]>([]);

  const [filterDepartment, setFilterDepartment] = useState('');
  const [filterSemester, setFilterSemester] = useState('');
  const [filterSubject, setFilterSubject] = useState('');
  const [filterInstructor, setFilterInstructor] = useState('');
  const [filterSentiment, setFilterSentiment] = useState('');

  const [availableSubjects, setAvailableSubjects] = useState<Subject[]>([]);
  const [availableInstructors, setAvailableInstructors] =
    useState<Instructor[]>([]);

  const [isManagementOpen, setIsManagementOpen] = useState(false);
  const [managementTab, setManagementTab] = useState<
    'departments' | 'subjects' | 'instructors'
  >('departments');

  const [isLoading, setIsLoading] = useState(true);
  const [dashboardError, setDashboardError] = useState<string | null>(null);

  const isOtherSelected = filterDepartment === 'Other';

  // Load department overview cards.
  const fetchDeptOverview = useCallback(async () => {
    try {
      const response = await fetch('/api/departments/overview');
      const data = await parseResponse(response);
      setDeptOverview(data);
    } catch (error) {
      console.error('Failed to load department overview:', error);
    }
  }, []);

  // Load subjects matching the selected department and semester.
  useEffect(() => {
    let cancelled = false;

    if (!filterDepartment || isOtherSelected) {
      setAvailableSubjects([]);
      setFilterSubject('');
      setAvailableInstructors([]);
      setFilterInstructor('');
      return;
    }

    const params = new URLSearchParams({
      department_name: filterDepartment,
    });

    if (filterSemester) {
      params.set('semester', filterSemester);
    }

    fetch(`/api/subjects?${params.toString()}`)
      .then(parseResponse)
      .then((data: Subject[]) => {
        if (cancelled) return;

        setAvailableSubjects(data);

        if (
          filterSubject &&
          !data.some((subject) => subject.name === filterSubject)
        ) {
          setFilterSubject('');
          setFilterInstructor('');
        }
      })
      .catch((error) => {
        console.error('Failed to load filtered subjects:', error);
        if (!cancelled) setAvailableSubjects([]);
      });

    return () => {
      cancelled = true;
    };
  }, [filterDepartment, filterSemester, isOtherSelected]);

  // Load instructors matching the department and subject selection.
  useEffect(() => {
    let cancelled = false;

    if (!filterDepartment || isOtherSelected) {
      setAvailableInstructors([]);
      setFilterInstructor('');
      return;
    }

    const params = new URLSearchParams({
      department_name: filterDepartment,
    });

    if (filterSubject) {
      const selectedSubject = availableSubjects.find(
        (subject) => subject.name === filterSubject
      );

      if (selectedSubject) {
        params.set('subject_id', String(selectedSubject.id));
      }
    }

    fetch(`/api/instructors?${params.toString()}`)
      .then(parseResponse)
      .then((data: Instructor[]) => {
        if (cancelled) return;

        setAvailableInstructors(data);

        if (
          filterInstructor &&
          !data.some((instructor) => instructor.name === filterInstructor)
        ) {
          setFilterInstructor('');
        }
      })
      .catch((error) => {
        console.error('Failed to load filtered instructors:', error);
        if (!cancelled) setAvailableInstructors([]);
      });

    return () => {
      cancelled = true;
    };
  }, [
    filterDepartment,
    filterSubject,
    availableSubjects,
    isOtherSelected,
  ]);

  // Load metrics, topics, and instructor breakdown using shared filters.
  const fetchFilteredData = useCallback(async () => {
    setIsLoading(true);
    setDashboardError(null);

    try {
      const params = new URLSearchParams();

      if (filterDepartment) {
        params.set('department_name', filterDepartment);
      }

      if (filterSemester) {
        params.set('semester', filterSemester);
      }

      if (filterSubject) {
        params.set('subject_name', filterSubject);
      }

      if (filterInstructor) {
        params.set('instructor_name', filterInstructor);
      }

      if (filterSentiment) {
        params.set('sentiment_label', filterSentiment);
      }

      const query = params.toString();
      const querySuffix = query ? `?${query}` : '';

      const breakdownParams = new URLSearchParams();

      if (filterDepartment) {
        breakdownParams.set('department_name', filterDepartment);
      }

      if (filterSemester) {
        breakdownParams.set('semester', filterSemester);
      }

      const breakdownQuery = breakdownParams.toString();
      const breakdownSuffix = breakdownQuery
        ? `?${breakdownQuery}`
        : '';

      const [metricsResponse, topicsResponse, breakdownResponse] =
        await Promise.all([
          fetch(`/api/analytics/overview${querySuffix}`),
          fetch(`/api/analytics/topics${querySuffix}`),
          fetch(`/api/analytics/instructor-breakdown${breakdownSuffix}`),
        ]);

      const [metricsData, topicsData, breakdownData] = await Promise.all([
        parseResponse(metricsResponse),
        parseResponse(topicsResponse),
        parseResponse(breakdownResponse),
      ]);

      setMetrics(metricsData);
      setTopics(topicsData);
      setInstructorBreakdown(breakdownData);
    } catch (error) {
      console.error('Failed to fetch filtered analytics:', error);

      setDashboardError(
        error instanceof Error
          ? error.message
          : 'Unable to load dashboard analytics.'
      );
    } finally {
      setIsLoading(false);
    }
  }, [
    filterDepartment,
    filterSemester,
    filterSubject,
    filterInstructor,
    filterSentiment,
  ]);

  useEffect(() => {
    void fetchDeptOverview();
  }, [fetchDeptOverview]);

  useEffect(() => {
    void fetchFilteredData();
  }, [fetchFilteredData]);

  const handleDataChanged = () => {
    void fetchDeptOverview();
    void fetchFilteredData();
  };

  const resetFilters = () => {
    setFilterDepartment('');
    setFilterSemester('');
    setFilterSubject('');
    setFilterInstructor('');
    setFilterSentiment('');
  };

  const total = metrics?.total_submissions ?? 0;
  const positive = metrics?.sentiment_counts.positive ?? 0;
  const negative = metrics?.sentiment_counts.negative ?? 0;
  const neutral = metrics?.sentiment_counts.neutral ?? 0;
  const mixed = metrics?.sentiment_counts.mixed ?? 0;

  const positivePercentage =
    total > 0 ? Math.round((positive / total) * 100) : 0;

  const negativePercentage =
    total > 0 ? Math.round((negative / total) * 100) : 0;

  const neutralPercentage =
    total > 0 ? Math.round((neutral / total) * 100) : 0;

  const pieData = [
    { name: 'Positive', value: positive, color: '#16A34A' },
    { name: 'Neutral', value: neutral, color: '#6B7280' },
    { name: 'Negative', value: negative, color: '#DC2626' },
  ].filter((item) => item.value > 0);

  const ratingChartData = metrics
    ? [
        { rating: '1 Star', count: metrics.rating_distribution[1] || 0 },
        { rating: '2 Stars', count: metrics.rating_distribution[2] || 0 },
        { rating: '3 Stars', count: metrics.rating_distribution[3] || 0 },
        { rating: '4 Stars', count: metrics.rating_distribution[4] || 0 },
        { rating: '5 Stars', count: metrics.rating_distribution[5] || 0 },
      ]
    : [];

  const filterSummary = [
    filterDepartment || null,
    filterSemester ? `Semester ${filterSemester}` : null,
    filterSubject || null,
    filterInstructor || null,
    filterSentiment || null,
  ].filter(Boolean);

  return (
    <div>
      {/* Dashboard heading */}
      <div
        className="dash-header"
        style={{
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          flexWrap: 'wrap',
        }}
      >
        <div>
          <h2 style={{ fontSize: '1.85rem', fontWeight: 700 }}>
            Administrator Intelligence Dashboard
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
            Review feedback, sentiment, and academic topics by semester.
          </p>
        </div>

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

      {dashboardError && (
        <div
          style={{
            padding: '0.85rem 1rem',
            marginBottom: '1rem',
            borderRadius: '6px',
            background: '#FEF2F2',
            color: '#B91C1C',
            border: '1px solid #FECACA',
          }}
        >
          {dashboardError}
        </div>
      )}

      {/* Department overview cards */}
      <section style={{ marginBottom: '2rem' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '0.75rem',
            flexWrap: 'wrap',
            marginBottom: '0.85rem',
          }}
        >
          <h3
            style={{
              fontSize: '1.1rem',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
            }}
          >
            <Building2 size={18} color="var(--primary-yellow-dark)" />
            Academic Departments &amp; Feedback Status
          </h3>

          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Department overview counts currently cover all semesters.
          </span>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: '1rem',
          }}
        >
          {deptOverview?.departments.map((department) => (
            <button
              key={department.id}
              type="button"
              onClick={() => {
                setFilterDepartment((current) =>
                  current === department.name ? '' : department.name
                );
                setFilterSubject('');
                setFilterInstructor('');
              }}
              style={{
                textAlign: 'left',
                background: '#FFFFFF',
                border:
                  filterDepartment === department.name
                    ? '2px solid var(--primary-yellow)'
                    : '1px solid var(--border-light)',
                borderTop: '4px solid var(--primary-yellow)',
                borderRadius: '10px',
                padding: '1.1rem 1.25rem',
                cursor: 'pointer',
                boxShadow:
                  filterDepartment === department.name
                    ? 'var(--shadow-md)'
                    : 'var(--shadow-sm)',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: '0.5rem',
                  marginBottom: '0.6rem',
                }}
              >
                <strong>{department.name}</strong>
                {department.code && (
                  <span className="tag-pill">{department.code}</span>
                )}
              </div>

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: '0.7rem',
                  fontSize: '0.82rem',
                  color: 'var(--text-secondary)',
                }}
              >
                <span>
                  <strong>{department.subject_count}</strong>
                  <br />
                  Subjects
                </span>
                <span>
                  <strong>{department.instructor_count}</strong>
                  <br />
                  Instructors
                </span>
                <span>
                  <strong>{department.feedback_count}</strong>
                  <br />
                  Feedback
                </span>
              </div>
            </button>
          ))}

          {deptOverview?.other && (
            <button
              type="button"
              onClick={() => {
                setFilterDepartment((current) =>
                  current === 'Other' ? '' : 'Other'
                );
                setFilterSubject('');
                setFilterInstructor('');
              }}
              style={{
                textAlign: 'left',
                background: '#FFFFFF',
                border:
                  filterDepartment === 'Other'
                    ? '2px solid #854D0E'
                    : '1px solid var(--border-light)',
                borderTop: '4px solid #854D0E',
                borderRadius: '10px',
                padding: '1.1rem 1.25rem',
                cursor: 'pointer',
              }}
            >
              <strong>Other — General Institutional Feedback</strong>
              <div style={{ marginTop: '0.75rem', fontSize: '0.85rem' }}>
                Total: {deptOverview.other.total_submissions}
                <div style={{ display: 'flex', gap: '0.65rem', marginTop: '0.35rem', flexWrap: 'wrap' }}>
                  <span style={{ color: '#16A34A' }}>
                    Positive: {deptOverview.other.positive}
                  </span>
                  <span>Neutral: {deptOverview.other.neutral}</span>
                  <span style={{ color: '#DC2626' }}>
                    Negative: {deptOverview.other.negative}
                  </span>
                </div>
              </div>
            </button>
          )}
        </div>
      </section>

      {/* Semester-aware analytics filters */}
      <div className="filter-card">
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '0.75rem',
            flexWrap: 'wrap',
            marginBottom: '0.85rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Filter size={16} color="var(--primary-yellow-dark)" />
            <span style={{ fontSize: '0.92rem', fontWeight: 700 }}>
              Dependent Analytics Filters
            </span>
          </div>

          {filterSummary.length > 0 && (
            <button
              onClick={resetFilters}
              style={{ fontSize: '0.78rem', color: '#B45309', fontWeight: 600 }}
            >
              Reset All Filters
            </button>
          )}
        </div>

        <div className="filter-grid">
          <div>
            <label className="form-label" style={{ fontSize: '0.78rem' }}>
              Department
            </label>
            <select
              className="form-select"
              value={filterDepartment}
              onChange={(event) => {
                setFilterDepartment(event.target.value);
                setFilterSubject('');
                setFilterInstructor('');
              }}
            >
              <option value="">All Departments</option>
              {deptOverview?.departments.map((department) => (
                <option key={department.id} value={department.name}>
                  {department.name}
                </option>
              ))}
              <option value="Other">Other (General Institutional)</option>
            </select>
          </div>

          <div>
            <label className="form-label" style={{ fontSize: '0.78rem' }}>
              Semester
            </label>
            <select
              className="form-select"
              value={filterSemester}
              onChange={(event) => {
                setFilterSemester(event.target.value);
                setFilterSubject('');
                setFilterInstructor('');
              }}
            >
              <option value="">All Semesters</option>
              {semesterOptions.map((semester) => (
                <option key={semester} value={semester}>
                  Semester {semester}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="form-label" style={{ fontSize: '0.78rem' }}>
              Subject
            </label>
            <select
              className="form-select"
              value={filterSubject}
              onChange={(event) => {
                setFilterSubject(event.target.value);
                setFilterInstructor('');
              }}
              disabled={!filterDepartment || isOtherSelected}
            >
              <option value="">
                {availableSubjects.length
                  ? 'All Subjects'
                  : 'All Subjects (select a department)'}
              </option>
              {availableSubjects.map((subject) => (
                <option key={subject.id} value={subject.name}>
                  {subject.name} — Sem {subject.semester}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="form-label" style={{ fontSize: '0.78rem' }}>
              Instructor
            </label>
            <select
              className="form-select"
              value={filterInstructor}
              onChange={(event) => setFilterInstructor(event.target.value)}
              disabled={!filterDepartment || isOtherSelected}
            >
              <option value="">All Instructors</option>
              {availableInstructors.map((instructor) => (
                <option key={instructor.id} value={instructor.name}>
                  {instructor.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="form-label" style={{ fontSize: '0.78rem' }}>
              Sentiment
            </label>
            <select
              className="form-select"
              value={filterSentiment}
              onChange={(event) => setFilterSentiment(event.target.value)}
            >
              <option value="">All Sentiments</option>
              <option value="Positive">Positive Only</option>
              <option value="Neutral">Neutral Only</option>
              <option value="Negative">Negative Only</option>
            </select>
          </div>
        </div>
      </div>

      {/* KPI cards */}
      <section className="stats-grid">
        <div className="stat-card accent-yellow">
          <div className="stat-title">Total Feedback Submissions</div>
          <div className="stat-value">{total}</div>
          <div className="stat-sub">
            {filterSemester
              ? `Semester ${filterSemester}`
              : 'All semesters'}
            {filterDepartment ? ` · ${filterDepartment}` : ''}
          </div>
        </div>

        <div className="stat-card accent-green">
          <div className="stat-title">Positive Sentiment</div>
          <div className="stat-value" style={{ color: '#16A34A' }}>
            {positive}{' '}
            <span style={{ fontSize: '1rem', fontWeight: 600 }}>
              ({positivePercentage}%)
            </span>
          </div>
          <div className="stat-sub">Positive feedback in this selection</div>
        </div>

        <div className="stat-card accent-red">
          <div className="stat-title">Negative Sentiment</div>
          <div className="stat-value" style={{ color: '#DC2626' }}>
            {negative}{' '}
            <span style={{ fontSize: '1rem', fontWeight: 600 }}>
              ({negativePercentage}%)
            </span>
          </div>
          <div className="stat-sub">Concerns in this selection</div>
        </div>

        <div className="stat-card accent-grey">
          <div className="stat-title">Neutral &amp; Mixed Sentiment</div>
          <div className="stat-value" style={{ color: '#4B5563' }}>
            {neutral}{' '}
            <span style={{ fontSize: '1rem', fontWeight: 600 }}>
              ({neutralPercentage}%)
            </span>
          </div>
          <div className="stat-sub">
            Includes {mixed} mixed feedback records
          </div>
        </div>
      </section>

      {isLoading && (
        <p style={{ margin: '1rem 0', color: 'var(--text-secondary)' }}>
          Updating analytics…
        </p>
      )}

      {/* Charts */}
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
                    {pieData.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <RechartsTooltip />
                  <Legend verticalAlign="bottom" height={36} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div
              style={{
                height: '200px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#9CA3AF',
              }}
            >
              No sentiment data for this selection.
            </div>
          )}
        </div>

        <div className="chart-card">
          <h3>Rating Breakdown</h3>
          <div style={{ height: '240px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={ratingChartData}
                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke="#F1F5F9"
                />
                <XAxis dataKey="rating" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <RechartsTooltip />
                <Bar
                  dataKey="count"
                  fill="#EAB308"
                  radius={[4, 4, 0, 0]}
                  name="Submissions"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      {/* Instructor breakdown */}
      {!isOtherSelected && (
        <section style={{ marginBottom: '2.5rem' }}>
          <div className="section-title-wrap">
            <div>
              <h3 className="section-title">
                Instructor Sentiment Breakdown
              </h3>
              <p className="section-subtitle">
                {filterSemester
                  ? `Semester ${filterSemester} feedback`
                  : 'Feedback across all semesters'}
              </p>
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
                  <th>Average Rating</th>
                </tr>
              </thead>
              <tbody>
                {instructorBreakdown.map((item) => (
                  <tr key={`${item.instructor_name}-${item.department}`}>
                    <td style={{ fontWeight: 600 }}>{item.instructor_name}</td>
                    <td>{item.department || '—'}</td>
                    <td style={{ fontWeight: 700 }}>{item.total_feedback}</td>
                    <td style={{ color: '#16A34A', fontWeight: 600 }}>
                      {item.positive}
                    </td>
                    <td>
                      {item.neutral}
                      {item.mixed > 0 ? ` (${item.mixed} mixed)` : ''}
                    </td>
                    <td style={{ color: '#DC2626', fontWeight: 600 }}>
                      {item.negative}
                    </td>
                    <td>
                      {item.total_feedback > 0
                        ? `★ ${item.average_rating}`
                        : '—'}
                    </td>
                  </tr>
                ))}

                {instructorBreakdown.length === 0 && (
                  <tr>
                    <td colSpan={7}>
                      No instructor records match this selection.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Topic intelligence */}
      <section style={{ marginBottom: '2.5rem' }}>
        <div className="section-title-wrap">
          <div>
            <h3 className="section-title">
              Topic Intelligence &amp; Semantic Clusters
            </h3>
            <p className="section-subtitle">
              Themes discovered from the selected feedback records.
            </p>
          </div>

          <span className="tag-pill accent">
            {topics.length}{' '}
            {topics.length === 1 ? 'Topic Discovered' : 'Topics Discovered'}
          </span>
        </div>

        {topics.length === 0 ? (
          <div className="empty-state" style={{ padding: '2rem' }}>
            <p>No feedback clusters found for this selection.</p>
          </div>
        ) : (
          <div className="topic-list">
            {topics.map((topic) => (
              <TopicCard key={topic.cluster_id} topic={topic} />
            ))}
          </div>
        )}
      </section>

      {/* All feedback navigation */}
      <section style={{ textAlign: 'center', padding: '1.5rem 0 3rem' }}>
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

      <AcademicManagementModal
        isOpen={isManagementOpen}
        onClose={() => setIsManagementOpen(false)}
        onDataChanged={handleDataChanged}
        initialTab={managementTab}
      />
    </div>
  );
};
