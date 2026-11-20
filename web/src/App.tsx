import { useCallback, useEffect, useState } from 'react';
import { Activity, ArrowDown, ArrowUp, Bell, CircleDot, Cpu, HardDrive, LayoutDashboard, LogOut, MemoryStick, RefreshCw, Server, ShieldCheck } from 'lucide-react';
import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

type Machine = { node_id: string; hostname: string; last_seen: number; online: boolean; cpu: number; memory: number; disk: number; memory_bytes: number; disk_bytes: number; rx_bytes: number; tx_bytes: number; uptime_seconds: number };
type Sample = { ts: number; cpu: number; memory: number; disk: number };
type Alert = { node_id: string; metric: string; severity: string; message: string };
type View = 'overview' | 'alerts';

const size = (bytes = 0) => {
  if (!Number.isFinite(bytes)) return '—';
  if (bytes < 1024) return Math.round(bytes) + ' B';
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), 4);
  return (bytes / 1024 ** exponent).toFixed(1) + ' ' + (['B', 'KB', 'MB', 'GB', 'TB'][exponent]);
};
const pct = (number?: number) => Number.isFinite(number) ? Math.round(number!) + '%' : '—';

export default function App() {
  const [tokenField, setTokenField] = useState('');
  const [token, setToken] = useState('');
  const [machines, setMachines] = useState<Machine[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selected, setSelected] = useState('');
  const [history, setHistory] = useState<Sample[]>([]);
  const [view, setView] = useState<View>('overview');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const request = useCallback(async (path: string) => {
    const result = await fetch(path, { headers: { Authorization: 'Bearer ' + token }, cache: 'no-store' });
    if (!result.ok) throw new Error(result.status === 401 ? 'Invalid administrator token' : 'API error (' + result.status + ')');
    return result.json();
  }, [token]);

  const refresh = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [systemData, alertData] = await Promise.all([request('/api/v1/systems'), request('/api/v1/alerts')]);
      setMachines(systemData.systems);
      setAlerts(alertData.alerts);
      setSelected(current => current && systemData.systems.some((m: Machine) => m.node_id === current)
        ? current : systemData.systems[0]?.node_id ?? '');
      setLastRefresh(new Date());
      setError('');
    } catch (e) { setError(e instanceof Error ? e.message : 'Connection failed'); }
    finally { setLoading(false); }
  }, [request, token]);

  useEffect(() => {
    if (!token) return;
    void refresh();
    const interval = window.setInterval(() => { void refresh(); }, 15000);
    return () => window.clearInterval(interval);
  }, [refresh, token]);

  useEffect(() => {
    if (!token || !selected) { setHistory([]); return; }
    let active = true;
    void request('/api/v1/systems/' + encodeURIComponent(selected) + '/history?hours=24')
      .then(data => { if (active) setHistory(data.samples); })
      .catch(() => { if (active) setHistory([]); });
    return () => { active = false; };
  }, [selected, request, lastRefresh, token]);

  const machine = machines.find(m => m.node_id === selected);
  const online = machines.filter(m => m.online).length;

  if (!token) {
    return <main className="login-screen">
      <section className="login-card">
        <span className="brand-icon"><Activity size={28} aria-hidden="true" /></span>
        <div className="eyebrow">GOREECLOUD / OBSERVABILITY</div>
        <h1>See every system.<br /><span>Know what matters.</span></h1>
        <p>Sign in to your private Metrics hub. The access token is held in memory only, never saved to browser storage.</p>
        <form onSubmit={e => { e.preventDefault(); if (tokenField.trim()) setToken(tokenField.trim()); }}>
          <label htmlFor="admin-token">Administrator access token</label>
          <input id="admin-token" type="password" autoComplete="off" value={tokenField}
            onChange={e => setTokenField(e.target.value)} placeholder="Enter your administrator token" required minLength={32} />
          <button className="primary" type="submit">Connect to hub <ArrowUp size={17} aria-hidden="true" /></button>
        </form>
        <div className="login-note"><ShieldCheck size={16} /> Self-hosted • No third-party telemetry</div>
      </section>
    </main>;
  }

  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-icon"><Activity size={23} /></span><span>GoreeCloud <strong>Metrics</strong><small>CONTROL CENTER</small></span></div>
      <div className="sidebar-section">WORKSPACE</div>
      <nav aria-label="Main navigation">
        <button type="button" className={view === 'overview' ? 'nav active' : 'nav'} onClick={() => setView('overview')}><LayoutDashboard size={19}/> Overview</button>
        <button type="button" className={view === 'alerts' ? 'nav active' : 'nav'} onClick={() => setView('alerts')}><Bell size={19}/> Alerts {alerts.length > 0 && <b>{alerts.length}</b>}</button>
      </nav>
      <div className="sidebar-bottom">
        <span className="sidebar-status"><CircleDot size={15} /> Private hub</span>
        <button type="button" className="nav" onClick={() => { setToken(''); setTokenField(''); setMachines([]); setError(''); }}><LogOut size={18}/> Disconnect</button>
      </div>
    </aside>
    <main className="content">
      <header className="topbar"><span className="crumb">GoreeCloud / Metrics / <b>{view === 'overview' ? 'Overview' : 'Alerts'}</b></span>
        <div className="top-actions"><span className="live-dot" aria-hidden="true"/> <span className="last-updated">{lastRefresh ? 'Updated ' + lastRefresh.toLocaleTimeString() : 'Connecting'}</span>
        <button type="button" className="icon-button" aria-label="Refresh data" disabled={loading} onClick={() => void refresh()}><RefreshCw size={19} className={loading ? 'spin' : ''}/></button></div>
      </header>
      <section className="workspace">
        <div className="heading-row">
          <div><div className="eyebrow">SYSTEM HEALTH / LIVE SNAPSHOT</div><h1>{view === 'overview' ? 'Infrastructure overview' : 'Active alerts'}</h1>
            <p className="subtitle">{view === 'overview' ? 'A clear view of the machines that keep your cloud running.' : 'Current-state threshold indicators and connectivity issues.'}</p></div>
          <span className="scope-pill"><ShieldCheck size={16}/> Private workspace</span>
        </div>
        {error && <div className="error" role="alert">{error} <button type="button" onClick={() => {setToken(''); setTokenField('');}}>Reconnect</button></div>}
        {view === 'alerts' ? <div className="panel alerts-panel">
          <h2>Current indicators <span className="muted">({alerts.length})</span></h2>
          {alerts.length ? alerts.map((a, i) => <div className="alert-row" key={a.node_id + a.metric + i}>
            <span className="alert-marker"/><div><strong>{a.node_id}</strong><p>{a.message}</p></div><span className="alert-label">{a.severity}</span>
          </div>) : <div className="empty"><ShieldCheck size={38}/><h3>No current alerts</h3><p>No threshold or offline indicators are active.</p></div>}
          <div className="fine-print">Thresholds are 90% CPU, memory or disk and 120 seconds without a heartbeat. Notification delivery is not yet implemented.</div>
        </div> : <>
          <div className="summary-grid">
            <div className="stat-card"><div className="stat-title"><span>Monitored systems</span><Server size={20}/></div><strong>{machines.length}</strong><span className="stat-caption">Configured agents reporting</span></div>
            <div className="stat-card"><div className="stat-title"><span>Online now</span><Activity size={20}/></div><strong>{online}<small> / {machines.length}</small></strong><span className="stat-caption"><span className="positive-dot"/> Received heartbeat recently</span></div>
            <div className="stat-card"><div className="stat-title"><span>Active indicators</span><Bell size={20}/></div><strong>{alerts.length}</strong><span className="stat-caption">Current threshold or heartbeat alerts</span></div>
          </div>
          <div className="section-heading"><div><h2>Systems</h2><p>Choose a host to explore its live metrics and history</p></div><span className="muted">{machines.length} total</span></div>
          <div className="machine-grid">
            {machines.map(m => <button key={m.node_id} type="button" className={'machine-card' + (selected === m.node_id ? ' selected' : '')} onClick={() => setSelected(m.node_id)}>
              <span className="machine-title"><span className="machine-glyph"><Server size={21}/></span><span><strong>{m.hostname}</strong><small>{m.node_id}</small></span><span className={'health ' + (m.online ? 'online' : 'offline')}>{m.online ? 'Online' : 'Offline'}</span></span>
              <div className="mini-metrics"><span>CPU <strong>{pct(m.cpu)}</strong></span><span>Memory <strong>{pct(m.memory)}</strong></span><span>Disk <strong>{pct(m.disk)}</strong></span></div>
              <div className="track"><div style={{width: Math.min(100, Math.max(0,m.cpu ?? 0))+'%'}}/></div>
            </button>)}
            {machines.length === 0 && <div className="empty machine-empty"><Server size={36}/><h3>No hosts connected</h3><p>Configure the agent token and run the agent on a Linux host to start reporting.</p></div>}
          </div>
          {machine && <div className="details">
            <div className="section-heading"><div><h2>{machine.hostname} <span className="muted">/ Last 24 hours</span></h2><p>CPU, memory and disk utilization over time</p></div></div>
            <div className="panel chart-panel">
              <div className="metric-strip">
                <span><Cpu size={18}/> CPU <b>{pct(machine.cpu)}</b></span>
                <span><MemoryStick size={18}/> Memory <b>{pct(machine.memory)}</b></span>
                <span><HardDrive size={18}/> Disk <b>{pct(machine.disk)}</b></span>
              </div>
              {history.length ? <div className="chart" aria-label="24 hour time series chart">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={history}>
                    <defs>
                      <linearGradient id="cpuFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#00697A" stopOpacity={0.24}/><stop offset="100%" stopColor="#00697A" stopOpacity={0}/></linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="4 4" vertical={false} stroke="var(--outline-soft)"/>
                    <XAxis dataKey="ts" tickFormatter={(ts: number) => new Date(ts * 1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})} tickLine={false} axisLine={false} minTickGap={28}/>
                    <YAxis domain={[0,100]} tickFormatter={(n: number) => n+'%'} tickLine={false} axisLine={false} width={42}/>
                    <Tooltip labelFormatter={value => new Date(Number(value) * 1000).toLocaleString()} formatter={value => pct(Number(value))}/>
                    <Legend/>
                    <Area type="monotone" dataKey="cpu" name="CPU" stroke="#00697A" strokeWidth={2} fill="url(#cpuFill)" dot={false}/>
                    <Area type="monotone" dataKey="memory" name="Memory" stroke="#5146C8" strokeWidth={2} fill="transparent" dot={false}/>
                    <Area type="monotone" dataKey="disk" name="Disk" stroke="#A43F1D" strokeWidth={2} fill="transparent" dot={false}/>
                  </AreaChart>
                </ResponsiveContainer>
              </div> : <div className="empty"><Activity size={30}/><p>Waiting for historical samples</p></div>}
            </div>
            <div className="network-grid">
              <div className="network-card"><ArrowDown size={20}/><div><span>Received since boot</span><strong>{size(machine.rx_bytes)}</strong></div></div>
              <div className="network-card"><ArrowUp size={20}/><div><span>Sent since boot</span><strong>{size(machine.tx_bytes)}</strong></div></div>
              <div className="network-card"><Activity size={20}/><div><span>System uptime</span><strong>{Math.floor(machine.uptime_seconds / 3600)} hours</strong></div></div>
            </div>
          </div>}
        </>}
        <footer>GoreeCloud Metrics · Development preview · Built for private infrastructure</footer>
      </section>
    </main>
  </div>;
}
