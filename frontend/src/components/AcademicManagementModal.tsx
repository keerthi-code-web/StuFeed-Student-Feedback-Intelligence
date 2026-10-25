
import React, { useEffect, useState } from 'react';
import {
  X,
  Edit2,
  Trash2,
  Building2,
  BookOpen,
  Users,
  Check,
  AlertCircle,
} from 'lucide-react';

import { Department, Subject, Instructor } from '../types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onDataChanged: () => void;
  initialTab?: 'departments' | 'subjects' | 'instructors';
}

type Tab = 'departments' | 'subjects' | 'instructors';

const semesters = Array.from({ length: 8 }, (_, index) => index + 1);

async function readResponse(response: Response) {
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

export const AcademicManagementModal: React.FC<Props> = ({
  isOpen,
  onClose,
  onDataChanged,
  initialTab = 'departments',
}) => {
  const [activeTab, setActiveTab] = useState<Tab>(initialTab);

  const [departments, setDepartments] = useState<Department[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [instructors, setInstructors] = useState<Instructor[]>([]);

  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [deptName, setDeptName] = useState('');
  const [deptCode, setDeptCode] = useState('');
  const [editingDeptId, setEditingDeptId] = useState<number | null>(null);

  const [subjName, setSubjName] = useState('');
  const [subjCode, setSubjCode] = useState('');
  const [subjDeptId, setSubjDeptId] = useState<number>(0);
  const [subjSemester, setSubjSemester] = useState<number>(1);
  const [subjInstIds, setSubjInstIds] = useState<number[]>([]);
  const [editingSubjId, setEditingSubjId] = useState<number | null>(null);

  const [instName, setInstName] = useState('');
  const [instDeptId, setInstDeptId] = useState<number>(0);
  const [instSubjIds, setInstSubjIds] = useState<number[]>([]);
  const [editingInstId, setEditingInstId] = useState<number | null>(null);

  const loadAll = async () => {
    try {
      const [departmentResponse, subjectResponse, instructorResponse] =
        await Promise.all([
          fetch('/api/departments'),
          fetch('/api/subjects?include_inactive=true'),
          fetch('/api/instructors?include_inactive=true'),
        ]);

      const [departmentData, subjectData, instructorData] =
        await Promise.all([
          readResponse(departmentResponse),
          readResponse(subjectResponse),
          readResponse(instructorResponse),
        ]);

      setDepartments(departmentData);
      setSubjects(subjectData);
      setInstructors(instructorData);

      if (departmentData.length > 0) {
        const firstDepartmentId = departmentData[0].id;

        setSubjDeptId((current) => current || firstDepartmentId);
        setInstDeptId((current) => current || firstDepartmentId);
      }
    } catch (error) {
      setErrorMsg(
        error instanceof Error
          ? error.message
          : 'Could not load academic information.'
      );
    }
  };

  useEffect(() => {
    if (isOpen) {
      setActiveTab(initialTab);
      setSuccessMsg(null);
      setErrorMsg(null);
      void loadAll();
    }
  }, [isOpen, initialTab]);

  const resetDepartmentForm = () => {
    setDeptName('');
    setDeptCode('');
    setEditingDeptId(null);
  };

  const resetSubjectForm = () => {
    setSubjName('');
    setSubjCode('');
    setSubjSemester(1);
    setSubjInstIds([]);
    setEditingSubjId(null);
  };

  const resetInstructorForm = () => {
    setInstName('');
    setInstSubjIds([]);
    setEditingInstId(null);
  };

  const finishSave = async (message: string) => {
    setSuccessMsg(message);
    setErrorMsg(null);
    await loadAll();
    onDataChanged();
  };

  const runAction = async (action: () => Promise<void>) => {
    setBusy(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      await action();
    } catch (error) {
      setErrorMsg(
        error instanceof Error ? error.message : 'The action failed.'
      );
    } finally {
      setBusy(false);
    }
  };

  const saveDepartment = async (event: React.FormEvent) => {
    event.preventDefault();
    const name = deptName.trim();

    if (!name) {
      setErrorMsg('Department name is required.');
      return;
    }

    await runAction(async () => {
      const editing = editingDeptId !== null;
      const response = await fetch(
        editing ? `/api/departments/${editingDeptId}` : '/api/departments',
        {
          method: editing ? 'PUT' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name,
            code: deptCode.trim() || null,
          }),
        }
      );
      const data = await readResponse(response);
      resetDepartmentForm();
      await finishSave(
        `Department "${data.name || name}" ${editing ? 'updated' : 'added'}.`
      );
    });
  };

  const deactivateDepartment = async (
    id: number,
    name: string
  ) => {
    if (
      !window.confirm(
        `Deactivate department "${name}"? Historical feedback should be preserved.`
      )
    ) return;

    await runAction(async () => {
      const response = await fetch(`/api/departments/${id}`, {
        method: 'DELETE',
      });
      const data = await readResponse(response);
      await finishSave(data.message || `Department "${name}" deactivated.`);
    });
  };

  const saveSubject = async (event: React.FormEvent) => {
    event.preventDefault();

    const name = subjName.trim();

    if (!name) {
      setErrorMsg('Subject name is required.');
      return;
    }

    if (!subjDeptId) {
      setErrorMsg('Select a department for the subject.');
      return;
    }

    if (subjSemester < 1 || subjSemester > 8) {
      setErrorMsg('Select a semester between 1 and 8.');
      return;
    }

    await runAction(async () => {
      const editing = editingSubjId !== null;
      const response = await fetch(
        editing ? `/api/subjects/${editingSubjId}` : '/api/subjects',
        {
          method: editing ? 'PUT' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name,
            code: subjCode.trim() || null,
            department_id: subjDeptId,
            semester: subjSemester,
            instructor_ids: subjInstIds,
          }),
        }
      );

      const data = await readResponse(response);
      resetSubjectForm();
      await finishSave(
        `Subject "${data.name || name}" ${editing ? 'updated' : 'added'} for Semester ${data.semester ?? subjSemester}.`
      );
    });
  };

  const deactivateSubject = async (id: number, name: string) => {
    if (
      !window.confirm(
        `Deactivate subject "${name}"? Historical feedback will be preserved.`
      )
    ) return;

    await runAction(async () => {
      const response = await fetch(`/api/subjects/${id}`, {
        method: 'DELETE',
      });
      const data = await readResponse(response);
      await finishSave(data.message || `Subject "${name}" deactivated.`);
    });
  };

  const saveInstructor = async (event: React.FormEvent) => {
    event.preventDefault();
    const name = instName.trim();

    if (!name) {
      setErrorMsg('Instructor name is required.');
      return;
    }

    if (!instDeptId) {
      setErrorMsg('Select a department for the instructor.');
      return;
    }

    await runAction(async () => {
      const editing = editingInstId !== null;
      const response = await fetch(
        editing
          ? `/api/instructors/${editingInstId}`
          : '/api/instructors',
        {
          method: editing ? 'PUT' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name,
            department_id: instDeptId,
            subject_ids: instSubjIds,
          }),
        }
      );

      const data = await readResponse(response);
      resetInstructorForm();
      await finishSave(
        `Instructor "${data.name || name}" ${editing ? 'updated' : 'added'}.`
      );
    });
  };

  const deactivateInstructor = async (
    id: number,
    name: string
  ) => {
    if (
      !window.confirm(
        `Deactivate instructor "${name}"? Historical feedback will be preserved.`
      )
    ) return;

    await runAction(async () => {
      const response = await fetch(`/api/instructors/${id}`, {
        method: 'DELETE',
      });
      const data = await readResponse(response);
      await finishSave(data.message || `Instructor "${name}" deactivated.`);
    });
  };

  const activeDepartments = departments.filter((item) => item.is_active);
  const activeSubjects = subjects.filter((item) => item.is_active);
  const activeInstructors = instructors.filter((item) => item.is_active);

  const availableInstructorsForSubject = activeInstructors.filter(
    (item) => item.department_id === subjDeptId
  );

  const availableSubjectsForInstructor = activeSubjects.filter(
    (item) => item.department_id === instDeptId
  );

  if (!isOpen) return null;

  const tabButtonStyle = (selected: boolean): React.CSSProperties => ({
    padding: '0.75rem 1rem',
    fontWeight: 700,
    fontSize: '0.88rem',
    borderBottom: selected
      ? '3px solid var(--primary-yellow)'
      : '3px solid transparent',
    color: selected ? 'var(--text-primary)' : 'var(--text-secondary)',
    display: 'flex',
    alignItems: 'center',
    gap: '0.4rem',
  });

  const actionButtonStyle = (
    background: string,
    color: string
  ): React.CSSProperties => ({
    padding: '0.3rem 0.6rem',
    fontSize: '0.75rem',
    background,
    borderRadius: '4px',
    color,
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.25rem',
  });

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0,0,0,0.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '1.5rem',
      }}
    >
      <div
        style={{
          background: '#FFFFFF',
          borderRadius: '12px',
          maxWidth: '1000px',
          width: '100%',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: 'var(--shadow-lg)',
          border: '1px solid var(--border-light)',
        }}
      >
        <div
          style={{
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid var(--border-light)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700 }}>
              Academic Structure Management
            </h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Manage departments, semesters, subjects, and instructors.
            </p>
          </div>

          <button onClick={onClose} aria-label="Close management modal">
            <X size={20} />
          </button>
        </div>

        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            borderBottom: '1px solid var(--border-light)',
            padding: '0 1.5rem',
            background: '#FAF9F5',
          }}
        >
          <button
            onClick={() => setActiveTab('departments')}
            style={tabButtonStyle(activeTab === 'departments')}
          >
            <Building2 size={16} />
            Departments ({departments.length})
          </button>

          <button
            onClick={() => setActiveTab('subjects')}
            style={tabButtonStyle(activeTab === 'subjects')}
          >
            <BookOpen size={16} />
            Subjects ({subjects.length})
          </button>

          <button
            onClick={() => setActiveTab('instructors')}
            style={tabButtonStyle(activeTab === 'instructors')}
          >
            <Users size={16} />
            Instructors ({instructors.length})
          </button>
        </div>

        <div style={{ padding: '1.5rem', overflowY: 'auto', flex: 1 }}>
          {successMsg && (
            <div
              style={{
                background: '#F0FDF4',
                border: '1px solid #BBF7D0',
                padding: '0.75rem 1rem',
                borderRadius: '6px',
                color: '#15803D',
                marginBottom: '1.25rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              <Check size={16} />
              {successMsg}
            </div>
          )}

          {errorMsg && (
            <div
              style={{
                background: '#FEF2F2',
                border: '1px solid #FECACA',
                padding: '0.75rem 1rem',
                borderRadius: '6px',
                color: '#B91C1C',
                marginBottom: '1.25rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              <AlertCircle size={16} />
              {errorMsg}
            </div>
          )}

          {busy && (
            <p style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }}>
              Saving changes…
            </p>
          )}

          {activeTab === 'departments' && (
            <section>
              <div className="filter-card" style={{ marginBottom: '1.5rem' }}>
                <h4 style={{ marginBottom: '0.75rem', fontWeight: 700 }}>
                  {editingDeptId ? 'Edit Department' : 'Add Department'}
                </h4>

                <form
                  onSubmit={saveDepartment}
                  style={{
                    display: 'flex',
                    gap: '0.75rem',
                    flexWrap: 'wrap',
                    alignItems: 'flex-end',
                  }}
                >
                  <div style={{ flex: 2, minWidth: '220px' }}>
                    <label className="form-label">Department Name *</label>
                    <input
                      className="form-input"
                      value={deptName}
                      onChange={(event) => setDeptName(event.target.value)}
                      placeholder="e.g. Mechanical Engineering"
                      required
                    />
                  </div>

                  <div style={{ flex: 1, minWidth: '120px' }}>
                    <label className="form-label">Department Code</label>
                    <input
                      className="form-input"
                      value={deptCode}
                      onChange={(event) => setDeptCode(event.target.value)}
                      placeholder="e.g. MECH"
                    />
                  </div>

                  <button className="btn-primary" type="submit" disabled={busy}>
                    {editingDeptId ? 'Save Changes' : 'Add Department'}
                  </button>

                  {editingDeptId !== null && (
                    <button
                      className="btn-secondary"
                      type="button"
                      onClick={resetDepartmentForm}
                    >
                      Cancel
                    </button>
                  )}
                </form>
              </div>

              <div className="table-container">
                <table className="styled-table">
                  <thead>
                    <tr>
                      <th>Department</th>
                      <th>Code</th>
                      <th>Subjects</th>
                      <th>Feedback</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {departments.map((department) => (
                      <tr key={department.id}>
                        <td>{department.name}</td>
                        <td>{department.code || '—'}</td>
                        <td>{department.subject_count ?? 0}</td>
                        <td>{department.feedback_count ?? 0}</td>
                        <td>
                          <div style={{ display: 'flex', gap: '0.4rem' }}>
                            <button
                              style={actionButtonStyle('#FEF9C3', '#854D0E')}
                              onClick={() => {
                                setEditingDeptId(department.id);
                                setDeptName(department.name);
                                setDeptCode(department.code || '');
                                setErrorMsg(null);
                              }}
                            >
                              <Edit2 size={12} /> Edit
                            </button>
                            <button
                              style={actionButtonStyle('#FEE2E2', '#B91C1C')}
                              onClick={() =>
                                void deactivateDepartment(
                                  department.id,
                                  department.name
                                )
                              }
                            >
                              <Trash2 size={12} /> Deactivate
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {departments.length === 0 && (
                      <tr>
                        <td colSpan={5}>No departments found.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {activeTab === 'subjects' && (
            <section>
              <div className="filter-card" style={{ marginBottom: '1.5rem' }}>
                <h4 style={{ marginBottom: '0.75rem', fontWeight: 700 }}>
                  {editingSubjId ? 'Edit Subject' : 'Add Subject'}
                </h4>

                <form
                  onSubmit={saveSubject}
                  style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}
                >
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
                      gap: '0.75rem',
                    }}
                  >
                    <div>
                      <label className="form-label">Department *</label>
                      <select
                        className="form-select"
                        value={subjDeptId || ''}
                        onChange={(event) => {
                          setSubjDeptId(Number(event.target.value));
                          setSubjInstIds([]);
                        }}
                        required
                      >
                        <option value="">Select department</option>
                        {activeDepartments.map((department) => (
                          <option key={department.id} value={department.id}>
                            {department.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="form-label">Semester *</label>
                      <select
                        className="form-select"
                        value={subjSemester}
                        onChange={(event) =>
                          setSubjSemester(Number(event.target.value))
                        }
                        required
                      >
                        {semesters.map((semester) => (
                          <option key={semester} value={semester}>
                            Semester {semester}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="form-label">Subject Name *</label>
                      <input
                        className="form-input"
                        value={subjName}
                        onChange={(event) => setSubjName(event.target.value)}
                        placeholder="e.g. Data Structures"
                        required
                      />
                    </div>

                    <div>
                      <label className="form-label">Subject Code</label>
                      <input
                        className="form-input"
                        value={subjCode}
                        onChange={(event) => setSubjCode(event.target.value)}
                        placeholder="e.g. CS3501"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="form-label">
                      Assign Instructors (multiple selection)
                    </label>
                    <div
                      style={{
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: '0.5rem',
                        maxHeight: '130px',
                        overflowY: 'auto',
                        padding: '0.6rem',
                        background: '#FFFFFF',
                        border: '1px solid var(--border-light)',
                        borderRadius: '6px',
                      }}
                    >
                      {availableInstructorsForSubject.length === 0 ? (
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                          No active instructors in this department yet.
                        </span>
                      ) : (
                        availableInstructorsForSubject.map((instructor) => {
                          const assigned = subjInstIds.includes(instructor.id);

                          return (
                            <button
                              key={instructor.id}
                              type="button"
                              onClick={() =>
                                setSubjInstIds((current) =>
                                  assigned
                                    ? current.filter((id) => id !== instructor.id)
                                    : [...current, instructor.id]
                                )
                              }
                              style={{
                                padding: '0.3rem 0.6rem',
                                borderRadius: '4px',
                                border: '1px solid var(--border-light)',
                                background: assigned ? 'var(--bg-yellow-light)' : '#FFFFFF',
                                color: assigned ? '#854D0E' : 'var(--text-primary)',
                                fontWeight: assigned ? 700 : 500,
                              }}
                            >
                              {assigned ? '✓ ' : '+ '}
                              {instructor.name}
                            </button>
                          );
                        })
                      )}
                    </div>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                    {editingSubjId !== null && (
                      <button
                        className="btn-secondary"
                        type="button"
                        onClick={resetSubjectForm}
                      >
                        Cancel
                      </button>
                    )}
                    <button className="btn-primary" type="submit" disabled={busy}>
                      {editingSubjId !== null ? 'Save Changes' : 'Add Subject'}
                    </button>
                  </div>
                </form>
              </div>

              <div className="table-container">
                <table className="styled-table">
                  <thead>
                    <tr>
                      <th>Subject</th>
                      <th>Code</th>
                      <th>Department</th>
                      <th>Semester</th>
                      <th>Assigned Instructors</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {subjects.map((subject) => (
                      <tr key={subject.id}>
                        <td>{subject.name}</td>
                        <td>{subject.code || '—'}</td>
                        <td>{subject.department_name || '—'}</td>
                        <td>Semester {subject.semester}</td>
                        <td>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                            {subject.instructors?.length
                              ? subject.instructors.map((instructor) => (
                                  <span className="tag-pill" key={instructor.id}>
                                    {instructor.name}
                                  </span>
                                ))
                              : <span style={{ color: 'var(--text-muted)' }}>None</span>}
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: '0.4rem' }}>
                            <button
                              style={actionButtonStyle('#FEF9C3', '#854D0E')}
                              onClick={() => {
                                setEditingSubjId(subject.id);
                                setSubjName(subject.name);
                                setSubjCode(subject.code || '');
                                setSubjDeptId(subject.department_id);
                                setSubjSemester(subject.semester || 1);
                                setSubjInstIds(
                                  subject.instructors?.map((item) => item.id) || []
                                );
                                setErrorMsg(null);
                              }}
                            >
                              <Edit2 size={12} /> Edit
                            </button>
                            <button
                              style={actionButtonStyle('#FEE2E2', '#B91C1C')}
                              onClick={() =>
                                void deactivateSubject(subject.id, subject.name)
                              }
                            >
                              <Trash2 size={12} /> Deactivate
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {subjects.length === 0 && (
                      <tr>
                        <td colSpan={6}>No subjects found.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {activeTab === 'instructors' && (
            <section>
              <div className="filter-card" style={{ marginBottom: '1.5rem' }}>
                <h4 style={{ marginBottom: '0.75rem', fontWeight: 700 }}>
                  {editingInstId ? 'Edit Instructor' : 'Add Instructor'}
                </h4>

                <form
                  onSubmit={saveInstructor}
                  style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}
                >
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                      gap: '0.75rem',
                    }}
                  >
                    <div>
                      <label className="form-label">Instructor Name *</label>
                      <input
                        className="form-input"
                        value={instName}
                        onChange={(event) => setInstName(event.target.value)}
                        placeholder="e.g. Dr. Robert Vance"
                        required
                      />
                    </div>

                    <div>
                      <label className="form-label">Department *</label>
                      <select
                        className="form-select"
                        value={instDeptId || ''}
                        onChange={(event) => {
                          setInstDeptId(Number(event.target.value));
                          setInstSubjIds([]);
                        }}
                        required
                      >
                        <option value="">Select department</option>
                        {activeDepartments.map((department) => (
                          <option key={department.id} value={department.id}>
                            {department.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="form-label">
                      Assign to Subjects (multiple selection)
                    </label>
                    <div
                      style={{
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: '0.5rem',
                        maxHeight: '130px',
                        overflowY: 'auto',
                        padding: '0.6rem',
                        background: '#FFFFFF',
                        border: '1px solid var(--border-light)',
                        borderRadius: '6px',
                      }}
                    >
                      {availableSubjectsForInstructor.length === 0 ? (
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                          No active subjects in this department yet.
                        </span>
                      ) : (
                        availableSubjectsForInstructor.map((subject) => {
                          const assigned = instSubjIds.includes(subject.id);

                          return (
                            <button
                              key={subject.id}
                              type="button"
                              onClick={() =>
                                setInstSubjIds((current) =>
                                  assigned
                                    ? current.filter((id) => id !== subject.id)
                                    : [...current, subject.id]
                                )
                              }
                              style={{
                                padding: '0.3rem 0.6rem',
                                borderRadius: '4px',
                                border: '1px solid var(--border-light)',
                                background: assigned ? 'var(--bg-yellow-light)' : '#FFFFFF',
                                color: assigned ? '#854D0E' : 'var(--text-primary)',
                                fontWeight: assigned ? 700 : 500,
                              }}
                            >
                              {assigned ? '✓ ' : '+ '}
                              {subject.name} — Sem {subject.semester}
                            </button>
                          );
                        })
                      )}
                    </div>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                    {editingInstId !== null && (
                      <button
                        className="btn-secondary"
                        type="button"
                        onClick={resetInstructorForm}
                      >
                        Cancel
                      </button>
                    )}
                    <button className="btn-primary" type="submit" disabled={busy}>
                      {editingInstId !== null ? 'Save Changes' : 'Add Instructor'}
                    </button>
                  </div>
                </form>
              </div>

              <div className="table-container">
                <table className="styled-table">
                  <thead>
                    <tr>
                      <th>Instructor</th>
                      <th>Department</th>
                      <th>Assigned Subjects</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {instructors.map((instructor) => (
                      <tr key={instructor.id}>
                        <td>{instructor.name}</td>
                        <td>{instructor.department_name || instructor.department || '—'}</td>
                        <td>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                            {instructor.subjects?.length
                              ? instructor.subjects.map((subject) => (
                                  <span className="tag-pill" key={subject.id}>
                                    {subject.name} (Sem {subject.semester})
                                  </span>
                                ))
                              : <span style={{ color: 'var(--text-muted)' }}>None</span>}
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: '0.4rem' }}>
                            <button
                              style={actionButtonStyle('#FEF9C3', '#854D0E')}
                              onClick={() => {
                                setEditingInstId(instructor.id);
                                setInstName(instructor.name);
                                setInstDeptId(
                                  instructor.department_id ||
                                  activeDepartments[0]?.id ||
                                  0
                                );
                                setInstSubjIds(
                                  instructor.subjects?.map((item) => item.id) || []
                                );
                                setErrorMsg(null);
                              }}
                            >
                              <Edit2 size={12} /> Edit
                            </button>
                            <button
                              style={actionButtonStyle('#FEE2E2', '#B91C1C')}
                              onClick={() =>
                                void deactivateInstructor(
                                  instructor.id,
                                  instructor.name
                                )
                              }
                            >
                              <Trash2 size={12} /> Deactivate
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {instructors.length === 0 && (
                      <tr>
                        <td colSpan={4}>No instructors found.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
};
