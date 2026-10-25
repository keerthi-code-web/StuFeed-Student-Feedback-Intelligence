import React, { useState, useEffect } from 'react';
import { X, Plus, Edit2, Trash2, Building2, BookOpen, Users, Check, AlertCircle } from 'lucide-react';
import { Department, Subject, Instructor } from '../types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onDataChanged: () => void;
  initialTab?: 'departments' | 'subjects' | 'instructors';
}

export const AcademicManagementModal: React.FC<Props> = ({
  isOpen,
  onClose,
  onDataChanged,
  initialTab = 'departments',
}) => {
  const [activeTab, setActiveTab] = useState<'departments' | 'subjects' | 'instructors'>(initialTab);
  
  // Data
  const [departments, setDepartments] = useState<Department[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [instructors, setInstructors] = useState<Instructor[]>([]);

  // Messages
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Department Form
  const [deptName, setDeptName] = useState('');
  const [deptCode, setDeptCode] = useState('');
  const [editingDeptId, setEditingDeptId] = useState<number | null>(null);

  // Subject Form
  const [subjName, setSubjName] = useState('');
  const [subjCode, setSubjCode] = useState('');
  const [subjDeptId, setSubjDeptId] = useState<number>(0);
  const [subjInstIds, setSubjInstIds] = useState<number[]>([]);
  const [editingSubjId, setEditingSubjId] = useState<number | null>(null);

  // Instructor Form
  const [instName, setInstName] = useState('');
  const [instDeptId, setInstDeptId] = useState<number>(0);
  const [instSubjIds, setInstSubjIds] = useState<number[]>([]);
  const [editingInstId, setEditingInstId] = useState<number | null>(null);

  const loadAll = async () => {
    try {
      const [deptRes, subjRes, instRes] = await Promise.all([
        fetch('/api/departments'),
        fetch('/api/subjects'),
        fetch('/api/instructors'),
      ]);
      const [deptData, subjData, instData] = await Promise.all([
        deptRes.json(),
        subjRes.json(),
        instRes.json(),
      ]);

      setDepartments(deptData);
      setSubjects(subjData);
      setInstructors(instData);

      if (deptData.length > 0 && !subjDeptId) {
        setSubjDeptId(deptData[0].id);
        setInstDeptId(deptData[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadAll();
      setSuccessMsg(null);
      setErrorMsg(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  // --- Department handlers ---
  const handleSaveDepartment = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMsg(null);
    setErrorMsg(null);

    const name = deptName.trim();
    if (!name) {
      setErrorMsg('Department name is required.');
      return;
    }

    try {
      if (editingDeptId) {
        const res = await fetch(`/api/departments/${editingDeptId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, code: deptCode.trim() || undefined }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to update department.');
        setSuccessMsg(`Department "${data.name}" updated successfully.`);
      } else {
        const res = await fetch('/api/departments', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, code: deptCode.trim() || undefined }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to create department.');
        setSuccessMsg(`Department "${data.name}" added successfully.`);
      }

      setDeptName('');
      setDeptCode('');
      setEditingDeptId(null);
      await loadAll();
      onDataChanged();
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const handleDeactivateDept = async (id: number, name: string) => {
    if (!window.confirm(`Are you sure you want to delete department "${name}"? Historical feedback will be preserved.`)) {
      return;
    }
    setSuccessMsg(null);
    setErrorMsg(null);
    try {
      const res = await fetch(`/api/departments/${id}`, { method: 'DELETE' });
      const data = await res.json();
      setSuccessMsg(data.message || `Department "${name}" deleted.`);
      await loadAll();
      onDataChanged();
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  // --- Subject handlers ---
  const handleSaveSubject = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMsg(null);
    setErrorMsg(null);

    const name = subjName.trim();
    if (!name) {
      setErrorMsg('Subject name is required.');
      return;
    }
    if (!subjDeptId) {
      setErrorMsg('Department is required for subject.');
      return;
    }

    try {
      if (editingSubjId) {
        const res = await fetch(`/api/subjects/${editingSubjId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name,
            code: subjCode.trim() || undefined,
            department_id: subjDeptId,
            instructor_ids: subjInstIds,
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to update subject.');
        setSuccessMsg(`Subject "${data.name}" updated.`);
      } else {
        const res = await fetch('/api/subjects', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name,
            code: subjCode.trim() || undefined,
            department_id: subjDeptId,
            instructor_ids: subjInstIds,
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to add subject.');
        setSuccessMsg(`Subject "${data.name}" added.`);
      }

      setSubjName('');
      setSubjCode('');
      setSubjInstIds([]);
      setEditingSubjId(null);
      await loadAll();
      onDataChanged();
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const handleDeactivateSubj = async (id: number, name: string) => {
    if (!window.confirm(`Are you sure you want to delete subject "${name}"? Historical feedback will be preserved.`)) {
      return;
    }
    try {
      const res = await fetch(`/api/subjects/${id}`, { method: 'DELETE' });
      const data = await res.json();
      setSuccessMsg(data.message || `Subject "${name}" deleted.`);
      await loadAll();
      onDataChanged();
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  // --- Instructor handlers ---
  const handleSaveInstructor = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMsg(null);
    setErrorMsg(null);

    const name = instName.trim();
    if (!name) {
      setErrorMsg('Instructor name is required.');
      return;
    }
    if (!instDeptId) {
      setErrorMsg('Department is required.');
      return;
    }

    try {
      if (editingInstId) {
        const res = await fetch(`/api/instructors/${editingInstId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name,
            department_id: instDeptId,
            subject_ids: instSubjIds,
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to update instructor.');
        setSuccessMsg(`Instructor "${data.name}" updated.`);
      } else {
        const res = await fetch('/api/instructors', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name,
            department_id: instDeptId,
            subject_ids: instSubjIds,
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to add instructor.');
        setSuccessMsg(`Instructor "${data.name}" added.`);
      }

      setInstName('');
      setInstSubjIds([]);
      setEditingInstId(null);
      await loadAll();
      onDataChanged();
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  const handleDeactivateInst = async (id: number, name: string) => {
    if (!window.confirm(`Are you sure you want to delete instructor "${name}"? Historical feedback will be preserved.`)) {
      return;
    }
    try {
      const res = await fetch(`/api/instructors/${id}`, { method: 'DELETE' });
      const data = await res.json();
      setSuccessMsg(data.message || `Instructor "${name}" deleted.`);
      await loadAll();
      onDataChanged();
    } catch (err: any) {
      setErrorMsg(err.message);
    }
  };

  // Filtered subjects for instructor selection (matching instructor's selected department)
  const availableSubjectsForInstructor = subjects.filter((s) => s.department_id === instDeptId);
  // Filtered instructors for subject selection (matching subject's selected department)
  const availableInstructorsForSubject = instructors.filter((i) => i.department_id === subjDeptId);

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.45)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '1.5rem',
    }}>
      <div style={{
        background: '#FFFFFF',
        borderRadius: '12px',
        maxWidth: '860px',
        width: '100%',
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: 'var(--shadow-lg)',
        border: '1px solid var(--border-light)',
      }}>
        {/* Modal Header */}
        <div style={{
          padding: '1.25rem 1.5rem',
          borderBottom: '1px solid var(--border-light)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Academic Structure Management</h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Configure Departments, Subjects, and Instructor assignments dynamically.
            </p>
          </div>
          <button onClick={onClose} style={{ color: 'var(--text-muted)', padding: '0.25rem' }}>
            <X size={20} />
          </button>
        </div>

        {/* Tabs */}
        <div style={{
          display: 'flex',
          borderBottom: '1px solid var(--border-light)',
          padding: '0 1.5rem',
          background: '#FAF9F5',
        }}>
          <button
            onClick={() => { setActiveTab('departments'); setSuccessMsg(null); setErrorMsg(null); }}
            style={{
              padding: '0.75rem 1.25rem',
              fontWeight: 700,
              fontSize: '0.88rem',
              borderBottom: activeTab === 'departments' ? '3px solid var(--primary-yellow)' : '3px solid transparent',
              color: activeTab === 'departments' ? 'var(--text-primary)' : 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
            }}
          >
            <Building2 size={16} />
            <span>Departments ({departments.length})</span>
          </button>

          <button
            onClick={() => { setActiveTab('subjects'); setSuccessMsg(null); setErrorMsg(null); }}
            style={{
              padding: '0.75rem 1.25rem',
              fontWeight: 700,
              fontSize: '0.88rem',
              borderBottom: activeTab === 'subjects' ? '3px solid var(--primary-yellow)' : '3px solid transparent',
              color: activeTab === 'subjects' ? 'var(--text-primary)' : 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
            }}
          >
            <BookOpen size={16} />
            <span>Subjects ({subjects.length})</span>
          </button>

          <button
            onClick={() => { setActiveTab('instructors'); setSuccessMsg(null); setErrorMsg(null); }}
            style={{
              padding: '0.75rem 1.25rem',
              fontWeight: 700,
              fontSize: '0.88rem',
              borderBottom: activeTab === 'instructors' ? '3px solid var(--primary-yellow)' : '3px solid transparent',
              color: activeTab === 'instructors' ? 'var(--text-primary)' : 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
            }}
          >
            <Users size={16} />
            <span>Instructors ({instructors.length})</span>
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: '1.5rem', overflowY: 'auto', flex: 1 }}>
          {successMsg && (
            <div style={{
              background: '#F0FDF4',
              border: '1px solid #BBF7D0',
              padding: '0.75rem 1rem',
              borderRadius: '6px',
              fontSize: '0.85rem',
              color: '#15803D',
              marginBottom: '1.25rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}>
              <Check size={16} />
              <span>{successMsg}</span>
            </div>
          )}

          {errorMsg && (
            <div style={{
              background: '#FEF2F2',
              border: '1px solid #FECACA',
              padding: '0.75rem 1rem',
              borderRadius: '6px',
              fontSize: '0.85rem',
              color: '#B91C1C',
              marginBottom: '1.25rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}>
              <AlertCircle size={16} />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* TAB 1: DEPARTMENTS */}
          {activeTab === 'departments' && (
            <div>
              <div style={{ background: '#FAF9F5', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-light)', marginBottom: '1.5rem' }}>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.75rem' }}>
                  {editingDeptId ? 'Edit Department' : 'Add New Department'}
                </h4>
                <form onSubmit={handleSaveDepartment} style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
                  <div style={{ flex: 2, minWidth: '220px' }}>
                    <label className="form-label" style={{ fontSize: '0.78rem' }}>Department Name *</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="e.g. Mechanical Engineering"
                      value={deptName}
                      onChange={(e) => setDeptName(e.target.value)}
                      required
                    />
                  </div>
                  <div style={{ flex: 1, minWidth: '100px' }}>
                    <label className="form-label" style={{ fontSize: '0.78rem' }}>Code (Optional)</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="e.g. MECH"
                      value={deptCode}
                      onChange={(e) => setDeptCode(e.target.value)}
                    />
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button type="submit" className="btn-primary" style={{ padding: '0.55rem 1rem' }}>
                      {editingDeptId ? 'Save Changes' : 'Add Department'}
                    </button>
                    {editingDeptId && (
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => { setEditingDeptId(null); setDeptName(''); setDeptCode(''); }}
                        style={{ padding: '0.55rem 0.8rem' }}
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </form>
              </div>

              <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.75rem' }}>Current Departments</h4>
              <div className="table-container">
                <table className="styled-table">
                  <thead>
                    <tr>
                      <th>Department Name</th>
                      <th>Code</th>
                      <th>Active Subjects</th>
                      <th>Feedback Count</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {departments.map((dept) => (
                      <tr key={dept.id}>
                        <td style={{ fontWeight: 600 }}>{dept.name}</td>
                        <td>{dept.code || '—'}</td>
                        <td>{dept.subject_count || 0}</td>
                        <td>{dept.feedback_count || 0}</td>
                        <td>
                          <div style={{ display: 'flex', gap: '0.4rem' }}>
                            <button
                              onClick={() => {
                                setEditingDeptId(dept.id);
                                setDeptName(dept.name);
                                setDeptCode(dept.code || '');
                              }}
                              style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem', background: '#FEF9C3', borderRadius: '4px', color: '#854D0E' }}
                            >
                              <Edit2 size={12} /> Edit
                            </button>
                            <button
                              onClick={() => handleDeactivateDept(dept.id, dept.name)}
                              style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem', background: '#FEE2E2', borderRadius: '4px', color: '#B91C1C' }}
                              title="Soft delete — historical feedback is preserved"
                            >
                              <Trash2 size={12} /> Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 2: SUBJECTS */}
          {activeTab === 'subjects' && (
            <div>
              <div style={{ background: '#FAF9F5', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-light)', marginBottom: '1.5rem' }}>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.75rem' }}>
                  {editingSubjId ? 'Edit Subject' : 'Add New Subject'}
                </h4>
                <form onSubmit={handleSaveSubject} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <div style={{ flex: 1, minWidth: '180px' }}>
                      <label className="form-label" style={{ fontSize: '0.78rem' }}>Department *</label>
                      <select
                        className="form-select"
                        value={subjDeptId}
                        onChange={(e) => {
                          setSubjDeptId(Number(e.target.value));
                          setSubjInstIds([]);
                        }}
                        required
                      >
                        {departments.filter(d => d.is_active).map((d) => (
                          <option key={d.id} value={d.id}>{d.name}</option>
                        ))}
                      </select>
                    </div>
                    <div style={{ flex: 2, minWidth: '200px' }}>
                      <label className="form-label" style={{ fontSize: '0.78rem' }}>Subject Name *</label>
                      <input
                        type="text"
                        className="form-input"
                        placeholder="e.g. Deep Learning Systems"
                        value={subjName}
                        onChange={(e) => setSubjName(e.target.value)}
                        required
                      />
                    </div>
                    <div style={{ flex: 1, minWidth: '100px' }}>
                      <label className="form-label" style={{ fontSize: '0.78rem' }}>Code (Optional)</label>
                      <input
                        type="text"
                        className="form-input"
                        placeholder="e.g. CS401"
                        value={subjCode}
                        onChange={(e) => setSubjCode(e.target.value)}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="form-label" style={{ fontSize: '0.78rem' }}>
                      Assign Instructors (Multiple Selection)
                    </label>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', maxHeight: '100px', overflowY: 'auto', padding: '0.5rem', background: '#FFFFFF', border: '1px solid var(--border-light)', borderRadius: '6px' }}>
                      {availableInstructorsForSubject.length === 0 ? (
                        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                          No instructors in this department yet. Add instructors in the Instructors tab.
                        </span>
                      ) : (
                        availableInstructorsForSubject.map((inst) => {
                          const isAssigned = subjInstIds.includes(inst.id);
                          return (
                            <button
                              key={inst.id}
                              type="button"
                              onClick={() => {
                                if (isAssigned) {
                                  setSubjInstIds(subjInstIds.filter((id) => id !== inst.id));
                                } else {
                                  setSubjInstIds([...subjInstIds, inst.id]);
                                }
                              }}
                              style={{
                                padding: '0.25rem 0.6rem',
                                borderRadius: '4px',
                                fontSize: '0.78rem',
                                border: '1px solid',
                                borderColor: isAssigned ? 'var(--primary-yellow)' : 'var(--border-light)',
                                background: isAssigned ? 'var(--bg-yellow-light)' : '#FFFFFF',
                                color: isAssigned ? '#854D0E' : 'var(--text-primary)',
                                fontWeight: isAssigned ? 700 : 500,
                              }}
                            >
                              {isAssigned ? '✓ ' : '+ '} {inst.name}
                            </button>
                          );
                        })
                      )}
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                    {editingSubjId && (
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => { setEditingSubjId(null); setSubjName(''); setSubjCode(''); setSubjInstIds([]); }}
                        style={{ padding: '0.55rem 0.8rem' }}
                      >
                        Cancel
                      </button>
                    )}
                    <button type="submit" className="btn-primary" style={{ padding: '0.55rem 1rem' }}>
                      {editingSubjId ? 'Save Changes' : 'Add Subject'}
                    </button>
                  </div>
                </form>
              </div>

              <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.75rem' }}>Active Subjects</h4>
              <div className="table-container">
                <table className="styled-table">
                  <thead>
                    <tr>
                      <th>Subject Name</th>
                      <th>Code</th>
                      <th>Department</th>
                      <th>Assigned Instructors</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {subjects.map((sub) => (
                      <tr key={sub.id}>
                        <td style={{ fontWeight: 600 }}>{sub.name}</td>
                        <td>{sub.code || '—'}</td>
                        <td>{sub.department_name || '—'}</td>
                        <td>
                          <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
                            {sub.instructors && sub.instructors.length > 0 ? (
                              sub.instructors.map((i) => (
                                <span key={i.id} className="tag-pill">
                                  {i.name}
                                </span>
                              ))
                            ) : (
                              <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>None</span>
                            )}
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: '0.4rem' }}>
                            <button
                              onClick={() => {
                                setEditingSubjId(sub.id);
                                setSubjName(sub.name);
                                setSubjCode(sub.code || '');
                                setSubjDeptId(sub.department_id);
                                setSubjInstIds(sub.instructors ? sub.instructors.map((i) => i.id) : []);
                              }}
                              style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem', background: '#FEF9C3', borderRadius: '4px', color: '#854D0E' }}
                            >
                              <Edit2 size={12} /> Edit
                            </button>
                            <button
                              onClick={() => handleDeactivateSubj(sub.id, sub.name)}
                              style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem', background: '#FEE2E2', borderRadius: '4px', color: '#B91C1C' }}
                            >
                              <Trash2 size={12} /> Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 3: INSTRUCTORS */}
          {activeTab === 'instructors' && (
            <div>
              <div style={{ background: '#FAF9F5', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-light)', marginBottom: '1.5rem' }}>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.75rem' }}>
                  {editingInstId ? 'Edit Instructor' : 'Add New Instructor'}
                </h4>
                <form onSubmit={handleSaveInstructor} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <div style={{ flex: 2, minWidth: '220px' }}>
                      <label className="form-label" style={{ fontSize: '0.78rem' }}>Instructor Full Name *</label>
                      <input
                        type="text"
                        className="form-input"
                        placeholder="e.g. Dr. Robert Vance"
                        value={instName}
                        onChange={(e) => setInstName(e.target.value)}
                        required
                      />
                    </div>
                    <div style={{ flex: 2, minWidth: '220px' }}>
                      <label className="form-label" style={{ fontSize: '0.78rem' }}>Department *</label>
                      <select
                        className="form-select"
                        value={instDeptId}
                        onChange={(e) => {
                          setInstDeptId(Number(e.target.value));
                          setInstSubjIds([]);
                        }}
                        required
                      >
                        {departments.filter(d => d.is_active).map((d) => (
                          <option key={d.id} value={d.id}>{d.name}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="form-label" style={{ fontSize: '0.78rem' }}>
                      Assign to Subjects in Department (Multiple Selection)
                    </label>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', maxHeight: '100px', overflowY: 'auto', padding: '0.5rem', background: '#FFFFFF', border: '1px solid var(--border-light)', borderRadius: '6px' }}>
                      {availableSubjectsForInstructor.length === 0 ? (
                        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                          No subjects available in this department. Add subjects first.
                        </span>
                      ) : (
                        availableSubjectsForInstructor.map((sub) => {
                          const isAssigned = instSubjIds.includes(sub.id);
                          return (
                            <button
                              key={sub.id}
                              type="button"
                              onClick={() => {
                                if (isAssigned) {
                                  setInstSubjIds(instSubjIds.filter((id) => id !== sub.id));
                                } else {
                                  setInstSubjIds([...instSubjIds, sub.id]);
                                }
                              }}
                              style={{
                                padding: '0.25rem 0.6rem',
                                borderRadius: '4px',
                                fontSize: '0.78rem',
                                border: '1px solid',
                                borderColor: isAssigned ? 'var(--primary-yellow)' : 'var(--border-light)',
                                background: isAssigned ? 'var(--bg-yellow-light)' : '#FFFFFF',
                                color: isAssigned ? '#854D0E' : 'var(--text-primary)',
                                fontWeight: isAssigned ? 700 : 500,
                              }}
                            >
                              {isAssigned ? '✓ ' : '+ '} {sub.name}
                            </button>
                          );
                        })
                      )}
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                    {editingInstId && (
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => { setEditingInstId(null); setInstName(''); setInstSubjIds([]); }}
                        style={{ padding: '0.55rem 0.8rem' }}
                      >
                        Cancel
                      </button>
                    )}
                    <button type="submit" className="btn-primary" style={{ padding: '0.55rem 1rem' }}>
                      {editingInstId ? 'Save Changes' : 'Save Instructor'}
                    </button>
                  </div>
                </form>
              </div>

              <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.75rem' }}>Active Instructors</h4>
              <div className="table-container">
                <table className="styled-table">
                  <thead>
                    <tr>
                      <th>Instructor Name</th>
                      <th>Department</th>
                      <th>Assigned Subjects</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {instructors.map((inst) => (
                      <tr key={inst.id}>
                        <td style={{ fontWeight: 600 }}>{inst.name}</td>
                        <td>{inst.department_name || inst.department || '—'}</td>
                        <td>
                          <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
                            {inst.subjects && inst.subjects.length > 0 ? (
                              inst.subjects.map((s) => (
                                <span key={s.id} className="tag-pill">
                                  {s.name}
                                </span>
                              ))
                            ) : (
                              <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>None</span>
                            )}
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: '0.4rem' }}>
                            <button
                              onClick={() => {
                                setEditingInstId(inst.id);
                                setInstName(inst.name);
                                setInstDeptId(inst.department_id || (departments.length > 0 ? departments[0].id : 0));
                                setInstSubjIds(inst.subjects ? inst.subjects.map((s) => s.id) : []);
                              }}
                              style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem', background: '#FEF9C3', borderRadius: '4px', color: '#854D0E' }}
                            >
                              <Edit2 size={12} /> Edit
                            </button>
                            <button
                              onClick={() => handleDeactivateInst(inst.id, inst.name)}
                              style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem', background: '#FEE2E2', borderRadius: '4px', color: '#B91C1C' }}
                            >
                              <Trash2 size={12} /> Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
