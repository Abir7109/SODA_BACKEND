import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const COLORS = ['#00f0ff', '#00ff88', '#ffaa00', '#ff3355', '#8884d8', '#ff66b2']

export default function BarChartCard({ title, labels, values, color }) {
  if (!labels || !values || labels.length === 0) return null
  const data = labels.map((l, i) => ({ name: l, value: values[i] || 0 }))
  return (
    <div className="bg-[#0a0a0f] border border-[#1e1e2e] p-3">
      <div className="text-[10px] text-[#00f0ff] uppercase tracking-widest font-bold mb-2">{title}</div>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} margin={{ top: 5, right: 5, bottom: 20, left: 0 }}>
          <XAxis dataKey="name" tick={{ fill: '#666680', fontSize: 9 }} axisLine={{ stroke: '#1e1e2e' }} tickLine={false} />
          <YAxis tick={{ fill: '#666680', fontSize: 9 }} axisLine={{ stroke: '#1e1e2e' }} tickLine={false} />
          <Tooltip contentStyle={{ background: '#1e1e2e', border: '1px solid #2a2a3a', borderRadius: 0, fontSize: 11 }}
            labelStyle={{ color: '#e0e0e0' }} itemStyle={{ color: '#00f0ff' }} />
          <Bar dataKey="value" fill={color || COLORS[0]} radius={[1, 1, 0, 0]}>
            {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
