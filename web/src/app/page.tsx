'use client';

import { useState, useEffect, useCallback } from 'react';

// Use relative path so Next.js rewrites to backend (avoids CORS). Only use NEXT_PUBLIC_API_URL if it's http(s).
function getApiBase(): string {
  if (typeof window === 'undefined') return '/api/v1';
  const url = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (url && (url.startsWith('http://') || url.startsWith('https://'))) return `${url.replace(/\/$/, '')}/api/v1`;
  return '/api/v1';
}
const API_BASE = getApiBase();

type UpstoxStatus = { connected: boolean; message?: string };

type MarketContext = {
  symbol: string;
  last_price: number;
  bias: string;
  source: string;
};

type ChartCandleItem = { time: string; open: number; high: number; low: number; close: number };

type ExtendedMarketContext = {
  symbol: string;
  last_price: number;
  bias: string;
  source: string;
  ema20_15m: number | null;
  ema200_15m: number | null;
  ema20_5m: number | null;
  ema200_5m: number | null;
  cpr_pivot: number | null;
  cpr_bottom: number | null;
  cpr_top: number | null;
  cpr_width: number | null;
  cpr_width_pct: number | null;
  cpr_trend_hint: string | null;
  range_5m_low: number | null;
  range_5m_high: number | null;
  range_15m_low: number | null;
  range_15m_high: number | null;
  prev_day_high: number | null;
  prev_day_low: number | null;
  chart_candles?: ChartCandleItem[] | null;
};

type RiskCheckItem = { rule: string; passed: boolean; reason?: string };
type SignalData = {
  status: string;
  reason: string;
  time_window_ok: boolean;
  risk_checklist: RiskCheckItem[];
  rejected?: boolean;
  rejected_reason?: string | null;
};

type PositionItem = {
  id: string;
  symbol: string;
  option_type: string;
  side: string;
  quantity: number;
  entry_price: number;
  sl_trigger: number;
  initial_sl: number;
  order_id: string;
  created_at: string;
};

type HistoryItem = {
  id: string;
  event_type: string;
  position_id: string | null;
  symbol: string;
  at: string;
  details: string;
  old_sl: number | null;
  new_sl: number | null;
};

type HoldingOpportunity = {
  isin: string | null;
  exchange: string | null;
  tradingsymbol: string | null;
  company_name: string | null;
  quantity: number | null;
  average_price: number | null;
  last_price: number | null;
  close_price: number | null;
  pnl: number | null;
  day_change: number | null;
  day_change_percentage: number | null;
  instrument_token: string | null;
  status: string | null;
  direction: string | null;
  reason: string | null;
  bias: string | null;
  pattern: string | null;
  pattern_strength: number | null;
  ema20: number | null;
  ema200: number | null;
  last_15m_time: string | null;
};

export default function DashboardPage() {
  const [upstoxConnected, setUpstoxConnected] = useState(false);
  const [connectModalOpen, setConnectModalOpen] = useState(false);
  const [accessTokenInput, setAccessTokenInput] = useState('');
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backendReachable, setBackendReachable] = useState<boolean | null>(null);
  const [marketNifty, setMarketNifty] = useState<MarketContext | null>(null);
  const [marketSensex, setMarketSensex] = useState<MarketContext | null>(null);
  const [extendedNifty, setExtendedNifty] = useState<ExtendedMarketContext | null>(null);
  const [extendedSensex, setExtendedSensex] = useState<ExtendedMarketContext | null>(null);
  const [signalNifty, setSignalNifty] = useState<SignalData | null>(null);
  const [signalLoading, setSignalLoading] = useState(false);
  // Trade settings (persist in localStorage). Defaults must match server/client to avoid hydration error.
  const [selectedIndex, setSelectedIndex] = useState<'NIFTY' | 'SENSEX'>('NIFTY');
  const [tradingMode, setTradingMode] = useState<'MANUAL' | 'SEMI_AUTO' | 'FULL_AUTO'>('MANUAL');
  const [optionType, setOptionType] = useState<'CE' | 'PE'>('CE');
  const [lots, setLots] = useState<number>(1);
  const [targetPremiumNifty, setTargetPremiumNifty] = useState<number>(200);
  const [targetPremiumSensex, setTargetPremiumSensex] = useState<number>(500);
  const [strikeNifty, setStrikeNifty] = useState<number>(25100);
  const [strikeSensex, setStrikeSensex] = useState<number>(81200);
  const [modeConsentOpen, setModeConsentOpen] = useState(false);
  const [pendingMode, setPendingMode] = useState<'SEMI_AUTO' | 'FULL_AUTO' | null>(null);
  const [positions, setPositions] = useState<PositionItem[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [signalHistory, setSignalHistory] = useState<{ symbol: string; status: string; reason: string; at: string }[]>([]);
  const [holdingsOpp, setHoldingsOpp] = useState<HoldingOpportunity[]>([]);
  const [holdingsMessage, setHoldingsMessage] = useState<string | null>(null);

  // After mount, restore from localStorage (client-only; avoids hydration mismatch)
  useEffect(() => {
    const idx = (localStorage.getItem('capitalguard_index') as 'NIFTY' | 'SENSEX') || 'NIFTY';
    setSelectedIndex(idx);
    const mode = (localStorage.getItem('capitalguard_mode') as 'MANUAL' | 'SEMI_AUTO' | 'FULL_AUTO') || 'MANUAL';
    setTradingMode(mode);
    const opt = (localStorage.getItem('capitalguard_option_type') as 'CE' | 'PE') || 'CE';
    setOptionType(opt);
    const v = parseInt(localStorage.getItem('capitalguard_lots') ?? '1', 10);
    if (Number.isFinite(v) && v >= 1 && v <= 10) setLots(v);
    const niftyPrem = parseInt(localStorage.getItem('capitalguard_target_premium_nifty') ?? '200', 10);
    if (Number.isFinite(niftyPrem) && niftyPrem >= 50 && niftyPrem <= 2000) setTargetPremiumNifty(niftyPrem);
    const sensexPrem = parseInt(localStorage.getItem('capitalguard_target_premium_sensex') ?? '500', 10);
    if (Number.isFinite(sensexPrem) && sensexPrem >= 50 && sensexPrem <= 2000) setTargetPremiumSensex(sensexPrem);
    const niftyStrike = parseInt(localStorage.getItem('capitalguard_strike_nifty') ?? '25100', 10);
    if (Number.isFinite(niftyStrike)) setStrikeNifty(Math.round(niftyStrike / 100) * 100);
    const sensexStrike = parseInt(localStorage.getItem('capitalguard_strike_sensex') ?? '81200', 10);
    if (Number.isFinite(sensexStrike)) setStrikeSensex(Math.round(sensexStrike / 100) * 100);
  }, []);

  useEffect(() => {
    localStorage.setItem('capitalguard_index', selectedIndex);
  }, [selectedIndex]);
  useEffect(() => {
    localStorage.setItem('capitalguard_mode', tradingMode);
  }, [tradingMode]);
  useEffect(() => {
    localStorage.setItem('capitalguard_option_type', optionType);
  }, [optionType]);
  useEffect(() => {
    localStorage.setItem('capitalguard_lots', String(lots));
  }, [lots]);
  useEffect(() => {
    localStorage.setItem('capitalguard_target_premium_nifty', String(targetPremiumNifty));
    localStorage.setItem('capitalguard_target_premium_sensex', String(targetPremiumSensex));
  }, [targetPremiumNifty, targetPremiumSensex]);
  useEffect(() => {
    localStorage.setItem('capitalguard_strike_nifty', String(strikeNifty));
    localStorage.setItem('capitalguard_strike_sensex', String(strikeSensex));
  }, [strikeNifty, strikeSensex]);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/upstox/status`, { signal: AbortSignal.timeout(8000) });
      if (!res.ok) throw new Error('Backend returned error');
      setBackendReachable(true);
      const data: UpstoxStatus = await res.json();
      setUpstoxConnected(data.connected);
    } catch {
      setBackendReachable(false);
      setUpstoxConnected(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // If we landed with ?upstox=connected after OAuth redirect
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    if (params.get('upstox') === 'connected') {
      // Don't assume connected: backend stores token in memory; always re-check.
      fetchStatus();
      window.history.replaceState({}, '', window.location.pathname);
    }
    if (params.get('connect') === '1') {
      setConnectModalOpen(true);
      setError(null);
      setAccessTokenInput('');
      fetchStatus();
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  const HEALTH_TIMEOUT_MS = 5000;
  const MARKET_CONTEXT_TIMEOUT_MS = 30000;

  // Fetch market context (LTP + extended: CPR, ranges, prev day, EMAs) when Upstox is connected.
  // Ping /health first so we show "Backend not reachable" quickly if backend is down (avoids long proxy errors).
  const fetchMarketContext = useCallback(async () => {
    if (!upstoxConnected) return;
    try {
      const healthRes = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(HEALTH_TIMEOUT_MS) });
      if (!healthRes.ok) throw new Error('Health check failed');
    } catch {
      setBackendReachable(false);
      setMarketNifty(null);
      setMarketSensex(null);
      setExtendedNifty(null);
      setExtendedSensex(null);
      return;
    }
    setBackendReachable(true);
    try {
      const [niftyRes, sensexRes, extNiftyRes, extSensexRes] = await Promise.all([
        fetch(`${API_BASE}/market/context/NIFTY`, { signal: AbortSignal.timeout(MARKET_CONTEXT_TIMEOUT_MS) }),
        fetch(`${API_BASE}/market/context/SENSEX`, { signal: AbortSignal.timeout(MARKET_CONTEXT_TIMEOUT_MS) }),
        fetch(`${API_BASE}/market/context/extended/NIFTY`, { signal: AbortSignal.timeout(MARKET_CONTEXT_TIMEOUT_MS) }),
        fetch(`${API_BASE}/market/context/extended/SENSEX`, { signal: AbortSignal.timeout(MARKET_CONTEXT_TIMEOUT_MS) }),
      ]);
      const niftyData = niftyRes.ok ? await niftyRes.json() : null;
      const sensexData = sensexRes.ok ? await sensexRes.json() : null;
      setMarketNifty(niftyData ? { symbol: niftyData.symbol, last_price: niftyData.last_price, bias: niftyData.bias, source: niftyData.source } : null);
      setMarketSensex(sensexData ? { symbol: sensexData.symbol, last_price: sensexData.last_price, bias: sensexData.bias, source: sensexData.source } : null);
      setExtendedNifty(extNiftyRes.ok ? await extNiftyRes.json() : null);
      setExtendedSensex(extSensexRes.ok ? await extSensexRes.json() : null);
    } catch {
      setMarketNifty(null);
      setMarketSensex(null);
      setExtendedNifty(null);
      setExtendedSensex(null);
      setBackendReachable(false);
    }
  }, [upstoxConnected]);

  useEffect(() => {
    fetchMarketContext();
    if (!upstoxConnected) return;
    const interval = setInterval(fetchMarketContext, 15000);
    return () => clearInterval(interval);
  }, [upstoxConnected, fetchMarketContext]);

  const fetchSignalHistory = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/signals/history?limit=30`);
      const data = await res.json();
      setSignalHistory(Array.isArray(data?.items) ? data.items : []);
    } catch {
      setSignalHistory([]);
    }
  }, []);

  const fetchSignal = useCallback(async () => {
    if (!upstoxConnected) return;
    setSignalLoading(true);
    try {
      const res = await fetch(`${API_BASE}/signals/evaluate/${selectedIndex}`);
      const data = await res.json();
      setSignalNifty({
        status: data.status ?? 'NO_SIGNAL',
        reason: data.reason ?? '',
        time_window_ok: data.time_window_ok ?? false,
        risk_checklist: Array.isArray(data.risk_checklist) ? data.risk_checklist : [],
        rejected: data.rejected,
        rejected_reason: data.rejected_reason,
      });
      fetchSignalHistory();
    } catch {
      setSignalNifty(null);
    } finally {
      setSignalLoading(false);
    }
  }, [upstoxConnected, selectedIndex, fetchSignalHistory]);

  useEffect(() => {
    fetchSignal();
    fetchSignalHistory();
    if (!upstoxConnected) return;
    const interval = setInterval(fetchSignal, 30000);
    const historyInterval = setInterval(fetchSignalHistory, 60000);
    return () => { clearInterval(interval); clearInterval(historyInterval); };
  }, [upstoxConnected, selectedIndex, fetchSignal, fetchSignalHistory]);

  const fetchPositions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/orders/positions`);
      const data = await res.json();
      setPositions(Array.isArray(data?.items) ? data.items : []);
    } catch {
      setPositions([]);
    }
  }, []);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/orders/history?limit=50`);
      const data = await res.json();
      setHistory(Array.isArray(data?.items) ? data.items : []);
    } catch {
      setHistory([]);
    }
  }, []);

  const fetchHoldingsOpp = useCallback(async () => {
    if (!upstoxConnected) return;
    try {
      const res = await fetch(`${API_BASE}/portfolio/holdings/opportunities?limit=10`, { signal: AbortSignal.timeout(30000) });
      const data = await res.json();
      setHoldingsOpp(Array.isArray(data?.items) ? data.items : []);
      setHoldingsMessage(typeof data?.message === 'string' ? data.message : null);
    } catch {
      setHoldingsOpp([]);
      setHoldingsMessage('Failed to load holdings from backend.');
    }
  }, [upstoxConnected]);

  useEffect(() => {
    fetchPositions();
    fetchHistory();
    fetchHoldingsOpp();
    const t = setInterval(() => {
      fetchPositions();
      fetchHistory();
      fetchHoldingsOpp();
    }, 20000);
    return () => clearInterval(t);
  }, [fetchPositions, fetchHistory, fetchHoldingsOpp]);

  const handleTradingModeClick = (mode: 'MANUAL' | 'SEMI_AUTO' | 'FULL_AUTO') => {
    if (mode === 'MANUAL') {
      setTradingMode('MANUAL');
      return;
    }
    setPendingMode(mode);
    setModeConsentOpen(true);
  };
  const confirmModeConsent = () => {
    if (pendingMode) {
      setTradingMode(pendingMode);
      setPendingMode(null);
      setModeConsentOpen(false);
    }
  };
  const cancelModeConsent = () => {
    setPendingMode(null);
    setModeConsentOpen(false);
  };

  const handleConnectUpstox = () => {
    setConnectModalOpen(true);
    setError(null);
    setAccessTokenInput('');
    fetchStatus(); // re-check backend when opening modal
  };

  const handleLoginWithUpstox = () => {
    // Redirect to backend; backend redirects to Upstox OAuth, then back to callback, then to frontend with ?upstox=connected
    window.location.href = `${API_BASE}/auth/upstox/login`;
  };

  const handleConnectWithAccessToken = async () => {
    const token = accessTokenInput.trim();
    if (!token) {
      setError('Please enter your Upstox Access Token.');
      return;
    }
    setConnecting(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/upstox/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ access_token: token }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
        setError(typeof msg === 'string' ? msg : 'Invalid or expired token. Please try again.');
        return;
      }
      setBackendReachable(true);
      setUpstoxConnected(true);
      setConnectModalOpen(false);
      setAccessTokenInput('');
    } catch {
      setBackendReachable(false);
      setError('Backend not reachable. Start the backend (Step 4 in the install guide): run uvicorn in the backend folder.');
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnectUpstox = async () => {
    try {
      await fetch(`${API_BASE}/auth/upstox/disconnect`, { method: 'POST' });
      setUpstoxConnected(false);
      setMarketNifty(null);
      setMarketSensex(null);
      setSignalNifty(null);
    } catch {
      setUpstoxConnected(false);
      setMarketNifty(null);
      setMarketSensex(null);
      setSignalNifty(null);
    }
  };

  const closeModal = () => {
    if (!connecting) {
      setConnectModalOpen(false);
      setError(null);
      setAccessTokenInput('');
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Connect Upstox modal */}
      {connectModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="connect-upstox-title"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '1rem',
          }}
          onClick={(e) => e.target === e.currentTarget && closeModal()}
        >
          <div
            className="card"
            style={{
              maxWidth: 420,
              width: '100%',
              padding: '1.5rem',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="connect-upstox-title" style={{ margin: '0 0 1rem 0', fontSize: '1.125rem' }}>
              Connect to Upstox
            </h2>
            {backendReachable === false && (
              <div style={{ margin: '0 0 1rem 0', padding: '0.75rem', background: 'rgba(218,54,51,0.15)', borderRadius: 'var(--radius)', color: 'var(--negative)', fontSize: '0.8125rem' }}>
                <p style={{ margin: 0 }}><strong>Connection failed.</strong> Start both:</p>
                <ol style={{ margin: '0.5rem 0 0 1.25rem', padding: 0 }}>
                  <li>Backend: from project root run <code style={{ background: 'var(--bg-page)', padding: '0.2em 0.4em', borderRadius: 4 }}>.\Start-Backend.ps1</code></li>
                  <li>Web app: in another terminal run <code style={{ background: 'var(--bg-page)', padding: '0.2em 0.4em', borderRadius: 4 }}>cd web; npm run dev</code></li>
                </ol>
                <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.75rem' }}>Open the app at <strong>http://localhost:3000</strong> (not file:// and not the API port 8000).</p>
                <button type="button" className="btn btn-primary" style={{ marginTop: '0.75rem' }} onClick={() => fetchStatus()}>Retry connection</button>
              </div>
            )}
            <p style={{ margin: '0 0 1.25rem 0', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
              API Key and Secret are configured on the server (.env). Either log in with Upstox (OAuth) or paste your Access Token below.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleLoginWithUpstox}
                disabled={connecting}
                style={{ width: '100%' }}
              >
                Login with Upstox (OAuth)
              </button>
              <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'center' }}>
                You will be redirected to Upstox to sign in. No need to enter a token.
              </p>

              <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem', marginTop: '0.5rem' }}>
                <label htmlFor="access-token" style={{ display: 'block', fontSize: '0.8125rem', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                  Or enter Access Token
                </label>
                <input
                  id="access-token"
                  type="password"
                  placeholder="Paste your Upstox Access Token here"
                  value={accessTokenInput}
                  onChange={(e) => setAccessTokenInput(e.target.value)}
                  disabled={connecting}
                  style={{
                    width: '100%',
                    padding: '0.5rem 0.75rem',
                    fontSize: '0.875rem',
                    background: 'var(--bg-page)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius)',
                    color: 'var(--text-primary)',
                  }}
                />
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleConnectWithAccessToken}
                  disabled={connecting}
                  style={{ width: '100%', marginTop: '0.75rem' }}
                >
                  {connecting ? 'Connecting…' : 'Connect with token'}
                </button>
              </div>

              {error && (
                <p style={{ margin: 0, fontSize: '0.8125rem', color: 'var(--negative)' }}>
                  {error}
                </p>
              )}
            </div>

            <button
              type="button"
              onClick={closeModal}
              disabled={connecting}
              style={{
                marginTop: '1.25rem',
                background: 'none',
                border: 'none',
                color: 'var(--text-secondary)',
                cursor: connecting ? 'not-allowed' : 'pointer',
                fontSize: '0.875rem',
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Header */}
      <header
        style={{
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg-card)',
          padding: '1rem 1.5rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.75rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
              Dasari&apos;s Algo Trading terminal
            </h1>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            {backendReachable === false && (
              <>
                <span className="badge badge-warning" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                  Backend unreachable
                </span>
                <button type="button" onClick={() => fetchStatus()} style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem', background: 'var(--bg-page)', border: '1px solid var(--border)', borderRadius: 4, color: 'var(--text-primary)', cursor: 'pointer' }}>
                  Retry
                </button>
              </>
            )}
            <span
              className={upstoxConnected ? 'badge badge-success' : 'badge badge-error'}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: upstoxConnected ? 'var(--positive)' : 'var(--negative)',
                }}
              />
              {upstoxConnected ? 'Upstox connected' : 'Upstox disconnected'}
            </span>
            {upstoxConnected ? (
              <button type="button" className="btn btn-danger" onClick={handleDisconnectUpstox}>
                Disconnect
              </button>
            ) : (
              <button type="button" className="btn btn-primary" onClick={handleConnectUpstox}>
                Connect Upstox
              </button>
            )}
          </div>
        </div>
        {!upstoxConnected && (
          <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            OAuth failing? Use <strong>Connect Upstox</strong> → <strong>Or enter Access Token</strong> to paste your token and skip redirect.
          </p>
        )}
      </header>

      <main style={{ padding: '1.5rem', flex: 1, maxWidth: 1200, margin: '0 auto', width: '100%' }}>
        {/* 1. Market context – top */}
        <section className="card dashboard-section" style={{ marginBottom: '1.25rem' }}>
          <h2 className="card-title" style={{ marginBottom: '0.5rem' }}>Market context</h2>
          <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.8125rem' }}>
            Live index price from Upstox. Strategy uses <strong>15m/5m/2m candles</strong> for <strong>EMAs</strong>, <strong>CPR</strong>, <strong>candlestick patterns</strong> and <strong>price action</strong>. CPR narrow = possible big trend; broad = choppy range.
          </p>
          <div style={{ marginTop: '1rem' }}>
            {upstoxConnected ? (
              <>
                <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap', alignItems: 'baseline' }}>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>NIFTY 50</span>
                    <span style={{ fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
                      {marketNifty?.source === 'live' && marketNifty.last_price > 0
                        ? `₹ ${marketNifty.last_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
                        : '—'}
                    </span>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>SENSEX</span>
                    <span style={{ fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
                      {marketSensex?.source === 'live' && marketSensex.last_price > 0
                        ? `₹ ${marketSensex.last_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
                        : '—'}
                    </span>
                  </div>
                </div>
                {/* Extended context: only the selected Index (NIFTY or SENSEX) – one block */}
                {(selectedIndex === 'NIFTY' ? extendedNifty : extendedSensex) && (() => {
                  const ext = selectedIndex === 'NIFTY' ? extendedNifty! : extendedSensex!;
                  return (
                    <div style={{ marginTop: '1.25rem', padding: '1rem', background: 'var(--bg-page)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
                      <div style={{ fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                        {ext.symbol} – Today&apos;s range &amp; CPR
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '1rem', fontSize: '0.8125rem' }}>
                        {ext.cpr_trend_hint != null && (
                          <div>
                            <span style={{ color: 'var(--text-muted)' }}>CPR trend</span>
                            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{ext.cpr_trend_hint}</div>
                          </div>
                        )}
                        <div>
                          <span style={{ color: 'var(--text-muted)' }}>Opening 5m (9:15–9:20)</span>
                          <div style={{ fontWeight: 600 }}>
                            {ext.range_5m_low != null && ext.range_5m_high != null
                              ? `${ext.range_5m_low.toFixed(2)} – ${ext.range_5m_high.toFixed(2)}`
                              : '—'}
                          </div>
                        </div>
                        <div>
                          <span style={{ color: 'var(--text-muted)' }}>Opening 15m (9:15–9:30)</span>
                          <div style={{ fontWeight: 600 }}>
                            {ext.range_15m_low != null && ext.range_15m_high != null
                              ? `${ext.range_15m_low.toFixed(2)} – ${ext.range_15m_high.toFixed(2)}`
                              : '—'}
                          </div>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase' }}>Previous day</span>
                          <div style={{ display: 'flex', gap: '1rem', alignItems: 'baseline', flexWrap: 'wrap' }}>
                            <div>
                              <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>HIGH</span>
                              <div style={{ fontWeight: 600, color: ext.prev_day_high != null ? 'var(--positive)' : 'var(--text-muted)' }}>
                                {ext.prev_day_high != null ? ext.prev_day_high.toFixed(2) : '—'}
                              </div>
                            </div>
                            <div>
                              <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>LOW</span>
                              <div style={{ fontWeight: 600, color: ext.prev_day_low != null ? 'var(--negative)' : 'var(--text-muted)' }}>
                                {ext.prev_day_low != null ? ext.prev_day_low.toFixed(2) : '—'}
                              </div>
                            </div>
                          </div>
                        </div>
                        {ext.cpr_bottom != null && ext.cpr_top != null && (
                          <div>
                            <span style={{ color: 'var(--text-muted)' }}>CPR range</span>
                            <div style={{ fontWeight: 600 }}>
                              <span style={{ color: 'var(--negative)' }}>B {ext.cpr_bottom.toFixed(2)}</span>
                              {' / '}
                              <span style={{ color: 'var(--text-primary)' }}>P {ext.cpr_pivot?.toFixed(2) ?? '—'}</span>
                              {' / '}
                              <span style={{ color: 'var(--positive)' }}>T {ext.cpr_top.toFixed(2)}</span>
                            </div>
                          </div>
                        )}
                        {ext.ema20_5m != null && ext.ema200_5m != null && (
                          <div>
                            <span style={{ color: 'var(--text-muted)' }}>5m: 20 EMA / 200 EMA</span>
                            <div style={{ fontWeight: 600 }}>{ext.ema20_5m.toFixed(2)} / {ext.ema200_5m.toFixed(2)}</div>
                          </div>
                        )}
                        {ext.ema20_15m != null && ext.ema200_15m != null && (
                          <div>
                            <span style={{ color: 'var(--text-muted)' }}>15m: 20 EMA / 200 EMA</span>
                            <div style={{ fontWeight: 600 }}>{ext.ema20_15m.toFixed(2)} / {ext.ema200_15m.toFixed(2)}</div>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })()}
                {(marketNifty?.source === 'live' || marketSensex?.source === 'live') && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--positive)', marginTop: '0.5rem' }}>Live data • refreshes every 15s</div>
                )}
                {marketNifty?.source !== 'live' && marketSensex?.source !== 'live' && (
                  <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                    {backendReachable === false
                      ? 'Backend not reachable. Start the backend (run .\\Start-All.ps1 from project root).'
                      : 'Fetching… (market may be closed)'}
                  </div>
                )}
              </>
            ) : (
              <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Connect Upstox to load NIFTY / SENSEX data.</div>
            )}
          </div>
        </section>

        {/* 2. Trade settings – single row, aligned */}
        <section className="card dashboard-section" style={{ marginBottom: '1.25rem' }}>
          <h2 className="card-title" style={{ marginBottom: '1rem' }}>Trade settings</h2>
          <div className="trade-settings-row">
            <div className="trade-settings-field">
              <label>Index</label>
              <select
                value={selectedIndex}
                onChange={(e) => setSelectedIndex(e.target.value as 'NIFTY' | 'SENSEX')}
                className="trade-settings-input"
              >
                <option value="NIFTY">NIFTY 50</option>
                <option value="SENSEX">SENSEX</option>
              </select>
            </div>
            <div className="trade-settings-field">
              <label>Trading mode</label>
              <select
                value={tradingMode}
                onChange={(e) => handleTradingModeClick(e.target.value as 'MANUAL' | 'SEMI_AUTO' | 'FULL_AUTO')}
                className="trade-settings-input"
              >
                <option value="MANUAL">Manual (signals only)</option>
                <option value="SEMI_AUTO">Semi-Auto (entry + SL)</option>
                <option value="FULL_AUTO">Full-Auto</option>
              </select>
            </div>
            <div className="trade-settings-field">
              <label>Option type</label>
              <select
                value={optionType}
                onChange={(e) => setOptionType(e.target.value as 'CE' | 'PE')}
                className="trade-settings-input"
              >
                <option value="CE">CE (Call)</option>
                <option value="PE">PE (Put)</option>
              </select>
            </div>
            <div className="trade-settings-field">
              <label>Lots</label>
              <input
                type="number"
                min={1}
                max={10}
                value={lots}
                onChange={(e) => {
                  const v = parseInt(e.target.value, 10);
                  if (Number.isFinite(v) && v >= 1 && v <= 10) setLots(v);
                }}
                className="trade-settings-input"
              />
              <span className="trade-settings-hint">Max 1 lot (risk rule)</span>
            </div>
            <div className="trade-settings-field">
              <label>Target premium (₹)</label>
              <input
                type="number"
                min={50}
                max={2000}
                step={10}
                value={selectedIndex === 'NIFTY' ? targetPremiumNifty : targetPremiumSensex}
                onChange={(e) => {
                  const v = parseInt(e.target.value, 10);
                  if (Number.isFinite(v) && v >= 50 && v <= 2000) {
                    if (selectedIndex === 'NIFTY') setTargetPremiumNifty(v);
                    else setTargetPremiumSensex(v);
                  }
                }}
                className="trade-settings-input"
                placeholder={selectedIndex === 'NIFTY' ? '200' : '500'}
              />
              <span className="trade-settings-hint">
                {selectedIndex === 'NIFTY' ? 'NIFTY CE/PE: ~200 (180–220)' : 'SENSEX CE/PE: 500+ (480–520)'}
              </span>
            </div>
            <div className="trade-settings-field">
              <label>Strike (index level)</label>
              <input
                type="number"
                min={selectedIndex === 'NIFTY' ? 20000 : 70000}
                max={selectedIndex === 'NIFTY' ? 30000 : 95000}
                step={100}
                value={selectedIndex === 'NIFTY' ? strikeNifty : strikeSensex}
                onChange={(e) => {
                  const v = parseInt(e.target.value, 10);
                  if (!Number.isFinite(v)) return;
                  const rounded = Math.round(v / 100) * 100;
                  if (selectedIndex === 'NIFTY') {
                    if (rounded >= 20000 && rounded <= 30000) setStrikeNifty(rounded);
                  } else {
                    if (rounded >= 70000 && rounded <= 95000) setStrikeSensex(rounded);
                  }
                }}
                className="trade-settings-input"
                placeholder={selectedIndex === 'NIFTY' ? '25100' : '81200'}
              />
              <span className="trade-settings-hint">
                Multiples of 100 only (e.g. {selectedIndex === 'NIFTY' ? '25100, 25200' : '81200, 81300'})
              </span>
            </div>
          </div>
        </section>

        {/* Consent modal for Semi-Auto / Full-Auto */}
        {modeConsentOpen && pendingMode && (
          <div
            role="dialog"
            aria-modal="true"
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0,0,0,0.7)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000,
              padding: '1rem',
            }}
            onClick={(e) => e.target === e.currentTarget && cancelModeConsent()}
          >
            <div className="card" style={{ maxWidth: 400, padding: '1.5rem' }} onClick={(e) => e.stopPropagation()}>
              <h3 style={{ margin: '0 0 0.75rem 0', fontSize: '1rem' }}>Confirm auto trading</h3>
              <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                {pendingMode === 'FULL_AUTO'
                  ? 'Full-Auto will place and manage orders automatically. You accept the risk of automated execution.'
                  : 'Semi-Auto will place entry and SL orders automatically; you manage exits manually.'}
              </p>
              <p style={{ margin: '0.75rem 0 0 0', fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                By confirming you give consent. This may be logged for audit.
              </p>
              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.25rem' }}>
                <button type="button" className="btn btn-primary" onClick={confirmModeConsent}>
                  I consent, enable
                </button>
                <button type="button" onClick={cancelModeConsent} style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '0.875rem' }}>
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* 3. Trading overview – Summary, Positions, History in one place */}
        <section className="card dashboard-section" style={{ marginBottom: '1.25rem' }}>
          <h2 className="card-title" style={{ marginBottom: '1rem' }}>Trading overview</h2>

          {/* Summary row */}
          <div className="overview-summary-grid">
            <div className="overview-metric">
              <span className="overview-metric-label">Today&apos;s P&L</span>
              <span className="overview-metric-value">— ₹</span>
              <span className="overview-metric-desc">Realized + Unrealized</span>
            </div>
            <div className="overview-metric">
              <span className="overview-metric-label">Trades today</span>
              <span className="overview-metric-value">0 / 3</span>
              <span className="overview-metric-desc">Max 3 per day</span>
            </div>
            <div className="overview-metric">
              <span className="overview-metric-label">Win rate</span>
              <span className="overview-metric-value">—</span>
              <span className="overview-metric-desc">Last 20 trades</span>
            </div>
            <div className="overview-metric">
              <span className="overview-metric-label">Market bias</span>
              <span className="overview-metric-value" style={{ fontSize: '1rem', fontWeight: 600 }}>
                {(selectedIndex === 'NIFTY' ? marketNifty?.bias : marketSensex?.bias) ?? 'NO TRADE'}
              </span>
              <span className="overview-metric-desc">15m EMA20 vs EMA200</span>
            </div>
            <div className="overview-metric">
              <span className="overview-metric-label">Trading mode</span>
              <span className="overview-metric-value" style={{ fontSize: '1rem', fontWeight: 600 }}>
                {tradingMode === 'MANUAL' ? 'Manual' : tradingMode === 'SEMI_AUTO' ? 'Semi-Auto' : 'Full-Auto'}
              </span>
              <span className="overview-metric-desc">
                {tradingMode === 'MANUAL' ? 'Signals only' : tradingMode === 'SEMI_AUTO' ? 'Auto entry + SL' : 'Fully automated'}
              </span>
            </div>
          </div>

          {/* Positions + History in one row */}
          <div className="overview-positions-history">
            <div>
              <h3 style={{ fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)', margin: '0 0 0.75rem 0' }}>Open positions</h3>
              <div className="overview-table-wrap">
                <table className="overview-table">
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th>Type</th>
                      <th>Entry</th>
                      <th>SL</th>
                      <th>TSL</th>
                      <th>P&L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {positions.length === 0 ? (
                      <tr>
                        <td colSpan={6} style={{ color: 'var(--text-muted)', fontSize: '0.8125rem', padding: '1rem', textAlign: 'center' }}>No open positions</td>
                      </tr>
                    ) : (
                      positions.map((p) => (
                        <tr key={p.id}>
                          <td>{p.symbol}</td>
                          <td>{p.option_type}</td>
                          <td>{p.entry_price > 0 ? `₹ ${p.entry_price.toFixed(2)}` : '—'}</td>
                          <td>{p.initial_sl > 0 ? p.initial_sl.toFixed(2) : '—'}</td>
                          <td>{p.sl_trigger > 0 ? p.sl_trigger.toFixed(2) : '—'}</td>
                          <td>—</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
            <div>
              <h3 style={{ fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)', margin: '0 0 0.75rem 0' }}>History</h3>
              <div className="overview-table-wrap">
                <table className="overview-table">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Symbol</th>
                      <th>Event</th>
                      <th>Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.length === 0 ? (
                      <tr>
                        <td colSpan={4} style={{ color: 'var(--text-muted)', fontSize: '0.8125rem', padding: '1rem', textAlign: 'center' }}>No history yet</td>
                      </tr>
                    ) : (
                      history.map((h) => (
                        <tr key={h.id}>
                          <td style={{ whiteSpace: 'nowrap' }}>{new Date(h.at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })}</td>
                          <td>{h.symbol}</td>
                          <td>{h.event_type.replace(/_/g, ' ')}</td>
                          <td>
                            {h.event_type === 'SL_TRAILED' && h.old_sl != null && h.new_sl != null
                              ? `${h.old_sl.toFixed(2)} → ${h.new_sl.toFixed(2)}`
                              : h.details}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </section>

        {/* 3b. Holdings – Intraday opportunities (15m) */}
        <section className="card dashboard-section" style={{ marginBottom: '1.25rem' }}>
          <h2 className="card-title" style={{ marginBottom: '1rem' }}>Holdings • Intraday opportunities (15m)</h2>
          {!upstoxConnected ? (
            <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Connect Upstox to load holdings.</div>
          ) : (
            <div className="overview-table-wrap">
              <table className="overview-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Qty</th>
                    <th>LTP</th>
                    <th>P&L</th>
                    <th>15m opp</th>
                    <th>Reason</th>
                    <th>As of</th>
                  </tr>
                </thead>
                <tbody>
                  {holdingsOpp.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={{ color: 'var(--text-muted)', fontSize: '0.8125rem', padding: '1rem', textAlign: 'center' }}>
                        {holdingsMessage ?? 'No holdings (or Upstox not connected / slow). Try again in 30s.'}
                      </td>
                    </tr>
                  ) : (
                    holdingsOpp.map((h) => {
                      const isSignal = h.status === 'SIGNAL';
                      const dir = h.direction ?? '—';
                      const dirColor = dir === 'BUY' ? 'var(--positive)' : dir === 'SELL' ? 'var(--negative)' : 'var(--text-muted)';
                      return (
                        <tr key={h.instrument_token ?? `${h.tradingsymbol}-${h.isin}`}>
                          <td style={{ whiteSpace: 'nowrap' }}>{h.tradingsymbol ?? '—'}</td>
                          <td>{h.quantity ?? '—'}</td>
                          <td>{typeof h.last_price === 'number' ? `₹ ${h.last_price.toFixed(2)}` : '—'}</td>
                          <td style={{ color: typeof h.pnl === 'number' ? (h.pnl >= 0 ? 'var(--positive)' : 'var(--negative)') : 'var(--text-muted)' }}>
                            {typeof h.pnl === 'number' ? `₹ ${h.pnl.toFixed(2)}` : '—'}
                          </td>
                          <td style={{ fontWeight: 700, color: isSignal ? dirColor : 'var(--text-muted)' }}>
                            {isSignal ? dir : 'NO'}
                          </td>
                          <td style={{ maxWidth: 360 }}>{h.reason ?? '—'}</td>
                          <td style={{ whiteSpace: 'nowrap' }}>{h.last_15m_time ? h.last_15m_time.replace('T', ' ') : '—'}</td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
              <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Logic: EMA20 vs EMA200 on 15m + 15m engulfing pattern alignment. Top 10 holdings by value.
              </div>
            </div>
          )}
        </section>

        {/* 4. Signal panel */}
        <section className="card dashboard-section">
          <h2 className="card-title">Signal panel ({selectedIndex})</h2>
            <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
              Trend-Continuation Capital Preserver. Candlestick (engulfing) + price action (EMAs, CPR, 2m entry). SL/TSL per position.
            </p>
            <div style={{ marginTop: '1rem' }}>
              {signalLoading ? (
                <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>Evaluating…</div>
              ) : signalNifty ? (
                <>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
                    <span
                      className={
                        signalNifty.status === 'BUY'
                          ? 'badge badge-success'
                          : signalNifty.status === 'SELL'
                            ? 'badge badge-error'
                            : 'badge badge-neutral'
                      }
                    >
                      {signalNifty.status}
                    </span>
                    {signalNifty.rejected && signalNifty.rejected_reason && (
                      <span style={{ fontSize: '0.75rem', color: 'var(--negative)' }}>Rejected: {signalNifty.rejected_reason}</span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                    {signalNifty.reason}
                  </div>
                  {signalNifty.risk_checklist.length > 0 && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {signalNifty.risk_checklist.map((r, i) => (
                        <div key={i} style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem' }}>
                          <span style={{ color: r.passed ? 'var(--positive)' : 'var(--text-muted)' }}>{r.passed ? '✓' : '○'}</span>
                          {r.rule}
                          {r.reason && <span>— {r.reason}</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : upstoxConnected ? (
                <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>Connect Upstox and wait for evaluation.</div>
              ) : (
                <span className="badge badge-neutral">No signal</span>
              )}
            </div>
            <div style={{ marginTop: '1.25rem', borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
              <h3 style={{ fontSize: '0.875rem', margin: '0 0 0.5rem 0', color: 'var(--text-secondary)' }}>Signal history</h3>
              {signalHistory.length === 0 ? (
                <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', margin: 0 }}>No signal history yet. Evaluations run every 30s when Upstox is connected.</p>
              ) : (
                <div style={{ maxHeight: 200, overflow: 'auto', fontSize: '0.75rem' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border)' }}>
                        <th style={{ textAlign: 'left', padding: '0.35rem 0.5rem' }}>Time</th>
                        <th style={{ textAlign: 'left', padding: '0.35rem 0.5rem' }}>Symbol</th>
                        <th style={{ textAlign: 'left', padding: '0.35rem 0.5rem' }}>Status</th>
                        <th style={{ textAlign: 'left', padding: '0.35rem 0.5rem' }}>Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {signalHistory.map((s, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                          <td style={{ padding: '0.35rem 0.5rem', color: 'var(--text-secondary)' }}>{s.at ? new Date(s.at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }) : '—'}</td>
                          <td style={{ padding: '0.35rem 0.5rem' }}>{s.symbol}</td>
                          <td style={{ padding: '0.35rem 0.5rem' }}>
                            <span className={s.status === 'BUY' ? 'badge badge-success' : s.status === 'SELL' ? 'badge badge-error' : 'badge badge-neutral'} style={{ fontSize: '0.7rem' }}>{s.status}</span>
                          </td>
                          <td style={{ padding: '0.35rem 0.5rem', color: 'var(--text-muted)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }} title={s.reason}>{s.reason || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
        </section>
      </main>
    </div>
  );
}
