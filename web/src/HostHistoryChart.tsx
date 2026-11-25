import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

type HistoryPoint = { ts: number; cpu: number; memory: number; disk: number };

const pct = (number: number) => Number.isFinite(number) ? Math.round(number) + '%' : '—';

// Loaded only when a selected host has chart samples; no API token or fetch
// is passed to the chart rendering component.
export default function HostHistoryChart({ history, hours }: {
  history: HistoryPoint[];
  hours: 6 | 24 | 168;
}) {
  return <div className="chart" aria-label={'Time series chart, last ' + hours + ' hours'}>
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={history}>
        <defs>
          <linearGradient id="cpuFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#00697A" stopOpacity={0.24}/>
            <stop offset="100%" stopColor="#00697A" stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="4 4" vertical={false} stroke="var(--outline-soft)"/>
        <XAxis dataKey="ts"
          tickFormatter={(ts: number) => new Date(ts * 1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}
          tickLine={false} axisLine={false} minTickGap={28}/>
        <YAxis domain={[0,100]} tickFormatter={(n: number) => n+'%'}
          tickLine={false} axisLine={false} width={42}/>
        <Tooltip labelFormatter={value => new Date(Number(value) * 1000).toLocaleString()}
          formatter={value => pct(Number(value))}/>
        <Legend/>
        <Area type="monotone" dataKey="cpu" name="CPU" stroke="#00697A"
          strokeWidth={2} fill="url(#cpuFill)" dot={false}/>
        <Area type="monotone" dataKey="memory" name="Memory" stroke="#5146C8"
          strokeWidth={2} fill="transparent" dot={false}/>
        <Area type="monotone" dataKey="disk" name="Disk" stroke="#A43F1D"
          strokeWidth={2} fill="transparent" dot={false}/>
      </AreaChart>
    </ResponsiveContainer>
  </div>;
}
