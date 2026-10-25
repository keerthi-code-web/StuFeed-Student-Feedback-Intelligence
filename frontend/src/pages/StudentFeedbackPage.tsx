import React, { useState, useEffect } from 'react';
import { Send, CheckCircle2, AlertCircle, Star, Loader2 } from 'lucide-react';
import { Department, Subject, Instructor, FeedbackSubmission } from '../types';
import { SentimentBadge } from '../components/SentimentBadge';

export const StudentFeedbackPage: React.FC = () => {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [instructors, setInstructors] = useState<Instructor[]>([]);

  // Form State
  const [registerNumber, setRegisterNumber] = useState('');
  const [studentName, setStudentName] = useState('');
  const [selectedDepartment, setSelectedDepartment] = useState('');
  const [selectedSubject, setSelectedSubject] = useState('');
  const [selectedInstructor, setSelectedInstructor] = useState('');
  const [rating, setRating] = useState<number>(5);
  const [feedbackText, setFeedbackText] = useState('');

  // UI state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successResult, setSuccessResult] = useState<FeedbackSubmission | null>(null);

  // 1. Load departments initially
  useEffect(() => {
    fetch('/api/departments')
      .then((res) => res.json())
      .then((data: Department[]) => {
        const activeDepts = data.filter((d) => d.is_active);
        setDepartments(activeDepts);
        if (activeDepts.length > 0) {
          setSelectedDepartment(activeDepts[0].name);
        }
      })
      .catch((err) => console.error('Failed to load departments', err));
  }, []);

  // 2. Load subjects dynamically when department changes
  useEffect(() => {
    if (!selectedDepartment || selectedDepartment === 'Other') {
      setSubjects([]);
      setSelectedSubject('');
      setInstructors([]);
      setSelectedInstructor('');
      return;
    }

    fetch(`/api/subjects?department_name=${encodeURIComponent(selectedDepartment)}`)
      .then((res) => res.json())
      .then((data: Subject[]) => {
        setSubjects(data);
        if (data.length > 0) {
          setSelectedSubject(data[0].name);
        } else {
          setSelectedSubject('');
        }
      })
      .catch((err) => console.error('Failed to load subjects for department', err));
  }, [selectedDepartment]);

  // 3. Load instructors dynamically when subject changes
  useEffect(() => {
    if (!selectedDepartment || selectedDepartment === 'Other' || !selectedSubject) {
      setInstructors([]);
      setSelectedInstructor('');
      return;
    }

    // Find current subject id to get assigned instructors
    const subObj = subjects.find((s) => s.name === selectedSubject);
    const subParam = subObj ? `&subject_id=${subObj.id}` : `&subject_name=${encodeURIComponent(selectedSubject)}`;

    fetch(`/api/instructors?department_name=${encodeURIComponent(selectedDepartment)}${subParam}`)
      .then((res) => res.json())
      .then((data: Instructor[]) => {
        setInstructors(data);
        if (data.length > 0) {
          setSelectedInstructor(data[0].name);
        } else {
          setSelectedInstructor('');
        }
      })
      .catch((err) => console.error('Failed to load instructors for subject', err));
  }, [selectedDepartment, selectedSubject, subjects]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessResult(null);

    const finalReg = registerNumber.trim();
    const finalName = studentName.trim();
    const finalDept = selectedDepartment.trim();
    const finalText = feedbackText.trim();
    const isOther = finalDept === 'Other';

    // Validation checks
    if (!finalReg) {
      setErrorMessage('Student Register Number is required.');
      return;
    }
    if (!finalName) {
      setErrorMessage('Student Full Name is required.');
      return;
    }
    if (!finalDept) {
      setErrorMessage('Please select a Department or category.');
      return;
    }

    if (!isOther) {
      if (!selectedSubject || !selectedSubject.trim()) {
        setErrorMessage(`Please select a Subject for department '${finalDept}'.`);
        return;
      }
      if (!selectedInstructor || !selectedInstructor.trim()) {
        setErrorMessage(`Please select an Instructor for subject '${selectedSubject}'.`);
        return;
      }
    }

    if (!rating || rating < 1 || rating > 5) {
      setErrorMessage('Rating must be an integer between 1 and 5.');
      return;
    }
    if (!finalText || finalText.length < 5) {
      setErrorMessage('Written Feedback is required and must be at least 5 characters.');
      return;
    }

    setIsSubmitting(true);

    try {
      const payload: any = {
        register_number: finalReg,
        student_name: finalName,
        department_name: finalDept,
        rating: rating,
        feedback_text: finalText,
      };

      if (!isOther) {
        payload.subject_name = selectedSubject.trim();
        payload.instructor_name = selectedInstructor.trim();
      }

      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Submission failed. Please check your inputs.');
      }

      setSuccessResult(data);
      setFeedbackText('');
    } catch (err: any) {
      setErrorMessage(err.message || 'An unexpected network error occurred.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const isOther = selectedDepartment === 'Other';

  return (
    <div style={{ maxWidth: '780px', margin: '0 auto' }}>
      <div className="form-card">
        <div className="form-header">
          <h2>Submit Academic Course Feedback</h2>
          <p>
            Share your experience to help improve curriculum quality, laboratory resources, and instructional pacing.
          </p>
        </div>

        {/* Success Confirmation Banner */}
        {successResult && (
          <div className="confirmation-banner">
            <h4>
              <CheckCircle2 size={20} />
              Feedback Submitted & Analyzed Successfully!
            </h4>
            <p>
              Your feedback for{' '}
              <strong>
                {successResult.is_other ? 'General Institutional Feedback (Other)' : `${successResult.subject_name} (${successResult.instructor_name})`}
              </strong>{' '}
              under {successResult.department_name} has been verified and classified by the NLP intelligence engine.
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginTop: '0.4rem' }}>
              <span style={{ fontSize: '0.82rem', color: '#166534', fontWeight: 600 }}>
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

        {/* Error Banner */}
        {errorMessage && (
          <div style={{
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
          }}>
            <AlertCircle size={18} />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            {/* Step 1: Student Identity */}
            <div className="form-group">
              <label className="form-label">
                Student Register Number <span className="required-star">*</span>
              </label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. 922524243088"
                value={registerNumber}
                onChange={(e) => setRegisterNumber(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">
                Student Full Name <span className="required-star">*</span>
              </label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. Alex Morgan"
                value={studentName}
                onChange={(e) => setStudentName(e.target.value)}
                required
              />
            </div>

            {/* Step 2: Department Selection */}
            <div className="form-group full-width">
              <label className="form-label">
                Department / Feedback Category <span className="required-star">*</span>
              </label>
              <select
                className="form-select"
                value={selectedDepartment}
                onChange={(e) => setSelectedDepartment(e.target.value)}
                required
              >
                {departments.map((dept) => (
                  <option key={dept.id} value={dept.name}>
                    {dept.name} {dept.code ? `(${dept.code})` : ''}
                  </option>
                ))}
                <option value="Other">Other (General Institutional Feedback)</option>
              </select>
            </div>

            {/* Step 3: Conditional Fields (Hidden if Other) */}
            {!isOther && (
              <>
                <div className="form-group">
                  <label className="form-label">
                    Subject Name <span className="required-star">*</span>
                  </label>
                  <select
                    className="form-select"
                    value={selectedSubject}
                    onChange={(e) => setSelectedSubject(e.target.value)}
                    required
                  >
                    {subjects.length === 0 ? (
                      <option value="">No active subjects configured for this department</option>
                    ) : (
                      subjects.map((sub) => (
                        <option key={sub.id} value={sub.name}>
                          {sub.name} {sub.code ? `(${sub.code})` : ''}
                        </option>
                      ))
                    )}
                  </select>
                  {subjects.length === 0 && (
                    <span style={{ fontSize: '0.75rem', color: '#B45309', marginTop: '0.25rem' }}>
                      Subjects must be configured by administrator in the Admin Dashboard.
                    </span>
                  )}
                </div>

                <div className="form-group">
                  <label className="form-label">
                    Assigned Instructor <span className="required-star">*</span>
                  </label>
                  <select
                    className="form-select"
                    value={selectedInstructor}
                    onChange={(e) => setSelectedInstructor(e.target.value)}
                    required
                    disabled={instructors.length === 0}
                  >
                    {instructors.length === 0 ? (
                      <option value="">No assigned instructors for this subject</option>
                    ) : (
                      instructors.map((inst) => (
                        <option key={inst.id} value={inst.name}>
                          {inst.name}
                        </option>
                      ))
                    )}
                  </select>
                  {instructors.length === 0 && (
                    <span style={{ fontSize: '0.75rem', color: '#B45309', marginTop: '0.25rem' }}>
                      Instructors must be assigned to this subject by administrator.
                    </span>
                  )}
                </div>
              </>
            )}

            {/* Step 4: Rating (1 to 5) */}
            <div className="form-group full-width">
              <label className="form-label">
                Course & Experience Rating <span className="required-star">*</span>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                  Selected: {rating} out of 5 stars
                </span>
              </label>
              <div className="rating-selector">
                {[1, 2, 3, 4, 5].map((val) => (
                  <button
                    key={val}
                    type="button"
                    className={`rating-btn ${rating === val ? 'selected' : ''}`}
                    onClick={() => setRating(val)}
                  >
                    <Star
                      size={15}
                      fill={rating >= val ? '#EAB308' : 'none'}
                      color={rating >= val ? '#CA8A04' : '#9CA3AF'}
                    />
                    <span>{val}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Step 5: Written Feedback */}
            <div className="form-group full-width">
              <div className="form-label">
                <span>Written Feedback <span className="required-star">*</span></span>
                <span className="char-counter">{feedbackText.length} characters</span>
              </div>
              <textarea
                className="form-textarea"
                placeholder={
                  isOther
                    ? 'Provide general institutional feedback regarding campus facilities, library, administrative processes, or student services...'
                    : 'Describe your learning experience, instructional clarity, laboratory hardware, course pace, or evaluation criteria...'
                }
                value={feedbackText}
                onChange={(e) => setFeedbackText(e.target.value)}
                required
              />
            </div>
          </div>

          <div style={{ marginTop: '1.25rem', display: 'flex', justifyContent: 'flex-end' }}>
            <button
              type="submit"
              className="btn-primary"
              disabled={isSubmitting || (!isOther && (subjects.length === 0 || instructors.length === 0))}
              style={{
                opacity: isSubmitting || (!isOther && (subjects.length === 0 || instructors.length === 0)) ? 0.7 : 1,
                minWidth: '180px',
                justifyContent: 'center'
              }}
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={16} className="spin-icon" style={{ animation: 'spin 1s linear infinite' }} />
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
