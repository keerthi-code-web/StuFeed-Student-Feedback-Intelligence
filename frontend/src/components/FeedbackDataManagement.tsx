
import React, { useEffect, useState } from "react";

type Item = { id?: number; name: string; semester?: number };

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "10px",
  border: "1px solid #d1d5db",
  borderRadius: 7,
  background: "#fff",
};

const buttonStyle: React.CSSProperties = {
  padding: "11px 15px",
  border: 0,
  borderRadius: 7,
  color: "#fff",
  cursor: "pointer",
  fontWeight: 600,
};

export const FeedbackDataManagement: React.FC = () => {
  const [departments, setDepartments] = useState<Item[]>([]);
  const [subjects, setSubjects] = useState<Item[]>([]);
  const [instructors, setInstructors] = useState<Item[]>([]);

  const [department, setDepartment] = useState("");
  const [semester, setSemester] = useState("");
  const [subject, setSubject] = useState("");
  const [instructor, setInstructor] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const isOther = department.toLowerCase() === "other";

  const token = () => localStorage.getItem("stufeed_admin_token") || "";

  const authHeaders = () => ({
    Authorization: `Bearer ${token()}`,
    "Content-Type": "application/json",
  });

  useEffect(() => {
    fetch("/api/departments")
      .then(async (r) => {
        if (!r.ok) throw new Error("Failed to load departments");
        return r.json();
      })
      .then((data) => {
        const list = Array.isArray(data) ? data : data.departments || [];
        setDepartments(list.filter((x: Item) => x?.name));
      })
      .catch(() => setMessage("Could not load departments. Check the backend."));
  }, []);

  useEffect(() => {
    setSubject("");
    setInstructor("");
    setSemester("");
    setSubjects([]);
    setInstructors([]);

    if (!department || isOther) return;

    fetch(`/api/subjects?department_name=${encodeURIComponent(department)}`)
      .then(async (r) => {
        if (!r.ok) throw new Error("Failed to load subjects");
        return r.json();
      })
      .then((data: Item[]) => setSubjects(Array.isArray(data) ? data : []))
      .catch(() => setMessage("Could not load subjects."));
  }, [department]);

  useEffect(() => {
    setInstructor("");
    setInstructors([]);

    if (!department || isOther) return;

    const selected = subjects.find((x) => x.name === subject);
    let url = `/api/instructors?department_name=${encodeURIComponent(department)}`;

    if (selected?.id) url += `&subject_id=${selected.id}`;
    else if (subject) url += `&subject_name=${encodeURIComponent(subject)}`;

    fetch(url)
      .then(async (r) => {
        if (!r.ok) throw new Error("Failed to load instructors");
        return r.json();
      })
      .then((data: Item[]) => setInstructors(Array.isArray(data) ? data : []))
      .catch(() => setMessage("Could not load instructors."));
  }, [department, subject, subjects]);

  const getScope = () => ({
    ...(department ? { department_name: department } : {}),
    ...(!isOther && semester ? { semester: Number(semester) } : {}),
    ...(!isOther && subject ? { subject_name: subject } : {}),
    ...(!isOther && instructor ? { instructor_name: instructor } : {}),
  });

  const describeScope = () =>
    [
      department || "All departments",
      !isOther && semester ? `Semester ${semester}` : "",
      !isOther && subject ? `Subject: ${subject}` : "",
      !isOther && instructor ? `Instructor: ${instructor}` : "",
    ]
      .filter(Boolean)
      .join(" / ");

  const downloadReport = async () => {
    const response = await fetch("/api/admin/feedback-data/report", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(getScope()),
    });

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || "Report generation failed.");
    }

    const cutoff = response.headers.get("X-Report-Cutoff-UTC");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");

    anchor.href = url;
    anchor.download = `stufeed_feedback_report_${new Date()
      .toISOString()
      .replace(/[:.]/g, "-")}.pdf`;

    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);

    return cutoff;
  };

  const generateReport = async () => {
    setBusy(true);
    setMessage("");

    try {
      await downloadReport();
      setMessage("PDF downloaded successfully. No feedback was deleted.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Report failed.");
    } finally {
      setBusy(false);
    }
  };

  const reportThenDelete = async () => {
    setBusy(true);
    setMessage("");

    try {
      const cutoff = await downloadReport();

      if (!cutoff) {
        setMessage(
          "Report downloaded, but the report cutoff was missing. No feedback was deleted."
        );
        return;
      }

      if (
        !window.confirm(
          `The report has been downloaded.\n\nScope: ${describeScope()}\n\nPermanently delete only feedback included up to the report time?`
        )
      ) {
        setMessage("Deletion cancelled. Feedback remains unchanged.");
        return;
      }

      const email = window.prompt("Re-enter the admin email to confirm:");
      if (!email?.trim()) {
        setMessage("Deletion cancelled.");
        return;
      }

      const password = window.prompt("Enter the admin password to confirm:");
      if (!password) {
        setMessage("Deletion cancelled.");
        return;
      }

      const response = await fetch("/api/admin/feedback-data/delete", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          ...getScope(),
          admin_password: password,
          cutoff_created_at: cutoff,
        }),
      });

      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Deletion failed.");

      setMessage(`${body.message} The PDF was downloaded first.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Operation failed.");
    } finally {
      setBusy(false);
    }
  };

  const clearWithoutReport = async () => {
    if (
      !window.confirm(
        `This permanently deletes feedback without a report.\n\nScope: ${describeScope()}\n\nDepartments, subjects, instructors, and student identity records will remain. Continue?`
      )
    ) {
      setMessage("Clear cancelled. No feedback was deleted.");
      return;
    }

    const email = window.prompt("Re-enter the admin email to confirm:");
    if (!email?.trim()) {
      setMessage("Clear cancelled.");
      return;
    }

    const password = window.prompt("Enter the admin password to confirm:");
    if (!password) {
      setMessage("Clear cancelled.");
      return;
    }

    setBusy(true);
    setMessage("");

    try {
      const response = await fetch("/api/admin/feedback-data/delete", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          ...getScope(),
          admin_password: password,
        }),
      });

      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Clear operation failed.");

      setMessage(body.message);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Clear failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section
      style={{
        margin: "0 auto 35px",
        padding: 22,
        maxWidth: 1000,
        border: "1px solid #e5e7eb",
        borderRadius: 12,
        background: "#fff",
      }}
    >
      <h3 style={{ marginTop: 0 }}>Feedback Report & Data Management</h3>
      <p style={{ color: "#6b7280" }}>
        Select the exact feedback scope before generating a report or deleting
        records.
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
          gap: 14,
        }}
      >
        <label>
          Department
          <select
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            style={inputStyle}
          >
            <option value="">All departments</option>
            {departments.map((x) => (
              <option key={x.id ?? x.name} value={x.name}>
                {x.name}
              </option>
            ))}
            {!departments.some((x) => x.name.toLowerCase() === "other") && (
              <option value="Other">Other — Institutional</option>
            )}
          </select>
        </label>

        <label>
          Semester
          <select
            value={semester}
            disabled={!department || isOther}
            onChange={(e) => setSemester(e.target.value)}
            style={inputStyle}
          >
            <option value="">All semesters</option>
            {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
              <option key={n} value={n}>
                Semester {n}
              </option>
            ))}
          </select>
        </label>

        <label>
          Subject
          <select
            value={subject}
            disabled={!department || isOther}
            onChange={(e) => setSubject(e.target.value)}
            style={inputStyle}
          >
            <option value="">All subjects</option>
            {subjects.map((x) => (
              <option key={x.id ?? x.name} value={x.name}>
                {x.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Instructor
          <select
            value={instructor}
            disabled={!department || isOther}
            onChange={(e) => setInstructor(e.target.value)}
            style={inputStyle}
          >
            <option value="">All instructors</option>
            {instructors.map((x) => (
              <option key={x.id ?? x.name} value={x.name}>
                {x.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <p style={{ margin: "15px 0", color: "#374151" }}>
        <b>Selected scope:</b> {describeScope()}
      </p>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
        <button
          disabled={busy}
          onClick={generateReport}
          style={{ ...buttonStyle, background: "#1d4ed8" }}
        >
          Generate & Download Report
        </button>

        <button
          disabled={busy}
          onClick={reportThenDelete}
          style={{ ...buttonStyle, background: "#b45309" }}
        >
          Generate Report & Delete Selected Feedback
        </button>

        <button
          disabled={busy}
          onClick={clearWithoutReport}
          style={{ ...buttonStyle, background: "#b91c1c" }}
        >
          Clear Selected Feedback Without Saving
        </button>
      </div>

      {busy && <p>Processing request…</p>}

      {message && (
        <p
          role="status"
          style={{
            marginTop: 14,
            padding: 10,
            borderRadius: 7,
            background: "#f3f4f6",
            whiteSpace: "pre-wrap",
          }}
        >
          {message}
        </p>
      )}
    </section>
  );
};

export default FeedbackDataManagement;
