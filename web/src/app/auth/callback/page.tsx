'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';

function getApiBase(): string {
  if (typeof window === 'undefined') return '/api/v1';
  const url = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (url && (url.startsWith('http://') || url.startsWith('https://'))) return `${url.replace(/\/$/, '')}/api/v1`;
  return '/api/v1';
}
const API_BASE = getApiBase();

function CallbackContent() {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');
  const [redirectUri, setRedirectUri] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const copyRedirectUri = (uri: string) => {
    navigator.clipboard.writeText(uri).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  useEffect(() => {
    fetch(`${API_BASE}/auth/redirect-uri`)
      .then((r) => r.ok ? r.json() : null)
      .then((d) => d?.redirect_uri && setRedirectUri(d.redirect_uri))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const code = searchParams.get('code');
    if (!code) {
      setStatus('error');
      setMessage('No authorization code received from Upstox.');
      return;
    }

    (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/upstox/exchange`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code }),
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok) {
          setStatus('success');
          window.location.href = '/?upstox=connected';
          return;
        }
        setStatus('error');
        const msg = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
        setMessage(
          typeof msg === 'string'
            ? msg
            : 'Token exchange failed. Check redirect URI in Upstox app matches http://localhost:3000/auth/callback and try again.'
        );
      } catch {
        setStatus('error');
        setMessage('Could not reach backend. Start the backend (e.g. .\\Start-Backend.ps1) and try again.');
      }
    })();
  }, [searchParams]);

  if (status === 'loading') {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
        Connecting to Upstox…
      </div>
    );
  }

  if (status === 'error') {
    const isInvalidCode = /Invalid Auth code|UDAPI100057|redirect.*uri/i.test(message);
    const displayUri = redirectUri || 'http://localhost:3000/auth/callback';
    return (
      <div style={{ padding: '2rem', maxWidth: 560, margin: '0 auto', overflowWrap: 'break-word', wordBreak: 'break-word' }}>
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--accent)', borderRadius: 8, padding: '0.75rem 1rem', marginBottom: '1rem', fontSize: '0.875rem' }}>
          <strong>Quick fix:</strong> Click <strong>&quot;Use Access Token instead&quot;</strong> below to connect without OAuth — paste your Upstox token on the dashboard.
        </div>
        <p style={{ color: 'var(--negative)', marginBottom: '0.75rem', overflowWrap: 'break-word' }}>{message}</p>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
          The authorization code is one-time use. Go back, click <strong>Connect Upstox</strong> again, and complete login without refreshing this page.
        </p>
        {isInvalidCode && (
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
            In <strong>Upstox Developer Console</strong> → your app → <strong>Redirect URI</strong>, set exactly (copy below):
          </p>
        )}
        {isInvalidCode && (
          <div style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <code style={{ background: 'var(--bg-card)', padding: '0.35rem 0.5rem', borderRadius: 6, fontSize: '0.8125rem', wordBreak: 'break-all', flex: '1 1 200px' }}>
              {displayUri}
            </code>
            <button
              type="button"
              onClick={() => copyRedirectUri(displayUri)}
              style={{
                padding: '0.35rem 0.75rem',
                background: 'var(--accent)',
                color: '#fff',
                border: 'none',
                borderRadius: 6,
                fontWeight: 600,
                fontSize: '0.8125rem',
                cursor: 'pointer',
              }}
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
        )}
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
          No trailing slash. Then restart backend if you changed .env, and try Connect Upstox again.
        </p>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
          <strong>Or skip OAuth:</strong> use Access Token — go to dashboard and in the Connect modal choose &quot;Or enter Access Token&quot; and paste your token.
        </p>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <a
            href="/?connect=1"
            style={{
              display: 'inline-block',
              padding: '0.5rem 1rem',
              background: 'var(--accent)',
              color: '#fff',
              borderRadius: 8,
              fontWeight: 600,
              fontSize: '0.875rem',
              textDecoration: 'none',
            }}
          >
            Use Access Token instead →
          </a>
          <a href="/" style={{ color: 'var(--accent)', fontSize: '0.875rem', fontWeight: 500 }}>
            ← Back to dashboard
          </a>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
      Redirecting to dashboard…
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<div style={{ padding: '2rem', textAlign: 'center' }}>Loading…</div>}>
      <CallbackContent />
    </Suspense>
  );
}
