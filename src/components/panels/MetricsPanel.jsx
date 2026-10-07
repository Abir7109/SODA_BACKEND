import { useState } from 'react'
import socket from '../../services/SocketService'
import SlidePanel from '../SlidePanel'
import { BarChart3, Wrench, Clock, CheckCircle, XCircle, Zap, Coins, RefreshCw, Activity } from 'lucide-react'

function SuccessBar({ rate }) {
  if (rate == null) return null
  const pct = Math.round(rate * 100)
  const color = pct >= 90 ? '#22c55e' : pct >= 70 ? '#f59e0b' : '#ef4444'
  return (
    <div className="agent-monitor-response">
      <div className="agent-monitor-response-header">
        <CheckCircle size={10} />
        Success rate
        <span className="agent-monitor-response-ms" style={{ color }}>{pct}%</span>
      </div>
      <div className="agent-monitor-bar-bg">
        <div className="agent-monitor-bar-fill" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
    </div>
  )
}

function TopToolRow({ t, maxCount }) {
  const pct = maxCount > 0 ? Math.round((t.count / maxCount) * 100) : 0
  return (
    <div className="agent-monitor-ssl-row" style={{ position: 'relative' }}>
      <span className="agent-monitor-ssl-key">
        <Wrench size={9} style={{ verticalAlign: '-1px', marginRight: 5 }} />
        {t.name}
      </span>
      <span className="agent-monitor-ssl-val">
        {t.count}× · {t.avg_duration_ms}ms
      </span>
      <div style={{
        position: 'absolute', left: 0, bottom: 0, height: 2, width: `${pct}%`,
        backgroundColor: '#00fbfb', opacity: 0.5,
      }} />
    </div>
  )
}

export default function MetricsPanel({ visible, data, onClose }) {
  const d = data?.result || data || {}
  const tools = d.tools || {}
  const turns = d.turns || {}
  const usage = d.usage || {}
  const top = Array.isArray(tools.top) ? tools.top : []
  const [refreshing, setRefreshing] = useState(false)

  const refresh = () => {
    setRefreshing(true)
    socket.emit('metrics_request', { window_hours: d.window_hours || 1 })
    setTimeout(() => setRefreshing(false), 800)
  }

  const fmtTokens = (n) => (n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n || 0))

  return (
    <SlidePanel visible={visible} direction="right" title={`METRICS · LAST ${d.window_hours || 1}H`}
      icon={<BarChart3 size={11} />} accentColor="#00fbfb" onClose={onClose} autoDismissMs={0}>

      <div className="agent-stats-row">
        <div className="agent-stat-card">
          <span className="agent-stat-label">TOOL CALLS</span>
          <span className="agent-stat-value">{tools.count ?? 0}</span>
        </div>
        <div className="agent-stat-card">
          <span className="agent-stat-label">AVG RUN</span>
          <span className="agent-stat-value">{tools.avg_duration_ms ?? 0}ms</span>
        </div>
        <div className="agent-stat-card">
          <span className="agent-stat-label">VOICE TURNS</span>
          <span className="agent-stat-value">{turns.count ?? 0}</span>
        </div>
        <div className="agent-stat-card">
          <span className="agent-stat-label">TOKENS</span>
          <span className="agent-stat-value">{fmtTokens((usage.tokens_in || 0) + (usage.tokens_out || 0))}</span>
        </div>
      </div>

      <div className="agent-divider" />

      <SuccessBar rate={tools.success_rate} />

      <div className="agent-section-block">
        <div className="agent-section-block-title">
          <Clock size={10} />
          Voice latency
        </div>
        <div className="agent-monitor-ssl-row">
          <span className="agent-monitor-ssl-key"><Activity size={9} style={{ verticalAlign: '-1px', marginRight: 5 }} />Avg first audio</span>
          <span className="agent-monitor-ssl-val" style={{ color: (turns.avg_first_audio_ms ?? 0) < 2000 ? '#22c55e' : '#f59e0b' }}>
            {turns.avg_first_audio_ms != null ? `${turns.avg_first_audio_ms}ms` : '—'}
          </span>
        </div>
        <div className="agent-monitor-ssl-row">
          <span className="agent-monitor-ssl-key"><Zap size={9} style={{ verticalAlign: '-1px', marginRight: 5 }} />Measured turns</span>
          <span className="agent-monitor-ssl-val">{turns.count ?? 0}</span>
        </div>
      </div>

      <div className="agent-section-block">
        <div className="agent-section-block-title">
          <Coins size={10} />
          Token usage
        </div>
        <div className="agent-monitor-ssl-row">
          <span className="agent-monitor-ssl-key">Input (prompt)</span>
          <span className="agent-monitor-ssl-val">{fmtTokens(usage.tokens_in)}</span>
        </div>
        <div className="agent-monitor-ssl-row">
          <span className="agent-monitor-ssl-key">Output (candidates)</span>
          <span className="agent-monitor-ssl-val">{fmtTokens(usage.tokens_out)}</span>
        </div>
      </div>

      <div className="agent-section-block">
        <div className="agent-section-block-title">
          <Wrench size={10} />
          Top tools
        </div>
        {top.length === 0
          ? <div className="agent-paragraph">No tool runs in this window yet.</div>
          : top.map(t => <TopToolRow key={t.name} t={t} maxCount={top[0].count} />)}
      </div>

      <div className="agent-divider" />

      <button className="agent-expand-btn" onClick={refresh} disabled={refreshing}
        style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'center', width: '100%' }}>
        <RefreshCw size={11} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
        {refreshing ? 'Refreshing…' : 'Refresh'}
      </button>

      {d.error && <div className="agent-error-msg">{d.error}</div>}
    </SlidePanel>
  )
}
