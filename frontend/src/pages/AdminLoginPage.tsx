
import React, { useState } from 'react';

interface AdminLoginPageProps {
  onSuccess: () => void;
  onCancel: () => void;
}

export const AdminLoginPage: React.FC<AdminLoginPageProps> = ({
  onSuccess,
  onCancel,
}) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Unable to log in.');
      }

      if (!data.access_token) {
        throw new Error('The server did not return a session token.');
      }

      localStorage.setItem('stufeed_admin_token', data.access_token);
      onSuccess();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Login failed. Check that the backend is running.',
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <section
      style={{
        maxWidth: 440,
        margin: '3rem auto',
        padding: '2rem',
        background: '#FFFFFF',
        border: '1px solid #E9E2CF',
        borderRadius: 16,
        boxShadow: '0 8px 28px rgba(0,0,0,0.06)',
      }}
    >
      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <h2 style={{ marginBottom: 8, color: '#242424' }}>
          Admin Login
        </h2>
        <p style={{ color: '#686868', margin: 0 }}>
          Sign in to view StuFeed analytics and manage academic records.
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        <label
          htmlFor="admin-email"
          style={{ display: 'block', marginBottom: 6, fontWeight: 600 }}
        >
          Admin email
        </label>
        <input
          id="admin-email"
          type="email"
          autoComplete="username"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
          style={{
            width: '100%',
            boxSizing: 'border-box',
            padding: 12,
            border: '1px solid #D9D2C0',
            borderRadius: 8,
            marginBottom: 16,
          }}
        />

        <label
          htmlFor="admin-password"
          style={{ display: 'block', marginBottom: 6, fontWeight: 600 }}
        >
          Password
        </label>
        <input
          id="admin-password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
          style={{
            width: '100%',
            boxSizing: 'border-box',
            padding: 12,
            border: '1px solid #D9D2C0',
            borderRadius: 8,
            marginBottom: 16,
          }}
        />

        {error && (
          <p role="alert" style={{ color: '#B42318', marginBottom: 16 }}>
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            width: '100%',
            padding: 13,
            border: 0,
            borderRadius: 8,
            background: '#F5C842',
            color: '#242424',
            fontWeight: 700,
            cursor: loading ? 'wait' : 'pointer',
          }}
        >
          {loading ? 'Signing in…' : 'Sign in'}
        </button>

        <button
          type="button"
          onClick={onCancel}
          style={{
            width: '100%',
            padding: 12,
            marginTop: 10,
            border: '1px solid #E2DCCB',
            borderRadius: 8,
            background: '#FFFFFF',
            cursor: 'pointer',
          }}
        >
          Back to Home
        </button>
      </form>
    </section>
  );
};
