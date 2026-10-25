
import React, { useEffect, useState } from 'react';
import { Navbar } from './components/Navbar';
import { HomePage } from './pages/HomePage';
import { StudentFeedbackPage } from './pages/StudentFeedbackPage';
import { AdminDashboardPage } from './pages/AdminDashboardPage';
import { AllFeedbackPage } from './pages/AllFeedbackPage';
import { AdminLoginPage } from './pages/AdminLoginPage';

type Tab = 'home' | 'student' | 'admin' | 'all-feedback';

const TOKEN_KEY = 'stufeed_admin_token';

function installAuthenticatedFetch(): void {
  const win = window as Window & { __stufeedFetchInstalled?: boolean };

  if (win.__stufeedFetchInstalled) return;

  const originalFetch = window.fetch.bind(window);

  window.fetch = (async (
    input: RequestInfo | URL,
    init?: RequestInit,
  ): Promise<Response> => {
    const url =
      typeof input === 'string'
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;

    const isApiRequest = url.startsWith('/api/') || url.includes('/api/');
    const isLoginRequest = url.includes('/api/auth/login');
    const token = localStorage.getItem(TOKEN_KEY);

    if (!isApiRequest || isLoginRequest || !token) {
      return originalFetch(input, init);
    }

    const headers = new Headers(
      init?.headers ?? (input instanceof Request ? input.headers : undefined),
    );
    headers.set('Authorization', `Bearer ${token}`);

    const response = await originalFetch(input, {
      ...init,
      headers,
    });

    // An expired or invalid session should return the user to the login page.
    if (response.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      window.dispatchEvent(new Event('stufeed-admin-session-expired'));
    }

    return response;
  }) as typeof window.fetch;

  win.__stufeedFetchInstalled = true;
}

export function App() {
  const [currentTab, setCurrentTab] = useState<Tab>('home');
  const [adminToken, setAdminToken] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_KEY),
  );

  useEffect(() => {
    installAuthenticatedFetch();

    const handleLocation = () => {
      const path = window.location.pathname;

      if (path === '/student') {
        setCurrentTab('student');
      } else if (path === '/admin') {
        setCurrentTab('admin');
      } else if (path === '/all-feedback') {
        setCurrentTab('all-feedback');
      } else {
        setCurrentTab('home');
      }
    };

    const handleSessionExpired = () => {
      setAdminToken(null);
      if (
        window.location.pathname === '/admin' ||
        window.location.pathname === '/all-feedback'
      ) {
        setCurrentTab('admin');
      }
    };

    handleLocation();
    window.addEventListener('popstate', handleLocation);
    window.addEventListener(
      'stufeed-admin-session-expired',
      handleSessionExpired,
    );

    return () => {
      window.removeEventListener('popstate', handleLocation);
      window.removeEventListener(
        'stufeed-admin-session-expired',
        handleSessionExpired,
      );
    };
  }, []);

  const navigateTo = (tab: Tab) => {
    setCurrentTab(tab);
    const targetPath = tab === 'home' ? '/' : `/${tab}`;

    if (window.location.pathname !== targetPath) {
      window.history.pushState({}, '', targetPath);
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleLoginSuccess = () => {
    setAdminToken(localStorage.getItem(TOKEN_KEY));
    navigateTo('admin');
  };

  const handleLogout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setAdminToken(null);
    navigateTo('home');
  };

  const isAdminPage =
    currentTab === 'admin' || currentTab === 'all-feedback';

  return (
    <div className="app-container">
      <Navbar currentTab={currentTab} setCurrentTab={navigateTo} />

      <main className="main-content">
        {currentTab === 'home' && <HomePage onNavigate={navigateTo} />}

        {currentTab === 'student' && <StudentFeedbackPage />}

        {isAdminPage && !adminToken && (
          <AdminLoginPage
            onSuccess={handleLoginSuccess}
            onCancel={() => navigateTo('home')}
          />
        )}

        {currentTab === 'admin' && adminToken && (
          <>
            <div
              style={{
                display: 'flex',
                justifyContent: 'flex-end',
                margin: '0 0 1rem',
              }}
            >
              <button type="button" onClick={handleLogout}>
                Log out
              </button>
            </div>
            <AdminDashboardPage
              onNavigateToAllFeedback={() => navigateTo('all-feedback')}
            />
          </>
        )}

        {currentTab === 'all-feedback' && adminToken && (
          <>
            <div
              style={{
                display: 'flex',
                justifyContent: 'flex-end',
                margin: '0 0 1rem',
              }}
            >
              <button type="button" onClick={handleLogout}>
                Log out
              </button>
            </div>
            <AllFeedbackPage
              onBackToDashboard={() => navigateTo('admin')}
            />
          </>
        )}
      </main>

      <footer
        className="footer"
        style={{
          padding: '1.5rem',
          textAlign: 'center',
          borderTop: '1px solid var(--border-light)',
          backgroundColor: '#FFFFFF',
        }}
      >
        <p
          style={{
            color: 'var(--text-secondary)',
            fontSize: '0.85rem',
            fontWeight: 500,
          }}
        >
          “Every voice matters. Every insight creates an opportunity to improve.”
        </p>
      </footer>
    </div>
  );
}

export default App;
