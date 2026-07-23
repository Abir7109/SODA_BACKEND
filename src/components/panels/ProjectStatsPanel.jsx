import { useState } from 'react'
import SlidePanel from '../SlidePanel'
import { Activity, Globe, Zap, CheckCircle, XCircle, Clock, ExternalLink } from 'lucide-react'

function ProjectCard({ project, onQuery }) {
  const [expanded, setExpanded] = useState(false)
  const data = project.data || project
  const isOnline = project.success !== false
  const stats = data.stats || {}

  return (
    <div className="sp-result-card" style={{ cursor: 'pointer' }} onClick={() => setExpanded(!expanded)}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Globe size={12} style={{ color: isOnline ? '#22c55e' : '#ef4444' }} />
          <span className="font-semibold text-xs" style={{ color: 'var(--text-primary)' }}>{data.project || project.name || 'Project'}</span>
        </div>
        <div className="flex items-center gap-2">
          {isOnline
            ? <CheckCircle size={11} style={{ color: '#22c55e' }} />
            : <XCircle size={11} style={{ color: '#ef4444' }} />}
          {onQuery && (
            <button
              onClick={(e) => { e.stopPropagation(); onQuery(project.id) }}
              className="text-[10px] px-2 py-0.5 rounded"
              style={{ border: '1px solid var(--accent)', color: 'var(--accent)', background: 'transparent' }}>
              Query
            </button>
          )}
        </div>
      </div>

      {expanded && stats && Object.keys(stats).length > 0 && (
        <div className="grid grid-cols-2 gap-1 mt-2">
          {Object.entries(stats).map(([key, val]) => (
            <div key={key} className="flex items-center gap-1 text-[10px]" style={{ color: 'var(--text-dim)' }}>
              <Zap size={8} />
              <span className="capitalize">{key.replace(/_/g, ' ')}:</span>
              <span style={{ color: 'var(--text-primary)' }}>{String(val)}</span>
            </div>
          ))}
        </div>
      )}

      {project.error && (
        <div className="text-[10px] mt-1" style={{ color: '#ef4444' }}>{project.error}</div>
      )}

      {project.response_time_ms != null && (
        <div className="flex items-center gap-1 mt-1 text-[10px]" style={{ color: 'var(--text-dim)' }}>
          <Clock size={8} />
          {project.response_time_ms}ms
        </div>
      )}
    </div>
  )
}

export default function ProjectStatsPanel({ visible, data, onClose }) {
  const projects = Array.isArray(data) ? data : (data?.result ? (Array.isArray(data.result) ? data.result : [data.result]) : [])

  return (
    <SlidePanel visible={visible} direction="right" title="PROJECTS" icon={<Activity size={11} />}
      accentColor="#00fbfb" onClose={onClose} autoDismissMs={0}>
      <div className="flex flex-col gap-2 p-3">
        {projects.length === 0 && (
          <div className="text-xs" style={{ color: 'var(--text-dim)' }}>No projects registered.</div>
        )}
        {projects.map((p, i) => (
          <ProjectCard key={p.id || i} project={p} />
        ))}
      </div>
    </SlidePanel>
  )
}
