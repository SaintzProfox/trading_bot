'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  AreaChart, Area, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';

// ─── API helpers ─────────────────────────────────────────────────────────────
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function apiFetch(path, opts = {}) {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  const res = await fetch(`${API}${path}`, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...opts.headers,
    },
  });
  if (res.status === 401) { localStorage.removeItem('token'); window.location.reload(); }
  return res.json();
}

// ─── Auth Screen ─────────────────────────────────────────────────────────────
function AuthScreen({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      const data = await apiFetch('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      if (data.access_token) {
        localStorage.setItem('token', data.access_token);
        onLogin(data.user);
      } else {
        setError(data.detail || 'Login failed');
      }
    } catch {
      setError('Connection error');
    }
    setLoading(false);
  }

  return (
    <div style={{
      minHeight: '100vh', background: '#070b14',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: "'IBM Plex Mono', monospace",
    }}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=Syne:wght@700;800&display=swap');`}</style>
      <div style={{ width: 420, padding: '48px 40px', background: '#0d1117', border: '1px solid #1e2d40', borderRadius: 2 }}>
        <div style={{ marginBottom: 40 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <div style={{ width: 8, height: 8, background: '#f0b429', borderRadius: '50%', boxShadow: '0 0 8px #f0b429' }} />
            <span style={{ color: '#f0b429', fontSize: 11, letterSpacing: 3, fontWeight: 600 }}>XAUUSD TRADING SYSTEM</span>
          </div>
          <h1 style={{ color: '#e6edf3', fontFamily: 'Syne', fontSize: 28, fontWeight: 800, margin: 0, letterSpacing: -0.5 }}>
            GOLDBOT
          </h1>
          <p style={{ color: '#6e7681', fontSize: 12, margin: '6px 0 0', letterSpacing: 1 }}>AUTHENTICATED ACCESS ONLY</p>
        </div>

        <form onSubmit={handleSubmit}>
          {[
            { label: 'EMAIL', val: email, set: setEmail, type: 'email' },
            { label: 'PASSWORD', val: password, set: setPassword, type: 'password' },
          ].map(({ label, val, set, type }) => (
            <div key={label} style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', color: '#6e7681', fontSize: 10, letterSpacing: 2, marginBottom: 6 }}>{label}</label>
              <input
                type={type}
                value={val}
                onChange={e => set(e.target.value)}
                style={{
                  width: '100%', padding: '10px 12px', background: '#161b22',
                  border: '1px solid #21262d', borderRadius: 2, color: '#e6edf3',
                  fontFamily: 'inherit', fontSize: 13, boxSizing: 'border-box',
                  outline: 'none',
                }}
              />
            </div>
          ))}
          {error && <p style={{ color: '#f85149', fontSize: 12, margin: '0 0 12px' }}>{error}</p>}
          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%', padding: '11px', background: '#f0b429', border: 'none',
              color: '#070b14', fontFamily: "'Syne', sans-serif", fontWeight: 700,
              fontSize: 13, letterSpacing: 2, cursor: 'pointer', borderRadius: 2,
              marginTop: 8,
            }}
          >
            {loading ? 'AUTHENTICATING...' : 'ACCESS DASHBOARD →'}
          </button>
        </form>
      </div>
    </div>
  );
}

// ─── Stat Card ───────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, color = '#e6edf3', glow }) {
  return (
    <div style={{
      background: '#0d1117', border: '1px solid #1e2d40', borderRadius: 2,
      padding: '20px 22px', flex: 1, minWidth: 140,
    }}>
      <div style={{ color: '#6e7681', fontSize: 10, letterSpacing: 2, marginBottom: 8 }}>{label}</div>
      <div style={{ color, fontSize: 26, fontFamily: "'Syne', sans-serif", fontWeight: 800, letterSpacing: -0.5,
        textShadow: glow ? `0 0 16px ${color}55` : 'none'
      }}>{value}</div>
      {sub && <div style={{ color: '#6e7681', fontSize: 11, marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

// ─── Trade Row ───────────────────────────────────────────────────────────────
function TradeRow({ trade }) {
  const pnl = trade.pnl ?? 0;
  const isOpen = trade.status === 'open';
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '80px 50px 70px 80px 80px 80px 90px 80px',
      gap: 8, padding: '10px 0', borderBottom: '1px solid #161b22',
      fontSize: 11, fontFamily: "'IBM Plex Mono', monospace", alignItems: 'center',
    }}>
      <span style={{ color: '#6e7681' }}>{new Date(trade.opened_at).toLocaleDateString()}</span>
      <span style={{
        color: trade.action === 'BUY' ? '#39d353' : '#f85149',
        fontWeight: 600, letterSpacing: 1
      }}>{trade.action}</span>
      <span style={{ color: '#e6edf3' }}>{trade.symbol}</span>
      <span style={{ color: '#8b949e' }}>{Number(trade.entry_price).toFixed(2)}</span>
      <span style={{ color: '#8b949e' }}>{trade.exit_price ? Number(trade.exit_price).toFixed(2) : '—'}</span>
      <span style={{ color: '#8b949e' }}>{trade.lot_size}</span>
      <span style={{ color: pnl >= 0 ? '#39d353' : '#f85149', fontWeight: 600 }}>
        {pnl >= 0 ? '+' : ''}{Number(pnl).toFixed(2)}
      </span>
      <span style={{
        padding: '2px 8px', borderRadius: 2, fontSize: 10, letterSpacing: 1,
        background: isOpen ? '#1a2e20' : '#1c1c1c',
        color: isOpen ? '#39d353' : '#6e7681',
        border: `1px solid ${isOpen ? '#39d353' : '#21262d'}`,
      }}>{trade.status.toUpperCase()}</span>
    </div>
  );
}

// ─── Settings Panel ──────────────────────────────────────────────────────────
function SettingsPanel({ settings, defaults, onSave, saving }) {
  const [local, setLocal] = useState({});

  useEffect(() => {
    const init = {};
    if (settings) Object.entries(settings).forEach(([k, v]) => { init[k] = v.value; });
    setLocal(init);
  }, [settings]);

  const inputStyle = {
    background: '#161b22', border: '1px solid #21262d', borderRadius: 2,
    color: '#e6edf3', fontFamily: "'IBM Plex Mono', monospace", fontSize: 12,
    padding: '7px 10px', width: '100%', boxSizing: 'border-box',
  };

  const groups = [
    { title: 'RISK MANAGEMENT', keys: ['risk_percent', 'max_daily_loss', 'max_open_trades'] },
    { title: 'RSI PARAMETERS', keys: ['rsi_period', 'rsi_overbought', 'rsi_oversold'] },
    { title: 'MOVING AVERAGES', keys: ['fast_ma', 'slow_ma'] },
    { title: 'ATR & EXECUTION', keys: ['atr_period', 'atr_multiplier_sl', 'atr_multiplier_tp', 'timeframe'] },
    { title: 'ML FILTER', keys: ['use_ml_filter', 'ml_confidence_threshold'] },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
      {groups.map(({ title, keys }) => (
        <div key={title} style={{ background: '#0d1117', border: '1px solid #1e2d40', padding: 20, borderRadius: 2 }}>
          <div style={{ color: '#f0b429', fontSize: 10, letterSpacing: 2, marginBottom: 16, fontWeight: 600 }}>{title}</div>
          {keys.map(key => {
            const def = defaults?.[key] || {};
            return (
              <div key={key} style={{ marginBottom: 12 }}>
                <label style={{ display: 'block', color: '#6e7681', fontSize: 10, letterSpacing: 1.5, marginBottom: 4 }}>
                  {key.toUpperCase().replace(/_/g, ' ')}
                </label>
                {def.options ? (
                  <select value={local[key] || ''} onChange={e => setLocal(p => ({ ...p, [key]: e.target.value }))} style={inputStyle}>
                    {def.options.map(o => <option key={o} value={o}>{o}</option>)}
                  </select>
                ) : typeof def.value === 'boolean' || key === 'use_ml_filter' ? (
                  <select value={String(local[key] ?? def.value)} onChange={e => setLocal(p => ({ ...p, [key]: e.target.value === 'true' }))} style={inputStyle}>
                    <option value="true">ENABLED</option>
                    <option value="false">DISABLED</option>
                  </select>
                ) : (
                  <input
                    type="number"
                    step={String(def.value).includes('.') ? '0.01' : '1'}
                    min={def.min} max={def.max}
                    value={local[key] ?? ''}
                    onChange={e => setLocal(p => ({ ...p, [key]: parseFloat(e.target.value) || e.target.value }))}
                    style={inputStyle}
                  />
                )}
              </div>
            );
          })}
        </div>
      ))}
      <div style={{ gridColumn: '1/-1', display: 'flex', justifyContent: 'flex-end' }}>
        <button
          onClick={() => onSave(local)}
          disabled={saving}
          style={{
            padding: '10px 28px', background: '#f0b429', border: 'none', borderRadius: 2,
            color: '#070b14', fontFamily: "'Syne', sans-serif", fontWeight: 700,
            fontSize: 12, letterSpacing: 2, cursor: 'pointer',
          }}
        >
          {saving ? 'SAVING...' : 'SAVE SETTINGS →'}
        </button>
      </div>
    </div>
  );
}

// ─── Backtest Panel ──────────────────────────────────────────────────────────
function BacktestPanel() {
  const [params, setParams] = useState({ start_date: '2022-01-01', end_date: '2024-01-01', initial_balance: 10000, risk_percent: 1.0, fast_ma: 20, slow_ma: 50 });
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);

  async function run() {
    setRunning(true); setResult(null);
    const data = await apiFetch('/api/backtest/run', { method: 'POST', body: JSON.stringify(params) });
    setResult(data);
    setRunning(false);
  }

  const inputS = { background: '#161b22', border: '1px solid #21262d', borderRadius: 2, color: '#e6edf3', fontFamily: "'IBM Plex Mono',monospace", fontSize: 12, padding: '7px 10px', width: '100%', boxSizing: 'border-box' };

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 16, marginBottom: 24 }}>
        {Object.entries(params).map(([k, v]) => (
          <div key={k}>
            <label style={{ display: 'block', color: '#6e7681', fontSize: 10, letterSpacing: 1.5, marginBottom: 4 }}>{k.toUpperCase().replace(/_/g, ' ')}</label>
            <input type={k.includes('date') ? 'date' : 'number'} value={v} onChange={e => setParams(p => ({ ...p, [k]: e.target.value }))} style={inputS} />
          </div>
        ))}
      </div>
      <button onClick={run} disabled={running} style={{ padding: '10px 28px', background: '#1f6feb', border: 'none', borderRadius: 2, color: '#fff', fontFamily: "'Syne',sans-serif", fontWeight: 700, fontSize: 12, letterSpacing: 2, cursor: 'pointer', marginBottom: 24 }}>
        {running ? 'RUNNING BACKTEST...' : 'RUN BACKTEST →'}
      </button>

      {result && !result.error && (
        <div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 24 }}>
            {[
              ['TOTAL TRADES', result.total_trades],
              ['WIN RATE', `${result.win_rate}%`],
              ['TOTAL P&L', `$${result.total_pnl}`, result.total_pnl >= 0 ? '#39d353' : '#f85149'],
              ['PROFIT FACTOR', result.profit_factor],
              ['MAX DRAWDOWN', `${result.max_drawdown_pct}%`, '#f85149'],
              ['SHARPE RATIO', result.sharpe_ratio],
              ['RETURN', `${result.return_pct}%`, result.return_pct >= 0 ? '#39d353' : '#f85149'],
            ].map(([l, v, c]) => <StatCard key={l} label={l} value={v} color={c} />)}
          </div>

          {result.equity_curve?.length > 0 && (
            <div style={{ background: '#0d1117', border: '1px solid #1e2d40', padding: 20, borderRadius: 2 }}>
              <div style={{ color: '#f0b429', fontSize: 10, letterSpacing: 2, marginBottom: 16 }}>EQUITY CURVE</div>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={result.equity_curve.map((v, i) => ({ i, equity: v }))}>
                  <defs>
                    <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#1f6feb" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#1f6feb" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#161b22" />
                  <XAxis dataKey="i" hide />
                  <YAxis stroke="#6e7681" tick={{ fill: '#6e7681', fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: '#0d1117', border: '1px solid #1e2d40', borderRadius: 2, color: '#e6edf3', fontSize: 11 }} formatter={v => [`$${v.toFixed(2)}`, 'Equity']} />
                  <Area type="monotone" dataKey="equity" stroke="#1f6feb" fill="url(#eq)" strokeWidth={2} dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
      {result?.error && <div style={{ color: '#f85149', padding: 16, background: '#1c1010', border: '1px solid #f8514933', borderRadius: 2 }}>Error: {result.error}</div>}
    </div>
  );
}

// ─── Credentials Panel ───────────────────────────────────────────────────────
function CredentialsPanel({ credentials, onSave, saving, isAdmin }) {
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [server, setServer] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [feedback, setFeedback] = useState(null);

  useEffect(() => {
    if (credentials) {
      setLogin(credentials.mt5_login || '');
      setServer(credentials.mt5_server || '');
      // password is never sent back to client
    }
  }, [credentials]);

  async function handleSave() {
    if (!login || !server) { setFeedback({ ok: false, msg: 'Login and Server are required.' }); return; }
    setFeedback(null);
    const payload = { mt5_login: login, mt5_server: server };
    if (password) payload.mt5_password = password;
    const res = await onSave(payload);
    if (res?.message) setFeedback({ ok: true, msg: res.message });
    else setFeedback({ ok: false, msg: res?.detail || 'Save failed.' });
    setPassword('');
  }

  const inputS = {
    background: '#161b22', border: '1px solid #21262d', borderRadius: 2,
    color: '#e6edf3', fontFamily: "'IBM Plex Mono', monospace", fontSize: 13,
    padding: '10px 12px', width: '100%', boxSizing: 'border-box',
  };
  const labelS = { display: 'block', color: '#6e7681', fontSize: 10, letterSpacing: 2, marginBottom: 6 };

  const knownServers = [
    'HFMarkets-Demo', 'HFMarkets-Live01', 'HFMarkets-Live02',
    'HFMarkets-Live03', 'HFMarkets-Live04',
  ];

  return (
    <div style={{ maxWidth: 560 }}>
      {/* Warning banner */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', padding: '14px 16px', background: '#161205', border: '1px solid #f0b42933', borderRadius: 2, marginBottom: 28 }}>
        <span style={{ fontSize: 16 }}>⚠️</span>
        <div>
          <div style={{ color: '#f0b429', fontSize: 11, fontWeight: 600, letterSpacing: 1, marginBottom: 4 }}>ADMIN ONLY — SENSITIVE CREDENTIALS</div>
          <div style={{ color: '#8b949e', fontSize: 11, lineHeight: 1.6 }}>
            Credentials are AES-256 encrypted at rest. The password is write-only — it is never returned to the UI.
            Saving will automatically restart the bot to apply changes.
          </div>
        </div>
      </div>

      {!isAdmin && (
        <div style={{ color: '#f85149', fontSize: 12, padding: '12px 16px', background: '#200e0e', border: '1px solid #f8514933', borderRadius: 2, marginBottom: 20 }}>
          🔒 Admin role required to view or edit MT5 credentials.
        </div>
      )}

      <div style={{ background: '#0d1117', border: '1px solid #1e2d40', borderRadius: 2, padding: '28px 28px 24px' }}>
        <div style={{ color: '#f0b429', fontSize: 10, letterSpacing: 2, marginBottom: 24, fontWeight: 600 }}>MT5 / HFM BROKER CREDENTIALS</div>

        {/* MT5 Login */}
        <div style={{ marginBottom: 18 }}>
          <label style={labelS}>MT5 ACCOUNT LOGIN</label>
          <input
            type="number"
            value={login}
            onChange={e => setLogin(e.target.value)}
            placeholder="e.g. 12345678"
            disabled={!isAdmin}
            style={{ ...inputS, opacity: isAdmin ? 1 : 0.5 }}
          />
          <div style={{ color: '#6e7681', fontSize: 10, marginTop: 4 }}>Your HFM account number</div>
        </div>

        {/* MT5 Password */}
        <div style={{ marginBottom: 18 }}>
          <label style={labelS}>MT5 PASSWORD {credentials?.has_password && <span style={{ color: '#39d353', marginLeft: 6 }}>● SET</span>}</label>
          <div style={{ position: 'relative' }}>
            <input
              type={showPw ? 'text' : 'password'}
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder={credentials?.has_password ? '(leave blank to keep current)' : 'Enter MT5 password'}
              disabled={!isAdmin}
              style={{ ...inputS, paddingRight: 44, opacity: isAdmin ? 1 : 0.5 }}
            />
            <button
              onClick={() => setShowPw(p => !p)}
              style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: '#6e7681', cursor: 'pointer', fontSize: 13 }}
            >
              {showPw ? '🙈' : '👁'}
            </button>
          </div>
          <div style={{ color: '#6e7681', fontSize: 10, marginTop: 4 }}>Write-only — never echoed back</div>
        </div>

        {/* MT5 Server */}
        <div style={{ marginBottom: 28 }}>
          <label style={labelS}>MT5 SERVER</label>
          <input
            list="server-options"
            value={server}
            onChange={e => setServer(e.target.value)}
            placeholder="e.g. HFMarkets-Demo"
            disabled={!isAdmin}
            style={{ ...inputS, opacity: isAdmin ? 1 : 0.5 }}
          />
          <datalist id="server-options">
            {knownServers.map(s => <option key={s} value={s} />)}
          </datalist>
          <div style={{ color: '#6e7681', fontSize: 10, marginTop: 4 }}>
            Demo: <span style={{ color: '#e6edf3' }}>HFMarkets-Demo</span> &nbsp;·&nbsp;
            Live: <span style={{ color: '#e6edf3' }}>HFMarkets-Live01</span> through <span style={{ color: '#e6edf3' }}>Live04</span>
          </div>
        </div>

        {/* Current state display */}
        {credentials && (
          <div style={{ display: 'flex', gap: 8, marginBottom: 24, flexWrap: 'wrap' }}>
            {[
              ['CURRENT LOGIN', credentials.mt5_login || '—'],
              ['SERVER', credentials.mt5_server || '—'],
              ['PASSWORD', credentials.has_password ? '••••••••' : 'NOT SET'],
              ['LAST UPDATED', credentials.updated_at ? new Date(credentials.updated_at).toLocaleDateString() : '—'],
            ].map(([l, v]) => (
              <div key={l} style={{ flex: 1, minWidth: 100, background: '#161b22', border: '1px solid #21262d', borderRadius: 2, padding: '10px 12px' }}>
                <div style={{ color: '#6e7681', fontSize: 9, letterSpacing: 1.5, marginBottom: 4 }}>{l}</div>
                <div style={{ color: '#e6edf3', fontSize: 12 }}>{v}</div>
              </div>
            ))}
          </div>
        )}

        {/* Feedback */}
        {feedback && (
          <div style={{ padding: '10px 14px', borderRadius: 2, marginBottom: 16, fontSize: 12,
            background: feedback.ok ? '#0e2016' : '#200e0e',
            border: `1px solid ${feedback.ok ? '#39d35333' : '#f8514933'}`,
            color: feedback.ok ? '#39d353' : '#f85149',
          }}>
            {feedback.ok ? '✓' : '✗'} {feedback.msg}
          </div>
        )}

        <button
          onClick={handleSave}
          disabled={saving || !isAdmin}
          style={{
            padding: '11px 28px', background: isAdmin ? '#f0b429' : '#1c1c1c',
            border: 'none', borderRadius: 2, color: isAdmin ? '#070b14' : '#6e7681',
            fontFamily: "'Syne', sans-serif", fontWeight: 700, fontSize: 12,
            letterSpacing: 2, cursor: isAdmin ? 'pointer' : 'not-allowed',
          }}
        >
          {saving ? 'SAVING...' : '🔐 SAVE & RESTART BOT →'}
        </button>
      </div>
    </div>
  );
}

// ─── Main Dashboard ──────────────────────────────────────────────────────────
export default function Dashboard() {
  const [user, setUser] = useState(null);
  const [tab, setTab] = useState('overview');
  const [botStatus, setBotStatus] = useState('stopped');
  const [metrics, setMetrics] = useState({});
  const [trades, setTrades] = useState([]);
  const [equityData, setEquityData] = useState([]);
  const [settings, setSettings] = useState(null);
  const [settingDefaults, setSettingDefaults] = useState(null);
  const [savingSettings, setSavingSettings] = useState(false);
  const [botLoading, setBotLoading] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [credentials, setCredentials] = useState(null);
  const [credLoading, setCredLoading] = useState(false);
  const wsRef = useRef(null);

  // ── Init ──
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        setUser({ email: payload.email, role: payload.role });
      } catch { localStorage.removeItem('token'); }
    }
  }, []);

  // ── WebSocket ──
  useEffect(() => {
    if (!user) return;
    const token = localStorage.getItem('token');
    const wsUrl = `${API.replace('http', 'ws')}/ws?token=${token}`;
    const ws = new WebSocket(wsUrl);
    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);
    ws.onmessage = e => {
      const data = JSON.parse(e.data);
      if (data.type === 'heartbeat') {
        setBotStatus(data.bot_status || 'stopped');
        if (data.metrics) setMetrics(data.metrics);
      }
    };
    wsRef.current = ws;
    return () => ws.close();
  }, [user]);

  // ── Fetch data ──
  const fetchAll = useCallback(async () => {
    if (!user) return;
    const [tradesData, metricsData, settingsData, defaultsData, credsData] = await Promise.all([
      apiFetch('/api/trades/?limit=50'),
      apiFetch('/api/metrics/summary'),
      apiFetch('/api/settings/'),
      apiFetch('/api/settings/defaults'),
      apiFetch('/api/credentials/'),
    ]);
    if (tradesData.trades) setTrades(tradesData.trades);
    if (metricsData.equity_curve) {
      setEquityData(metricsData.equity_curve.map(d => ({ ...d, cumPnl: d.pnl })));
      setMetrics(prev => ({ ...prev, ...metricsData }));
    }
    setSettings(settingsData);
    setSettingDefaults(defaultsData);
    if (!credsData.detail) setCredentials(credsData);
  }, [user]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  async function toggleBot() {
    setBotLoading(true);
    const action = botStatus === 'running' ? 'stop' : 'start';
    await apiFetch(`/api/bot/${action}`, { method: 'POST' });
    setBotLoading(false);
  }

  async function saveSettings(vals) {
    setSavingSettings(true);
    await apiFetch('/api/settings/', { method: 'PUT', body: JSON.stringify({ settings: vals }) });
    setSavingSettings(false);
    await fetchAll();
  }

  async function saveCredentials(vals) {
    setCredLoading(true);
    const res = await apiFetch('/api/credentials/', { method: 'PUT', body: JSON.stringify(vals) });
    setCredLoading(false);
    if (!res.error) await fetchAll();
    return res;
  }

  if (!user) return <AuthScreen onLogin={u => { setUser(u); fetchAll(); }} />;

  const isRunning = botStatus === 'running';
  const tabs = ['overview', 'trades', 'settings', 'credentials', 'backtest'];

  // Build cumulative equity from daily data
  let cum = 0;
  const cumulativeEquity = equityData.map(d => { cum += d.cumPnl; return { ...d, cumulative: cum }; });

  return (
    <div style={{ minHeight: '100vh', background: '#070b14', color: '#e6edf3', fontFamily: "'IBM Plex Mono', monospace" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=Syne:wght@700;800&display=swap');
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 4px; background: #0d1117; }
        ::-webkit-scrollbar-thumb { background: #21262d; }
        input, select { outline: none; }
        input:focus, select:focus { border-color: #1f6feb !important; }
      `}</style>

      {/* ── Header ── */}
      <header style={{ borderBottom: '1px solid #1e2d40', padding: '0 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 56, position: 'sticky', top: 0, background: '#070b14', zIndex: 100 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 8, height: 8, background: '#f0b429', borderRadius: '50%', boxShadow: '0 0 8px #f0b429' }} />
            <span style={{ fontFamily: "'Syne', sans-serif", fontWeight: 800, fontSize: 15, letterSpacing: 1, color: '#f0b429' }}>GOLDBOT</span>
          </div>
          <span style={{ color: '#21262d' }}>|</span>
          <span style={{ color: '#6e7681', fontSize: 11, letterSpacing: 2 }}>XAUUSD · HFM BROKER</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          {/* WS indicator */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: wsConnected ? '#39d353' : '#6e7681', boxShadow: wsConnected ? '0 0 6px #39d353' : 'none' }} />
            <span style={{ fontSize: 10, color: '#6e7681', letterSpacing: 1 }}>{wsConnected ? 'LIVE' : 'OFFLINE'}</span>
          </div>

          {/* Bot toggle */}
          <button
            onClick={toggleBot}
            disabled={botLoading}
            style={{
              padding: '6px 16px', borderRadius: 2, border: `1px solid ${isRunning ? '#f85149' : '#39d353'}`,
              background: isRunning ? '#200e0e' : '#0e2016', color: isRunning ? '#f85149' : '#39d353',
              fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, letterSpacing: 1.5, cursor: 'pointer',
            }}
          >
            {botLoading ? '...' : isRunning ? '⏹ STOP BOT' : '▶ START BOT'}
          </button>

          <div style={{ color: '#6e7681', fontSize: 11 }}>{user.email}</div>
          <button onClick={() => { localStorage.removeItem('token'); setUser(null); }} style={{ background: 'none', border: 'none', color: '#6e7681', cursor: 'pointer', fontSize: 11 }}>LOGOUT</button>
        </div>
      </header>

      {/* ── Tabs ── */}
      <nav style={{ borderBottom: '1px solid #1e2d40', padding: '0 32px', display: 'flex', gap: 0 }}>
        {tabs.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: '14px 20px', background: 'none', border: 'none', borderBottom: `2px solid ${tab === t ? '#f0b429' : 'transparent'}`,
              color: tab === t ? '#f0b429' : '#6e7681', fontFamily: "'IBM Plex Mono', monospace",
              fontSize: 11, letterSpacing: 2, cursor: 'pointer', textTransform: 'uppercase',
            }}
          >
            {t}
          </button>
        ))}
      </nav>

      <main style={{ padding: '28px 32px', maxWidth: 1400, margin: '0 auto' }}>

        {/* ── OVERVIEW ── */}
        {tab === 'overview' && (
          <div>
            {/* Bot status bar */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24, padding: '12px 18px', background: '#0d1117', border: '1px solid #1e2d40', borderRadius: 2 }}>
              <div style={{ width: 10, height: 10, borderRadius: '50%', background: isRunning ? '#39d353' : '#6e7681', boxShadow: isRunning ? '0 0 10px #39d353' : 'none', animation: isRunning ? 'pulse 2s infinite' : 'none' }} />
              <span style={{ color: isRunning ? '#39d353' : '#6e7681', fontSize: 12, letterSpacing: 2, fontWeight: 600 }}>
                BOT {isRunning ? 'RUNNING' : 'STOPPED'}
              </span>
              {metrics.updated_at && <span style={{ color: '#6e7681', fontSize: 10, marginLeft: 'auto' }}>Updated: {new Date(metrics.updated_at).toLocaleTimeString()}</span>}
            </div>
            <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }`}</style>

            {/* Stats row */}
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 24 }}>
              <StatCard label="BALANCE" value={`$${Number(metrics.balance || 0).toLocaleString('en', { minimumFractionDigits: 2 })}`} />
              <StatCard label="EQUITY" value={`$${Number(metrics.equity || 0).toLocaleString('en', { minimumFractionDigits: 2 })}`} color="#1f6feb" />
              <StatCard label="DAILY P&L" value={`${(metrics.daily_pnl || 0) >= 0 ? '+' : ''}$${Number(metrics.daily_pnl || 0).toFixed(2)}`} color={(metrics.daily_pnl || 0) >= 0 ? '#39d353' : '#f85149'} glow />
              <StatCard label="TOTAL P&L" value={`${(metrics.total_pnl || 0) >= 0 ? '+' : ''}$${Number(metrics.total_pnl || 0).toFixed(2)}`} color={(metrics.total_pnl || 0) >= 0 ? '#39d353' : '#f85149'} />
              <StatCard label="WIN RATE" value={`${metrics.win_rate || 0}%`} color="#f0b429" />
              <StatCard label="PROFIT FACTOR" value={metrics.profit_factor || '—'} />
              <StatCard label="MAX DRAWDOWN" value={`${metrics.max_drawdown_pct || 0}%`} color="#f85149" />
              <StatCard label="OPEN TRADES" value={metrics.open_trades || 0} color="#8b949e" />
            </div>

            {/* Charts row */}
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20, marginBottom: 20 }}>
              {/* Equity curve */}
              <div style={{ background: '#0d1117', border: '1px solid #1e2d40', padding: 20, borderRadius: 2 }}>
                <div style={{ color: '#f0b429', fontSize: 10, letterSpacing: 2, marginBottom: 16 }}>EQUITY CURVE</div>
                <ResponsiveContainer width="100%" height={220}>
                  <AreaChart data={cumulativeEquity}>
                    <defs>
                      <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#f0b429" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="#f0b429" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#161b22" />
                    <XAxis dataKey="date" tick={{ fill: '#6e7681', fontSize: 9 }} tickLine={false} />
                    <YAxis stroke="#6e7681" tick={{ fill: '#6e7681', fontSize: 9 }} />
                    <Tooltip contentStyle={{ background: '#0d1117', border: '1px solid #1e2d40', fontSize: 11 }} formatter={v => [`$${Number(v).toFixed(2)}`, 'Cumulative P&L']} />
                    <ReferenceLine y={0} stroke="#21262d" strokeDasharray="4 4" />
                    <Area type="monotone" dataKey="cumulative" stroke="#f0b429" fill="url(#eqGrad)" strokeWidth={2} dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              {/* Daily P&L bars */}
              <div style={{ background: '#0d1117', border: '1px solid #1e2d40', padding: 20, borderRadius: 2 }}>
                <div style={{ color: '#f0b429', fontSize: 10, letterSpacing: 2, marginBottom: 16 }}>DAILY P&L (LAST 30)</div>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={equityData.slice(-30)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#161b22" vertical={false} />
                    <XAxis dataKey="date" tick={{ fill: '#6e7681', fontSize: 8 }} tickLine={false} />
                    <YAxis tick={{ fill: '#6e7681', fontSize: 9 }} />
                    <Tooltip contentStyle={{ background: '#0d1117', border: '1px solid #1e2d40', fontSize: 11 }} formatter={v => [`$${Number(v).toFixed(2)}`, 'P&L']} />
                    <ReferenceLine y={0} stroke="#21262d" />
                    <Bar dataKey="pnl" fill="#39d353" radius={[2, 2, 0, 0]}
                      label={false}
                      isAnimationActive={false}
                      style={{ fill: 'var(--bar-color)' }}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Recent trades */}
            <div style={{ background: '#0d1117', border: '1px solid #1e2d40', padding: 20, borderRadius: 2 }}>
              <div style={{ color: '#f0b429', fontSize: 10, letterSpacing: 2, marginBottom: 12 }}>RECENT TRADES</div>
              <div style={{ color: '#6e7681', fontSize: 10, letterSpacing: 1, display: 'grid', gridTemplateColumns: '80px 50px 70px 80px 80px 80px 90px 80px', gap: 8, paddingBottom: 8, borderBottom: '1px solid #1e2d40' }}>
                {['DATE', 'SIDE', 'SYMBOL', 'ENTRY', 'EXIT', 'LOTS', 'P&L', 'STATUS'].map(h => <span key={h}>{h}</span>)}
              </div>
              {trades.slice(0, 10).map((t, i) => <TradeRow key={t.id || i} trade={t} />)}
              {trades.length === 0 && <div style={{ color: '#6e7681', textAlign: 'center', padding: '24px 0', fontSize: 12 }}>No trades yet</div>}
            </div>
          </div>
        )}

        {/* ── TRADES ── */}
        {tab === 'trades' && (
          <div style={{ background: '#0d1117', border: '1px solid #1e2d40', padding: 20, borderRadius: 2 }}>
            <div style={{ color: '#f0b429', fontSize: 10, letterSpacing: 2, marginBottom: 12 }}>FULL TRADE HISTORY</div>
            <div style={{ color: '#6e7681', fontSize: 10, letterSpacing: 1, display: 'grid', gridTemplateColumns: '80px 50px 70px 80px 80px 80px 90px 80px', gap: 8, paddingBottom: 8, borderBottom: '1px solid #1e2d40' }}>
              {['DATE', 'SIDE', 'SYMBOL', 'ENTRY', 'EXIT', 'LOTS', 'P&L', 'STATUS'].map(h => <span key={h}>{h}</span>)}
            </div>
            {trades.map((t, i) => <TradeRow key={t.id || i} trade={t} />)}
            {trades.length === 0 && <div style={{ color: '#6e7681', textAlign: 'center', padding: '40px 0', fontSize: 12 }}>No trades found</div>}
          </div>
        )}

        {/* ── SETTINGS ── */}
        {tab === 'settings' && (
          <div>
            <div style={{ marginBottom: 20, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ color: '#f0b429', fontSize: 10, letterSpacing: 2, marginBottom: 4 }}>STRATEGY CONFIGURATION</div>
                <div style={{ color: '#6e7681', fontSize: 12 }}>Changes apply to the next trading cycle automatically.</div>
              </div>
            </div>
            <SettingsPanel settings={settings} defaults={settingDefaults} onSave={saveSettings} saving={savingSettings} />
          </div>
        )}

        {/* ── CREDENTIALS ── */}
        {tab === 'credentials' && (
          <div>
            <div style={{ marginBottom: 20 }}>
              <div style={{ color: '#f0b429', fontSize: 10, letterSpacing: 2, marginBottom: 4 }}>BROKER CREDENTIALS</div>
              <div style={{ color: '#6e7681', fontSize: 12 }}>MT5 / HFM connection settings. Stored encrypted — never logged.</div>
            </div>
            <CredentialsPanel
              credentials={credentials}
              onSave={saveCredentials}
              saving={credLoading}
              isAdmin={user?.role === 'admin'}
            />
          </div>
        )}

        {/* ── BACKTEST ── */}
        {tab === 'backtest' && (
          <div>
            <div style={{ marginBottom: 20 }}>
              <div style={{ color: '#f0b429', fontSize: 10, letterSpacing: 2, marginBottom: 4 }}>STRATEGY BACKTESTER</div>
              <div style={{ color: '#6e7681', fontSize: 12 }}>Historical simulation using XAUUSD (GC=F) data from Yahoo Finance.</div>
            </div>
            <BacktestPanel />
          </div>
        )}
      </main>
    </div>
  );
}
