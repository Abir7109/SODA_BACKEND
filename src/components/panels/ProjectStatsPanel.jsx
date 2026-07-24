import { useState } from 'react'
import SlidePanel from '../SlidePanel'
import { Activity, Globe, Zap, CheckCircle, XCircle, Clock, ExternalLink, X, Users, Shield, TrendingUp } from 'lucide-react'

function StatBar({ label, value, max, color }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-[10px]">
        <span style={{ color: 'var(--text-dim)' }}>{label}</span>
        <span style={{ color }}>{value}</span>
      </div>
      <div className="h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.05)' }}>
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  )
}

function ProjectCard({ project }) {
  const [expanded, setExpanded] = useState(true)
  const body = project.data || project
  const isOnline = project.success !== false
  const err = project.error || body.error

  const numericStats = Object.fromEntries(
    Object.entries(body).filter(([k, v]) => typeof v === 'number' && !['uptime', 'created_at'].includes(k))
  )
  const maxVal = Math.max(...Object.values(numericStats), 1)

  return (
    <div className="rounded-xl border p-4" style={{ borderColor: 'var(--border)', background: 'rgba(0,0,0,0.3)' }}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div style={{ width: 28, height: 28, borderRadius: 8, background: isOnline ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {isOnline ? <CheckCircle size={14} style={{ color: '#22c55e' }} /> : <XCircle size={14} style={{ color: '#ef4444' }} />}
          </div>
          <div>
            <div className="font-bold text-sm" style={{ color: 'var(--text-primary)' }}>{body.project || project.name || 'Project'}</div>
            {body.status && (
              <span className="text-[9px] px-1.5 py-0.5 rounded mt-0.5" style={{ background: 'rgba(0,251,251,0.1)', color: '#00fbfb' }}>
                {body.status.toUpperCase()}
              </span>
            )}
          </div>
        </div>
        <button onClick={() => setExpanded(!expanded)} className="text-[10px] px-2 py-1 rounded" style={{ border: '1px solid var(--border)', color: 'var(--text-dim)', background: 'transparent' }}>
          {expanded ? 'Collapse' : 'Expand'}
        </button>
      </div>

      {err && (
        <div className="text-[11px] p-2 rounded mb-3" style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444' }}>
          {err}
        </div>
      )}

      {expanded && !err && (
        <>
          {Object.keys(numericStats).length > 0 && (
            <div className="space-y-2 mb-3">
              {Object.entries(numericStats).map(([key, val]) => {
                const colors = { totalUsers: '#22c55e', activeUsers: '#3b82f6', blockedUsers: '#ef4444', protectionActive: '#00fbfb' }
                return <StatBar key={key} label={key.replace(/_/g, ' ')} value={val} max={maxVal} color={colors[key] || '#a855f7'} />
              })}
              {body.uptime != null && (
                <div className="flex items-center gap-1 text-[10px]" style={{ color: 'var(--text-dim)' }}>
                  <Clock size={10} />
                  <span>Uptime: {Math.round(body.uptime)}s</span>
                </div>
              )}
            </div>
          )}

          {body.recentEvents?.length > 0 && (
            <div className="rounded-lg p-2" style={{ background: 'rgba(255,255,255,0.03)' }}>
              <div className="text-[9px] font-bold mb-1.5 uppercase tracking-wider" style={{ color: 'var(--text-dim)' }}>
                Recent Events ({body.recentEvents.length})
              </div>
              {body.recentEvents.slice(0, 5).map((e, i) => (
                <div key={i} className="flex items-center gap-2 py-1 text-[9px]" style={{ borderTop: i > 0 ? '1px solid rgba(255,255,255,0.05)' : 'none' }}>
                  <span className="px-1 py-0.5 rounded text-[8px] font-bold uppercase" style={{ background: e.type?.includes('trigger') ? 'rgba(239,68,68,0.15)' : 'rgba(59,130,246,0.15)', color: e.type?.includes('trigger') ? '#ef4444' : '#3b82f6' }}>
                    {e.type?.replace('_', ' ').slice(0, 8) || 'EVENT'}
                  </span>
                  <span className="truncate" style={{ color: 'var(--text-dim)' }}>{e.details || e.timestamp?.slice(0, 16).replace('T', ' ')}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default function ProjectStatsPanel({ visible, data, onClose }) {
  const raw = data?.result ?? data
  const projects = Array.isArray(raw) ? raw : (raw ? [raw] : [])

  return (
    <SlidePanel visible={visible} direction="right" title="PROJECT STATS" icon={<Activity size={11} />}
      accentColor="#00fbfb" onClose={onClose} autoDismissMs={0}>
      <div className="flex flex-col gap-3 p-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px]" style={{ color: 'var(--text-dim)' }}>{projects.length} project{projects.length !== 1 ? 's' : ''}</span>
          <button onClick={onClose} className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[10px] font-bold"
            style={{ background: 'rgba(255,255,255,0.08)', color: 'var(--text-primary)', border: '1px solid var(--border)' }}>
            <X size={12} /> Dismiss
          </button>
        </div>
        {projects.length === 0 && (
          <div className="flex flex-col items-center justify-center py-8 gap-2">
            <Globe size={24} style={{ color: 'var(--text-dim)', opacity: 0.3 }} />
            <div className="text-xs" style={{ color: 'var(--text-dim)' }}>No projects registered.</div>
          </div>
        )}
        {projects.map((p, i) => (
          <ProjectCard key={p.id || i} project={p} />
        ))}
      </div>
    </SlidePanel>
  )
}
