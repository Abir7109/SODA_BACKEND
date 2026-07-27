import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'

const COLORS = ['#00f0ff', '#00ff88', '#ffaa00', '#ff3355', '#8884d8', '#ff66b2', '#50e3c2', '#f5a623']

export default function PieChartCard({ title, data }) {
  if (!data || data.length === 0) return null
  return (
    <div className="bg-[#0a0a0f] border border-[#1e1e2e] p-3">
      <div className="text-[10px] text-[#00f0ff] uppercase tracking-widest font-bold mb-2">{title}</div>
      <div className="flex items-center gap-4">
        <ResponsiveContainer width="60%" height={160}>
          <PieChart>
            <Pie data={data} cx="50%" cy="50%" innerRadius={35} outerRadius={60} paddingAngle={2}
              dataKey="value" nameKey="name">
              {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Pie>
            <Tooltip contentStyle={{ background: '#1e1e2e', border: '1px solid #2a2a3a', borderRadius: 0, fontSize: 11 }}
              labelStyle={{ color: '#e0e0e0' }} itemStyle={{ color: '#fff' }} />
          </PieChart>
        </ResponsiveContainer>
        <div className="space-y-1">
          {data.map((d, i) => (
            <div key={i} className="flex items-center gap-2 text-[10px]">
              <span className="w-2 h-2 shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
              <span className="text-[#b0b0cc]">{d.name}</span>
              <span className="text-white font-bold ml-auto">{d.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
