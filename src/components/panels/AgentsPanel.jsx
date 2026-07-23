import { useState } from 'react'
import SlidePanel from '../SlidePanel'
import { Cpu, Activity, CheckCircle, XCircle, Clock, Layers, ChevronDown, ChevronUp, Bot } from 'lucide-react'

function AgentCard({ agent }) {
  const [expanded, setExpanded] = useState(false)
  const s = agent.stats || {}
  const lastCall = s.last_call ? new Date(s.last_call + 'Z').toLocaleString() : 'Never'
  const hasCalls = (s.calls || 0) > 0

  return (
    <div className="agent-card" onClick={() => setExpanded(!expanded)}>
      <div className="agent-card-header">
        <div className="agent-card-name-row">
          <Bot size={14} className="agent-card-icon" />
          <span className="agent-card-name">{agent.name}</span>
          <span className={`agent-card-status ${hasCalls ? 'active' : 'idle'}`}>
            {hasCalls ? <Activity size={10} /> : <Clock size={10} />}
            {hasCalls ? 'Active' : 'Idle'}
          </span>
        </div>
        <div className="agent-card-desc">{agent.description}</div>
      </div>
      <div className="agent-card-stats-row">
        <div className="agent-card-stat">
          <CheckCircle size={10} />
          <span>{s.calls || 0} calls</span>
        </div>
        {s.errors > 0 && (
          <div className="agent-card-stat error">
            <XCircle size={10} />
            <span>{s.errors} errors</span>
          </div>
        )}
        <div className="agent-card-stat">
          <Clock size={10} />
          <span>{lastCall}</span>
        </div>
        {expanded && <ChevronUp size={12} />}
        {!expanded && <ChevronDown size={12} />}
      </div>
    </div>
  )
}

function TaskList({ tasks }) {
  if (!tasks || (tasks.active?.length || 0) === 0 && (tasks.recent?.length || 0) === 0) return null

  return (
    <div className="agent-section-block">
      <div className="agent-section-block-title"><Activity size={12} />Recent Activity</div>
      {tasks.active?.length > 0 && (
        <div className="agent-task-group">
          <div className="agent-task-group-label">Active ({tasks.active.length})</div>
          {tasks.active.map((t, i) => (
            <div key={i} className="agent-task-item active">
              <span className="agent-task-tool">{t.tool}</span>
              {t.agent_name && <span className="agent-task-agent">{t.agent_name}</span>}
            </div>
          ))}
        </div>
      )}
      {tasks.recent?.map((t, i) => (
        <div key={i} className="agent-task-item">
          <span className="agent-task-tool">{t.tool}</span>
          {t.agent_name && <span className="agent-task-agent">{t.agent_name}</span>}
          <span className="agent-task-status">{t.status}</span>
          <span className="agent-task-time">{t.completed_at || ''}</span>
        </div>
      ))}
    </div>
  )
}

export default function AgentsPanel({ visible, data, onClose }) {
  const d = data?.result || data || {}
  const agents = d.agents || []
  const tasks = d.tasks || {}
  const [showAll, setShowAll] = useState(false)
  const display = showAll ? agents : agents.slice(0, 6)
  const hasMore = agents.length > 6
  const hasCalls = agents.filter(a => (a.stats?.calls || 0) > 0)

  return (
    <SlidePanel visible={visible} direction="bottom" title="ACTIVE AGENTS" icon={<Cpu size={11} />} accentColor="#a78bfa" onClose={onClose} autoDismissMs={0}>
      <div className="agent-research-hero">
        <div className="agent-research-hero-icon"><Cpu size={20} /></div>
        <div>
          <div className="agent-research-hero-title">Sub-Agent Fleet</div>
          <div className="agent-research-hero-meta">
            <span className="agent-research-source-count">{agents.length} agents</span>
            <span className="agent-research-source-count">{d.total_tools || 0} tools</span>
            <span className="agent-research-source-count">{hasCalls.length} active</span>
          </div>
        </div>
      </div>

      <div className="agent-stats-row">
        <div className="agent-stat-card"><span className="agent-stat-label">AGENTS</span><span className="agent-stat-value">{agents.length}</span></div>
        <div className="agent-stat-card"><span className="agent-stat-label">TOOLS</span><span className="agent-stat-value">{d.total_tools || 0}</span></div>
        <div className="agent-stat-card"><span className="agent-stat-label">ACTIVE</span><span className="agent-stat-value">{hasCalls.length}</span></div>
        <div className="agent-stat-card"><span className="agent-stat-label">PENDING</span><span className="agent-stat-value">{tasks.active?.length || 0}</span></div>
      </div>

      <div className="agent-divider" />

      <TaskList tasks={tasks} />

      <div className="agent-section-block">
        <div className="agent-section-block-title"><Layers size={12} />All Agents ({agents.length})</div>
        {display.map((a, i) => (
          <AgentCard key={i} agent={a} />
        ))}
        {hasMore && (
          <button className="agent-expand-btn" onClick={() => setShowAll(!showAll)}>
            {showAll ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            {showAll ? 'Show fewer' : `Show all ${agents.length} agents`}
          </button>
        )}
      </div>

      {d._debug && <div className="agent-error-msg" style={{borderColor: 'rgba(167,139,250,0.3)', background: 'rgba(167,139,250,0.05)'}}>Debug: {d._debug}</div>}
      {d.error && <div className="agent-error-msg">{d.error}</div>}
    </SlidePanel>
  )
}
