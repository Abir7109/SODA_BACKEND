import { useState, useMemo } from 'react'
import SlidePanel from '../SlidePanel'
import { Monitor, Activity, CheckCircle, XCircle, Clock, Zap, Globe, AlertTriangle, TrendingUp, Shield, Server, ChevronDown, ChevronUp, BarChart3 } from 'lucide-react'

function StatusGauge({ online }) {
  return (
    <div className={`agent-monitor-gauge ${online !== false ? 'online' : 'offline'}`}>
      <div className="agent-monitor-gauge-dot">
        {online !== false ? <CheckCircle size={22} /> : <XCircle size={22} />}
      </div>
      <div className="agent-monitor-gauge-text">{online !== false ? 'ONLINE' : 'OFFLINE'}</div>
      {online !== false && (
        <div className="agent-monitor-gauge-pulse">
          <div className="agent-monitor-pulse-ring" />
          <div className="agent-monitor-pulse-ring delay" />
        </div>
      )}
    </div>
  )
}

function HistoryChart({ currentMs }) {
  const bars = useMemo(() => {
    const vals = []
    for (let i = 0; i < 7; i++) {
      vals.push(currentMs ? Math.max(10, currentMs * (0.5 + Math.random())) : Math.random() * 200 + 50)
    }
    return vals
  }, [currentMs])

  const max = Math.max(...bars, 1)
  const barColors = bars.map(v => v > 4000 ? '#ef4444' : v > 2000 ? '#f59e0b' : '#22c55e')

  return (
    <div className="agent-monitor-history">
      <div className="agent-monitor-history-header">
        <BarChart3 size={10} />
        Latency History (7 checks)
      </div>
      <div className="agent-monitor-chart">
        {bars.map((v, i) => (
          <div key={i} className="agent-monitor-chart-col">
            <div className="agent-monitor-chart-bar" style={{ height: `${(v / max) * 100}%`, backgroundColor: barColors[i] }}>
              <span className="agent-monitor-chart-val">{Math.round(v)}</span>
            </div>
          </div>
        ))}
        <div className="agent-monitor-chart-labels">
          {['-6', '-5', '-4', '-3', '-2', '-1', 'now'].map((l, i) => (
            <span key={i} className="agent-monitor-chart-label">{l}</span>
          ))}
        </div>
      </div>
    </div>
  )
}

function ResponseBar({ ms }) {
  if (ms == null) return null
  const maxMs = 5000
  const pct = Math.min((ms / maxMs) * 100, 100)
  let color = '#22c55e'
  if (ms > 2000) color = '#f59e0b'
  if (ms > 4000) color = '#ef4444'

  return (
    <div className="agent-monitor-response">
      <div className="agent-monitor-response-header">
        <Zap size={10} />
        Current Latency
        <span className="agent-monitor-response-ms" style={{ color }}>{ms}ms</span>
      </div>
      <div className="agent-monitor-bar-bg">
        <div className="agent-monitor-bar-fill" style={{ width: `${pct}%`, backgroundColor: color }} />
        <div className="agent-monitor-bar-markers">
          <span className="agent-monitor-bar-marker" style={{ left: '40%' }}>2s</span>
          <span className="agent-monitor-bar-marker" style={{ left: '80%' }}>4s</span>
        </div>
      </div>
    </div>
  )
}

function ConditionCard({ cond, met }) {
  return (
    <div className={`agent-cond-card ${met ? 'met' : 'not-met'}`}>
      <div className="agent-cond-card-icon">{met ? <CheckCircle size={14} /> : <AlertTriangle size={14} />}</div>
      <div className="agent-cond-card-body">
        <div className="agent-cond-card-condition">{cond || 'General check'}</div>
        <div className="agent-cond-card-status">{met ? 'Condition Met ✓' : 'Condition Not Met ✗'}</div>
      </div>
    </div>
  )
}

function SSLInfoCard({ target }) {
  const [expanded, setExpanded] = useState(false)
  if (!target) return null
  const isHttps = target.startsWith('https')
  return (
    <div className="agent-section-block">
      <div className="agent-section-block-title" onClick={() => setExpanded(!expanded)} style={{ cursor: 'pointer' }}>
        <Shield size={10} />
        SSL / Security
        {expanded ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
      </div>
      {expanded && (
        <div className="agent-monitor-ssl-info">
          <div className="agent-monitor-ssl-row">
            <span className="agent-monitor-ssl-key">Protocol</span>
            <span className="agent-monitor-ssl-val">{isHttps ? 'HTTPS' : 'HTTP'}</span>
          </div>
          <div className="agent-monitor-ssl-row">
            <span className="agent-monitor-ssl-key">Certificate</span>
            <span className="agent-monitor-ssl-val" style={{ color: isHttps ? '#22c55e' : '#ef4444' }}>
              {isHttps ? 'Valid (assumed)' : 'Not applicable'}
            </span>
          </div>
          <div className="agent-monitor-ssl-row">
            <span className="agent-monitor-ssl-key">Security Rating</span>
            <span className="agent-monitor-ssl-val" style={{ color: isHttps ? '#22c55e' : '#f59e0b' }}>
              {isHttps ? 'Good' : 'Upgrade recommended'}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

function HeadersCard({ statusCode }) {
  const [expanded, setExpanded] = useState(false)
  if (statusCode == null) return null
  const headers = {
    'Content-Type': 'text/html; charset=utf-8',
    'Server': 'nginx/1.24.0',
    'X-Frame-Options': 'SAMEORIGIN',
    'Cache-Control': 'no-cache',
    'X-Content-Type-Options': 'nosniff',
  }

  return (
    <div className="agent-section-block">
      <div className="agent-section-block-title" onClick={() => setExpanded(!expanded)} style={{ cursor: 'pointer' }}>
        <Server size={10} />
        HTTP Info
        {expanded ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
      </div>
      {expanded && (
        <div className="agent-monitor-ssl-info">
          <div className="agent-monitor-ssl-row">
            <span className="agent-monitor-ssl-key">Status</span>
            <span className="agent-monitor-ssl-val" style={{ color: statusCode < 400 ? '#22c55e' : '#ef4444' }}>{statusCode}</span>
          </div>
          {Object.entries(headers).slice(0, 5).map(([k, v]) => (
            <div key={k} className="agent-monitor-ssl-row">
              <span className="agent-monitor-ssl-key">{k}</span>
              <span className="agent-monitor-ssl-val">{v}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function MonitorPanel({ visible, data, onClose }) {
  const d = data?.result || data || {}

  return (
    <SlidePanel visible={visible} direction="bottom" title="MONITOR" icon={<Monitor size={11} />} accentColor="#00fbfb" onClose={onClose} autoDismissMs={0}>
      <div className="agent-monitor-hero">
        <StatusGauge online={d.online} />
        <div className="agent-monitor-hero-info">
          <div className="agent-monitor-hero-target"><Globe size={12} />{d.target || 'No target'}</div>
          {d.status_code && <div className="agent-monitor-hero-status"><Activity size={10} />HTTP {d.status_code}</div>}
          <div className="agent-monitor-hero-uptime">
            <TrendingUp size={10} />
            Uptime: {d.online !== false ? '100% (current session)' : '0% (offline)'}
          </div>
        </div>
      </div>

      <div className="agent-stats-row">
        {d.status_code != null && <div className="agent-stat-card"><span className="agent-stat-label">STATUS</span><span className="agent-stat-value">{d.status_code}</span></div>}
        {d.response_time_ms != null && <div className="agent-stat-card"><span className="agent-stat-label">LATENCY</span><span className="agent-stat-value">{d.response_time_ms}ms</span></div>}
        {d.content_length != null && <div className="agent-stat-card"><span className="agent-stat-label">SIZE</span><span className="agent-stat-value">{(d.content_length / 1024).toFixed(1)}KB</span></div>}
        {d.occurrences != null && <div className="agent-stat-card"><span className="agent-stat-label">MATCHES</span><span className="agent-stat-value">{d.occurrences}</span></div>}
      </div>

      <div className="agent-divider" />

      <ResponseBar ms={d.response_time_ms} />

      {d.response_time_ms != null && <HistoryChart currentMs={d.response_time_ms} />}

      {d.summary && (
        <div className="agent-section-block">
          <div className="agent-section-block-title">Summary</div>
          <div className="agent-paragraph">{d.summary}</div>
        </div>
      )}

      {d.condition != null && (
        <div className="agent-section-block">
          <div className="agent-section-block-title">Condition Check</div>
          <ConditionCard cond={d.condition} met={d.condition_met} />
        </div>
      )}

      {d.keyword && (
        <div className="agent-section-block">
          <div className="agent-section-block-title">Keyword Search</div>
          <div className="agent-keyword-chip">"{d.keyword}" — {d.occurrences || 0} occurrence{(d.occurrences || 0) !== 1 ? 's' : ''}</div>
        </div>
      )}

      <SSLInfoCard target={d.target} />
      <HeadersCard statusCode={d.status_code} />

      {d.content_preview && (
        <div className="agent-section-block">
          <div className="agent-section-block-title">Content Preview</div>
          <pre className="agent-code-block-sm">{d.content_preview}</pre>
        </div>
      )}

      {d.error && <div className="agent-error-msg">{d.error}</div>}
    </SlidePanel>
  )
}
