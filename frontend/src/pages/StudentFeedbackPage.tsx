
import React, { useState, useEffect } from 'react';
import {
  Send,
  CheckCircle2,
  AlertCircle,
  Star,
  Loader2,
} from 'lucide-react';

import {
  Department,
  Subject,
  Instructor,
  FeedbackSubmission,
} from '../types';

import { SentimentBadge } from '../components/SentimentBadge';


export const StudentFeedbackPage: React.FC = () => {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [instructors, setInstructors] = useState<Instructor[]>([]);

  // Student and feedback form state.
  const [registerNumber, setRegisterNumber] = useState('');
  const [studentName, setStudentName] = useState('');
  const [selectedDepartment, setSelectedDepartment] = useState('');
  const [selectedSemester, setSelectedSemester] = useState<number>(1);
  const [selectedSubject, setSelectedSubject] = useState('');
  const [selectedInstructor, setSelectedInstructor] = useState('');
  const [rating, setRating] = useState<number>(5);
  const [feedbackText, setFeedbackText] = useState('');

  // Submission state.
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successResult, setSuccessResult] =
    useState<FeedbackSubmission | null>(null);

  const isOther = selectedDepartment.toLowerCase() === 'other';

  // Load active departments.
  useEffect(() => {
    let cancelled = false;

    fetch('/api/departments')
      .then(async (response) => {
        if (!response.ok) {
          throw new Error('Failed to load departments.');
        }
        return response.json();
      })
      .then((data: Department[]) => {
        if (cancelled) return;

        const activeDepartments = data.filter(
          (department) => department.is_active
        );

        setDepartments(activeDepartments);

        if (activeDepartments.length > 0) {
          setSelectedDepartment((current) => {
            if (
              current &&
              activeDepartments.some((item) => item.name === current)
            ) {
              return current;
            }
            return activeDepartments[0].name;
          });
        }
      })
      .catch((error) => {
        console.error('Failed to load departments:', error);
        if (!cancelled) {
          setErrorMessage(
            'Unable to load departments. Refresh the page and try again.'
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Load subjects whenever the department or semester changes.
  useEffect(() => {
    let cancelled = false;

    if (!selectedDepartment || isOther) {
      setSubjects([]);
      setSelectedSubject('');
      setInstructors([]);
      setSelectedInstructor('');
      return;
    }

    setSubjects([]);
    setSelectedSubject('');
    setInstructors([]);
    setSelectedInstructor('');

    const params = new URLSearchParams({
      department_name: selectedDepartment,
      semester: String(selectedSemester),
    });

    fetch(`/api/subjects?${params.toString()}`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error('Failed to load subjects.');
        }
        return response.json();
      })
      .then((data: Subject[]) => {
        if (cancelled) return;

        setSubjects(data);

        if (data.length > 0) {
          setSelectedSubject(data[0].name);
        }
      })
      .catch((error) => {
        console.error('Failed to load subjects:', error);
        if (!cancelled) {
          setSubjects([]);
          setSelectedSubject('');
          setErrorMessage(
            'Unable to load subjects for the selected semester.'
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedDepartment, selectedSemester, isOther]);

  // Load instructors assigned to the selected subject.
  useEffect(() => {
    let cancelled = false;

    if (isOther || !selectedDepartment || !selectedSubject) {
      setInstructors([]);
      setSelectedInstructor('');
      return;
    }

    const subject = subjects.find(
      (item) => item.name === selectedSubject
    );

    if (!subject) {
      setInstructors([]);
      setSelectedInstructor('');
      return;
    }

    setInstructors([]);
    setSelectedInstructor('');

    const params = new URLSearchParams({
      department_name: selectedDepartment,
      subject_id: String(subject.id),
    });

    fetch(`/api/instructors?${params.toString()}`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error('Failed to load instructors.');
        }
        return response.json();
      })
      .then((data: Instructor[]) => {
        if (cancelled) return;

        setInstructors(data);

        if (data.length > 0) {
          setSelectedInstructor(data[0].name);
        }
      })
      .catch((error) => {
        console.error('Failed to load instructors:', error);
        if (!cancelled) {
          setInstructors([]);
          setSelectedInstructor('');
          setErrorMessage(
            'Unable to load instructors for the selected subject.'
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedDepartment, selectedSubject, subjects, isOther]);

  const handleDepartmentChange = (value: string) => {
    setSelectedDepartment(value);
    setSelectedSemester(1);
    setSelectedSubject('');
    setSelectedInstructor('');
    setSubjects([]);
    setInstructors([]);
    setErrorMessage(null);
    setSuccessResult(null);
  };

  const handleSemesterChange = (value: number) => {
    setSelectedSemester(value);
    setSelectedSubject('');
    setSelectedInstructor('');
    setSubjects([]);
    setInstructors([]);
    setErrorMessage(null);
    setSuccessResult(null);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setErrorMessage(null);
    setSuccessResult(null);

    const finalRegisterNumber = registerNumber.trim();
    const finalStudentName = studentName.trim();
    const finalDepartment = selectedDepartment.trim();
    const finalFeedbackText = feedbackText.trim();

    if (!finalRegisterNumber) {
      setErrorMessage('Student Register Number is required.');
      return;
    }

    if (!finalStudentName) {
      setErrorMessage('Student Full Name is required.');
      return;
    }

    if (!finalDepartment) {
      setErrorMessage('Please select a department or category.');
      return;
    }

    if (!isOther) {
      if (
        selectedSemester < 1 ||
        selectedSemester > 8
      ) {
        setErrorMessage('Please select a valid semester.');
        return;
      }

      if (!selectedSubject.trim()) {
        setErrorMessage(
          `Please select a subject for ${finalDepartment}.`
        );
        return;
      }

      if (!selectedInstructor.trim()) {
        setErrorMessage(
          `Please select an instructor for ${selectedSubject}.`
        );
        return;
      }
    }

    if (!Number.isInteger(rating) || rating < 1 || rating > 5) {
      setErrorMessage('Rating must be between 1 and 5.');
      return;
    }

    if (finalFeedbackText.length < 5) {
      setErrorMessage(
        'Written feedback must contain at least 5 characters.'
      );
      return;
    }

    setIsSubmitting(true);

    try {
      const payload: {
        register_number: string;
        student_name: string;
        department_name: string;
        semester?: number;
        subject_name?: string;
        instructor_name?: string;
        rating: number;
        feedback_text: string;
      } = {
        register_number: finalRegisterNumber,
        student_name: finalStudentName,
        department_name: finalDepartment,
        rating,
        feedback_text: finalFeedbackText,
      };

      if (!isOther) {
        payload.semester = selectedSemester;
        payload.subject_name = selectedSubject.trim();
        payload.instructor_name = selectedInstructor.trim();
      }

      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        const detail =
          typeof data.detail === 'string'
            ? data.detail
            : 'Submission failed. Please check your inputs.';

        throw new Error(detail);
      }

      setSuccessResult(data as FeedbackSubmission);
      setFeedbackText('');
    } catch (error) {
      console.error('Feedback submission failed:', error);
      setErrorMessage(
        error instanceof Error
          ? error.message
          : 'An unexpected network error occurred.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const academicFieldsUnavailable =
    !isOther &&
    (subjects.length === 0 || instructors.length === 0);

  return (
    <div style={{ maxWidth: '780px', margin: '0 auto' }}>
      <div className="form-card">
        <div className="form-header">
          <h2>Submit Academic Course Feedback</h2>
          <p>
            Share your experience to help improve curriculum quality,
            laboratory resources, and instructional pacing.
          </p>
        </div>

        {successResult && (
          <div className="confirmation-banner">
            <h4>
              <CheckCircle2 size={20} />
              Feedback Submitted &amp; Analyzed Successfully!
            </h4>

            <p>
              Your feedback for{' '}
              <strong>
                {successResult.is_other
                  ? 'General Institutional Feedback (Other)'
                  : `${successResult.subject_name} (${successResult.instructor_name})`}
              </strong>{' '}
              under {successResult.department_name}
              {!successResult.is_other
                ? `, Semester ${successResult.semester ?? selectedSemester}`
                : ''}{' '}
              has been classified by the NLP intelligence engine.
            </p>

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.65rem',
                marginTop: '0.4rem',
              }}
            >
              <span
                style={{
                  fontSize: '0.82rem',
                  color: '#166534',
                  fontWeight: 600,
                }}
              >
                NLP Sentiment Output:
              </span>

              <SentimentBadge
                sentiment={successResult.sentiment_label}
                detail={successResult.sentiment_detail}
                confidence={successResult.sentiment_confidence}
                isMixed={successResult.is_mixed}
              />
            </div>
          </div>
        )}

        {errorMessage && (
          <div
            style={{
              background: '#FEF2F2',
              border: '1px solid #FECACA',
              borderLeft: '4px solid #DC2626',
              borderRadius: '6px',
              padding: '0.85rem 1rem',
              color: '#B91C1C',
              fontSize: '0.88rem',
              marginBottom: '1.5rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <AlertCircle size={18} />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            {/* Student identity */}
            <div className="form-group">
              <label className="form-label">
                Student Register Number{' '}
                <span className="required-star">*</span>
              </label>

              <input
                type="text"
                className="form-input"
                placeholder="e.g. 922524243088"
                value={registerNumber}
                onChange={(event) =>
                  setRegisterNumber(event.target.value)
                }
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">
                Student Full Name{' '}
                <span className="required-star">*</span>
              </label>

              <input
                type="text"
                className="form-input"
                placeholder="e.g. Alex Morgan"
                value={studentName}
                onChange={(event) =>
                  setStudentName(event.target.value)
                }
                required
              />
            </div>

            {/* Department */}
            <div className="form-group full-width">
              <label className="form-label">
                Department / Feedback Category{' '}
                <span className="required-star">*</span>
              </label>

              <select
                className="form-select"
                value={selectedDepartment}
                onChange={(event) =>
                  handleDepartmentChange(event.target.value)
                }
                required
              >
                <option value="">Select a department</option>

                {departments.map((department) => (
                  <option
                    key={department.id}
                    value={department.name}
                  >
                    {department.name}
                    {department.code ? ` (${department.code})` : ''}
                  </option>
                ))}

                <option value="Other">
                  Other (General Institutional Feedback)
                </option>
              </select>
            </div>

            {/* Semester */}
            {!isOther && (
              <div className="form-group full-width">
                <label className="form-label">
                  Semester{' '}
                  <span className="required-star">*</span>
                </label>

                <select
                  className="form-select"
                  value={selectedSemester}
                  onChange={(event) =>
                    handleSemesterChange(Number(event.target.value))
                  }
                  required
                  disabled={!selectedDepartment}
                >
                  {Array.from(
                    { length: 8 },
                    (_, index) => index + 1
                  ).map((semester) => (
                    <option key={semester} value={semester}>
                      Semester {semester}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Subject and instructor */}
            {!isOther && (
              <>
                <div className="form-group">
                  <label className="form-label">
                    Subject Name{' '}
                    <span className="required-star">*</span>
                  </label>

                  <select
                    className="form-select"
                    value={selectedSubject}
                    onChange={(event) => {
                      setSelectedSubject(event.target.value);
                      setSelectedInstructor('');
                      setInstructors([]);
                      setErrorMessage(null);
                    }}
                    required
                    disabled={subjects.length === 0}
                  >
                    <option value="">
                      {subjects.length === 0
                        ? 'No subjects configured for this semester'
                        : 'Select a subject'}
                    </option>

                    {subjects.map((subject) => (
                      <option
                        key={subject.id}
                        value={subject.name}
                      >
                        {subject.name}
                        {subject.code ? ` (${subject.code})` : ''}
                      </option>
                    ))}
                  </select>

                  {subjects.length === 0 && (
                    <span
                      style={{
                        fontSize: '0.75rem',
                        color: '#B45309',
                        marginTop: '0.25rem',
                      }}
                    >
                      An administrator must configure subjects for
                      this department and semester.
                    </span>
                  )}
                </div>

                <div className="form-group">
                  <label className="form-label">
                    Assigned Instructor{' '}
                    <span className="required-star">*</span>
                  </label>

                  <select
                    className="form-select"
                    value={selectedInstructor}
                    onChange={(event) =>
                      setSelectedInstructor(event.target.value)
                    }
                    required
                    disabled={instructors.length === 0}
                  >
                    <option value="">
                      {instructors.length === 0
                        ? 'No assigned instructors'
                        : 'Select an instructor'}
                    </option>

                    {instructors.map((instructor) => (
                      <option
                        key={instructor.id}
                        value={instructor.name}
                      >
                        {instructor.name}
                      </option>
                    ))}
                  </select>

                  {selectedSubject && instructors.length === 0 && (
                    <span
                      style={{
                        fontSize: '0.75rem',
                        color: '#B45309',
                        marginTop: '0.25rem',
                      }}
                    >
                      An administrator must assign an instructor
                      to this subject.
                    </span>
                  )}
                </div>
              </>
            )}

            {/* Rating */}
            <div className="form-group full-width">
              <label className="form-label">
                Course &amp; Experience Rating{' '}
                <span className="required-star">*</span>
                <span
                  style={{
                    fontSize: '0.78rem',
                    color: 'var(--text-secondary)',
                  }}
                >
                  {' '}Selected: {rating} out of 5 stars
                </span>
              </label>

              <div className="rating-selector">
                {[1, 2, 3, 4, 5].map((value) => (
                  <button
                    key={value}
                    type="button"
                    className={`rating-btn ${
                      rating === value ? 'selected' : ''
                    }`}
                    onClick={() => setRating(value)}
                    aria-label={`Rate ${value} out of 5`}
                  >
                    <Star
                      size={15}
                      fill={rating >= value ? '#EAB308' : 'none'}
                      color={rating >= value ? '#CA8A04' : '#9CA3AF'}
                    />
                    <span>{value}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Written feedback */}
            <div className="form-group full-width">
              <div className="form-label">
                <span>
                  Written Feedback{' '}
                  <span className="required-star">*</span>
                </span>

                <span className="char-counter">
                  {feedbackText.length} characters
                </span>
              </div>

              <textarea
                className="form-textarea"
                placeholder={
                  isOther
                    ? 'Provide general institutional feedback regarding campus facilities, library, administrative processes, or student services...'
                    : 'Describe your learning experience, instructional clarity, laboratory resources, course pace, or evaluation criteria...'
                }
                value={feedbackText}
                onChange={(event) =>
                  setFeedbackText(event.target.value)
                }
                required
                minLength={5}
                maxLength={2000}
              />
            </div>
          </div>

          <div
            style={{
              marginTop: '1.25rem',
              display: 'flex',
              justifyContent: 'flex-end',
            }}
          >
            <button
              type="submit"
              className="btn-primary"
              disabled={isSubmitting || academicFieldsUnavailable}
              style={{
                opacity:
                  isSubmitting || academicFieldsUnavailable
                    ? 0.7
                    : 1,
                minWidth: '180px',
                justifyContent: 'center',
              }}
            >
              {isSubmitting ? (
                <>
                  <Loader2
                    size={16}
                    className="spin-icon"
                    style={{ animation: 'spin 1s linear infinite' }}
                  />
                  <span>Processing NLP...</span>
                </>
              ) : (
                <>
                  <Send size={16} />
                  <span>Submit Feedback</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
