import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { Activity, ArrowDown, ArrowUp, Bell, CircleDot, Cpu, HardDrive, LayoutDashboard, LogOut, MemoryStick, RefreshCw, Server, ShieldCheck } from 'lucide-react';
import { fetchHostCsv } from './hostExport';
import { RequestEpoch } from './requestEpoch';

type Machine = { node_id: string; hostname: string; last_seen: number; online: boolean; cpu: number; memory: number; disk: number; memory_bytes: number; disk_bytes: number; rx_bytes: number; tx_bytes: number; uptime_seconds: number };
type Sample = { ts: number; cpu: number; memory: number; disk: number };
type Alert = { node_id: string; metric: string; severity: string; message: string };
type ContainerSnapshot = { name: string; cpu: number; memory: number; rx_bytes: number; tx_bytes: number; ts: number };
type AlertTransition = { id: number; node_id: string; metric: string; state: string; message: string; created_ts: number };
type NetworkRate = { node_id: string; state: 'ok' | 'insufficient_samples' | 'counter_reset' | 'invalid_interval'; latest_ts: number | null; interval_seconds: number | null; rx_bytes_per_second: number | null; tx_bytes_per_second: number | null };
type View = 'overview' | 'alerts';

const HostHistoryChart = lazy(() => import('./HostHistoryChart'));

const size = (bytes = 0) => {
  if (!Number.isFinite(bytes)) return '—';
  if (bytes < 1024) return Math.round(bytes) + ' B';
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), 4);
  return (bytes / 1024 ** exponent).toFixed(1) + ' ' + (['B', 'KB', 'MB', 'GB', 'TB'][exponent]);
};
const pct = (number?: number) => Number.isFinite(number) ? Math.round(number!) + '%' : '—';

export default function App() {
  const session = useRef(new RequestEpoch());
  const polling = useRef(new RequestEpoch());
  const [tokenField, setTokenField] = useState('');
  const [token, setToken] = useState('');
  const [machines, setMachines] = useState<Machine[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selected, setSelected] = useState('');
  const [history, setHistory] = useState<Sample[]>([]);
  const [historyHours, setHistoryHours] = useState<6 | 24 | 168>(24);
  const [exportBusy, setExportBusy] = useState(false);
  const [exportNote, setExportNote] = useState('');
  const [exportFailed, setExportFailed] = useState(false);
  const [containers, setContainers] = useState<ContainerSnapshot[]>([]);
  const [networkRate, setNetworkRate] = useState<NetworkRate | null>(null);
  const [alertEvents, setAlertEvents] = useState<AlertTransition[]>([]);
  const [view, setView] = useState<View>('overview');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const request = useCallback(async (path: string) => {
    const result = await fetch(path, { headers: { Authorization: 'Bearer ' + token }, cache: 'no-store', redirect: 'error' });
    if (!result.ok) throw new Error(result.status === 401 ? 'Invalid administrator token' : 'API error (' + result.status + ')');
    return result.json();
  }, [token]);

  const refresh = useCallback(async () => {
    if (!token) return;
    const sessionTicket = session.current.snapshot();
    const pollTicket = polling.current.begin();
    const stillCurrent = () => session.current.accepts(sessionTicket) && polling.current.accepts(pollTicket);
    setLoading(true);
    try {
      const [systemData, alertData] = await Promise.all([request('/api/v1/systems'), request('/api/v1/alerts')]);
      if (!stillCurrent()) return;
      setMachines(systemData.systems);
      setAlerts(alertData.alerts);
      setSelected(current => current && systemData.systems.some((m: Machine) => m.node_id === current)
        ? current : systemData.systems[0]?.node_id ?? '');
      setLastRefresh(new Date());
      setError('');
    } catch (e) {
      if (stillCurrent()) setError(e instanceof Error ? e.message : 'Connection failed');
    } finally {
      if (stillCurrent()) setLoading(false);
    }
  }, [request, token]);

  useEffect(() => {
    if (!token) return;
    void refresh();
    const interval = window.setInterval(() => { void refresh(); }, 15000);
    return () => {
      window.clearInterval(interval);
      polling.current.invalidate();
      session.current.invalidate();
    };
  }, [refresh, token]);

  useEffect(() => {
    if (!token || !selected) { setHistory([]); setContainers([]); setNetworkRate(null); return; }
    let active = true;
    setNetworkRate(null);
    setHistory([]);
    const host = encodeURIComponent(selected);
    void request('/api/v1/systems/' + host + '/history?hours=' + historyHours + '&points=400')
      .then(data => { if (active) setHistory(data.samples); })
      .catch(() => { if (active) setHistory([]); });
    void request('/api/v1/systems/' + host + '/containers')
      .then(data => { if (active) setContainers(data.containers); })
      .catch(() => { if (active) setContainers([]); });
    void request('/api/v1/systems/' + host + '/network-rate')
      .then(data => { if (active) setNetworkRate(data as NetworkRate); })
      .catch(() => { if (active) setNetworkRate(null); });
    return () => { active = false; };
  }, [selected, request, lastRefresh, historyHours, token]);

  useEffect(() => {
    if (!token || view !== 'alerts') return;
    let active = true;
    void request('/api/v1/alert-events?limit=50')
      .then(data => { if (active) setAlertEvents(data.events); })
      .catch(() => { if (active) setAlertEvents([]); });
    return () => { active = false; };
  }, [token, view, request, lastRefresh]);

  const machine = machines.find(m => m.node_id === selected);
  const online = machines.filter(m => m.online).length;
  const rate = networkRate?.node_id === selected && networkRate.state === 'ok' ? networkRate : null;
  const rateNote = networkRate?.node_id !== selected ? 'Waiting for a valid interval' :
    networkRate?.state === 'counter_reset' ? 'Counter reset or host restart' :
    networkRate?.state === 'invalid_interval' ? 'Invalid or stale interval' :
    networkRate?.state === 'insufficient_samples' ? 'Waiting for a second reading' :
    networkRate?.state === 'ok' ? 'Across latest two readings' : 'Rate unavailable';

  async function downloadCsv() {
    if (!token || !selected || exportBusy) return;
    const sessionTicket = session.current.snapshot();
    const host = selected;
    const hours = historyHours;
    setExportBusy(true);
    setExportNote('');
    setExportFailed(false);
    try {
      const result = await fetchHostCsv(host, token, hours);
      // Never start a delayed file download after logout or a new sign-in.
      if (!session.current.accepts(sessionTicket)) return;
      const blobUrl = URL.createObjectURL(result.blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = 'metrics-' + host + '-' + hours + 'h-' + new Date().toISOString().slice(0, 10) + '.csv';
      document.body.appendChild(link);
      link.click();
      link.remove();
      // Keep the URL valid long enough for the browser to initiate its download.
      window.setTimeout(() => URL.revokeObjectURL(blobUrl), 60000);
      setExportNote(result.partial
        ? 'Downloaded the newest 10,000 samples only. Use the API cursor for older data.'
        : 'CSV download requested for the selected host and period.');
    } catch (error) {
      if (session.current.accepts(sessionTicket)) {
        setExportFailed(true);
        setExportNote(error instanceof Error ? error.message : 'CSV export failed');
      }
    } finally {
      if (session.current.accepts(sessionTicket)) setExportBusy(false);
    }
  }

  function disconnect() {
    session.current.invalidate();
    polling.current.invalidate();
    setToken('');
    setTokenField('');
    setMachines([]);
    setAlerts([]);
    setSelected('');
    setHistory([]);
    setContainers([]);
    setNetworkRate(null);
    setAlertEvents([]);
    setError('');
    setLoading(false);
    setLastRefresh(null);
    setExportBusy(false);
    setExportNote('');
    setExportFailed(false);
  }

  if (!token) {
    return <main className="login-screen">
      <section className="login-card">
        <span className="brand-icon"><Activity size={28} aria-hidden="true" /></span>
        <div className="eyebrow">GOREECLOUD / OBSERVABILITY</div>
        <h1>See every system.<br /><span>Know what matters.</span></h1>
        <p>Sign in to your private Metrics hub. The access token is held in memory only, never saved to browser storage.</p>
        <form onSubmit={e => {
          e.preventDefault();
          if (tokenField.trim()) {
            session.current.invalidate();
            polling.current.invalidate();
            setToken(tokenField.trim());
          }
        }}>
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
        <button type="button" className="nav" onClick={disconnect}><LogOut size={18}/> Disconnect</button>
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
        {error && <div className="error" role="alert">{error} <button type="button" onClick={disconnect}>Reconnect</button></div>}
        {view === 'alerts' ? <div className="panel alerts-panel">
          <h2>Current indicators <span className="muted">({alerts.length})</span></h2>
          {alerts.length ? alerts.map((a, i) => <div className="alert-row" key={a.node_id + a.metric + i}>
            <span className="alert-marker"/><div><strong>{a.node_id}</strong><p>{a.message}</p></div><span className="alert-label">{a.severity}</span>
          </div>) : <div className="empty"><ShieldCheck size={38}/><h3>No current alerts</h3><p>No threshold or offline indicators are active.</p></div>}
          <div className="fine-print">Thresholds are configured on the hub (defaults: 90% and 120 seconds offline). External notifications require a separately enabled webhook worker.</div>
          <div className="event-history" aria-label="Recent alert transitions">
            <h2>Recent transitions <span className="muted">({alertEvents.length})</span></h2>
            {alertEvents.length === 0 ? <p className="muted">No recorded transitions. An operator must start the optional notification journal worker.</p>
              : alertEvents.map(event => <div className="event-row" key={event.id}>
                <span className={'event-state ' + (event.state === 'resolved' ? 'event-resolved' : 'event-firing')}>{event.state}</span>
                <div><strong>{event.node_id} · {event.metric}</strong><p>{event.message}</p></div>
                <time dateTime={new Date(event.created_ts * 1000).toISOString()}>{new Date(event.created_ts * 1000).toLocaleString()}</time>
              </div>)}
          </div>
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
            <div className="section-heading history-heading"><div><h2>{machine.hostname} <span className="muted">/ Last {historyHours === 168 ? '7 days' : historyHours + ' hours'}</span></h2><p>CPU, memory and disk utilization over the selected interval</p></div>
              <div className="history-actions">
                <div className="history-periods" role="group" aria-label="History time window">
                  {([6, 24, 168] as const).map(hours =>
                    <button key={hours} type="button" aria-pressed={historyHours === hours}
                      className={'history-period' + (historyHours === hours ? ' active' : '')}
                      onClick={() => setHistoryHours(hours)}>{hours === 168 ? '7d' : hours + 'h'}</button>
                  )}
                </div>
                <button className="export-button" type="button" onClick={() => void downloadCsv()}
                  disabled={exportBusy} aria-describedby="csv-export-help">
                  {exportBusy ? 'Preparing CSV…' : 'Export CSV'}
                </button>
              </div>
            </div>
            <p id="csv-export-help" className="export-hint">Raw host samples for the selected interval, newest 10,000 at most. Older pages require the API cursor.</p>
            {exportNote && <p className="export-hint" role={exportFailed ? 'alert' : 'status'}>{exportNote}</p>}
            <div className="panel chart-panel">
              <div className="metric-strip">
                <span><Cpu size={18}/> CPU <b>{pct(machine.cpu)}</b></span>
                <span><MemoryStick size={18}/> Memory <b>{pct(machine.memory)}</b></span>
                <span><HardDrive size={18}/> Disk <b>{pct(machine.disk)}</b></span>
              </div>
              {history.length ? <Suspense fallback={<div className="chart chart-loading" role="status">Preparing history chart…</div>}>
                <HostHistoryChart history={history} hours={historyHours}/>
              </Suspense> : <div className="empty"><Activity size={30}/><p>Waiting for historical samples</p></div>}
            </div>
            <div className="network-grid">
              <div className="network-card"><ArrowDown size={20}/><div><span>Received since boot</span><strong>{size(machine.rx_bytes)}</strong></div></div>
              <div className="network-card"><ArrowUp size={20}/><div><span>Sent since boot</span><strong>{size(machine.tx_bytes)}</strong></div></div>
              <div className="network-card"><Activity size={20}/><div><span>System uptime</span><strong>{Math.floor(machine.uptime_seconds / 3600)} hours</strong></div></div>
              <div className="network-card"><ArrowDown size={20}/><div><span>Received per second</span><strong>{rate?.rx_bytes_per_second == null ? '—' : size(rate.rx_bytes_per_second) + '/s'}</strong><small className="rate-note">{rateNote}</small></div></div>
              <div className="network-card"><ArrowUp size={20}/><div><span>Sent per second</span><strong>{rate?.tx_bytes_per_second == null ? '—' : size(rate.tx_bytes_per_second) + '/s'}</strong><small className="rate-note">{rateNote}</small></div></div>
            </div>
            <div className="section-heading"><div><h2>Containers <span className="muted">/ Optional</span></h2><p>Read-only snapshots from explicitly enabled Podman or Docker collection.</p></div></div>
            <div className="panel">
              {containers.length === 0 ? <p className="muted">No container snapshots for this host. Collection is disabled by default.</p>
                : <div className="container-table-wrap"><table className="container-table"><thead><tr><th>Container</th><th>CPU</th><th>Memory</th><th>Network received</th><th>Network sent</th></tr></thead>
                <tbody>{containers.map(container => <tr key={container.name}><th scope="row">{container.name}</th><td>{pct(container.cpu)}</td><td>{pct(container.memory)}</td><td>{size(container.rx_bytes)}</td><td>{size(container.tx_bytes)}</td></tr>)}</tbody>
                </table></div>}
            </div>
          </div>}
        </>}
        <footer>GoreeCloud Metrics · Development preview · Built for private infrastructure</footer>
      </section>
    </main>
  </div>;
}
