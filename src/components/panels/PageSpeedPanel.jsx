import { useState } from 'react'
import SlidePanel from '../SlidePanel'

function downloadBlob(content, filename, mime) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function formatJSON(data) {
  return JSON.stringify({
    url: data.url,
    strategy: data.strategy,
    scores: data.scores,
    vitals: data.vitals,
    opportunities: data.opportunities,
    passed_audits: data.passed_audits,
    total_audits: data.total_audits,
  }, null, 2)
}

function formatMarkdown(data) {
  const { scores = {}, vitals = {}, opportunities = [], passed_audits = [], url, strategy } = data
  let md = `# PageSpeed Insights Report\n\n`
  md += `**URL:** ${url}\n`
  md += `**Strategy:** ${strategy || 'desktop'}\n\n`
  md += `## Scores\n\n`
  md += `| Category | Score |\n| --- | ---: |\n`
  md += `| SEO | ${scores.seo ?? 0}% |\n`
  md += `| Performance | ${scores.performance ?? 0}% |\n`
  md += `| Accessibility | ${scores.accessibility ?? 0}% |\n`
  md += `| Best Practices | ${scores.best_practices ?? 0}% |\n\n`
  md += `## Core Web Vitals\n\n`
  md += `| Metric | Value |\n| --- | ---: |\n`
  for (const [k, v] of Object.entries(vitals)) {
    md += `| ${k.toUpperCase()} | ${v} |\n`
  }
  if (opportunities.length > 0) {
    md += `\n## Optimization Opportunities (${opportunities.length})\n\n`
    opportunities.forEach((o, i) => {
      md += `${i + 1}. **${o.title}** — impact: -${o.score_impact}pt\n`
      if (o.issue) md += `   ${o.issue}\n`
    })
  }
  if (passed_audits.length > 0) {
    md += `\n## Passed Audits (${passed_audits.length})\n\n`
    passed_audits.forEach((t) => { md += `- ${t}\n` })
  }
  return md
}

function formatHTML(data) {
  const { scores, vitals, opportunities = [], passed_audits = [], url, strategy } = data
  const scoreColor = (v) => v >= 90 ? '#00ff88' : v >= 50 ? '#ffaa00' : '#ff3355'
  let h = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>PageSpeed Report</title>`
  h += `<style>body{font-family:monospace;background:#0a0a0f;color:#e0e0e0;padding:20px;max-width:800px;margin:0 auto}`
  h += `h1{color:#00f0ff;border-bottom:1px solid #1e1e2e;padding-bottom:8px}`
  h += `h2{color:#00f0ff;margin-top:24px}`
  h += `.score{display:inline-block;padding:2px 8px;font-weight:700;border-radius:2px}`
  h += `table{width:100%;border-collapse:collapse;margin:8px 0}`
  h += `td,th{border:1px solid #1e1e2e;padding:6px 10px;text-align:left;font-size:13px}`
  h += `th{color:#666680;text-transform:uppercase;font-size:11px}`
  h += `.pass{color:#00ff88}.fail{color:#ff3355}.warn{color:#ffaa00}`
  h += `.opp{border:1px solid #1e1e2e;padding:10px;margin:6px 0;background:#0a0a0f/40}`
  h += `.opp-title{font-weight:700;color:#fff}.opp-impact{color:#ff3355;float:right}`
  h += `</style></head><body>`
  h += `<h1>PageSpeed Insights Report</h1>`
  h += `<p style="color:#666680">${url} &nbsp;|&nbsp; ${strategy || 'desktop'}</p>`
  h += `<h2>Scores</h2><table>`
  for (const [k, v] of Object.entries(scores)) {
    h += `<tr><td>${k.replace(/_/g, ' ').toUpperCase()}</td><td><span class="score" style="background:${scoreColor(v)}20;color:${scoreColor(v)}">${v}%</span></td></tr>`
  }
  h += `</table><h2>Core Web Vitals</h2><table>`
  for (const [k, v] of Object.entries(vitals)) {
    h += `<tr><td>${k.toUpperCase()}</td><td>${v}</td></tr>`
  }
  h += `</table>`
  if (opportunities.length > 0) {
    h += `<h2>Optimization Opportunities (${opportunities.length})</h2>`
    opportunities.forEach((o) => {
      h += `<div class="opp"><span class="opp-title">${o.title}</span> <span class="opp-impact">-${o.score_impact}pt</span>`
      if (o.issue) h += `<br><span style="color:#b0b0cc;font-size:12px">${o.issue}</span>`
      h += `</div>`
    })
  }
  if (passed_audits.length > 0) {
    h += `<h2>Passed Audits (${passed_audits.length})</h2><ul>`
    passed_audits.forEach((t) => { h += `<li style="color:#00ff88">${t}</li>` })
    h += `</ul>`
  }
  h += `</body></html>`
  return h
}

function HealthBar({ passed, total }) {
  const fail = total - passed
  const pct = total > 0 ? (passed / total) * 100 : 0
  return (
    <div className="bg-[#0a0a0f] border border-[#1e1e2e] p-3">
      <div className="flex justify-between text-[10px] text-[#666680] mb-2">
        <span className="text-[#00f0ff] tracking-widest uppercase font-bold">Audit Health</span>
        <span>{passed}/{total} passed</span>
      </div>
      <div className="relative h-2 bg-[#1e1e2e] rounded-none overflow-hidden">
        <div className="absolute inset-0 flex">
          <div style={{ width: `${pct}%` }} className="h-full bg-[#00ff88] transition-all duration-1000 ease-out" />
          {fail > 0 && <div style={{ width: `${100 - pct}%` }} className="h-full bg-[#ff3355] transition-all duration-1000 ease-out delay-200" />}
        </div>
      </div>
      <div className="flex justify-between text-[9px] mt-1">
        <span className="text-[#00ff88]">{Math.round(pct)}% passed</span>
        {fail > 0 && <span className="text-[#ff3355]">{fail} failed</span>}
      </div>
    </div>
  )
}

function ScoreBar({ label, value }) {
  const color = value >= 90 ? '#00ff88' : value >= 50 ? '#ffaa00' : '#ff3355'
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-[#b0b0cc] w-24 shrink-0 uppercase tracking-wider font-medium">{label}</span>
      <div className="flex-1 h-[6px] bg-[#1e1e2e] rounded-none relative overflow-hidden">
        <div className="absolute inset-y-0 left-0 rounded-none transition-all duration-1000 ease-out" style={{ width: `${value}%`, backgroundColor: color }} />
      </div>
      <span className="text-[11px] font-bold w-8 text-right" style={{ color }}>{value}</span>
    </div>
  )
}

function RadarChart({ scores }) {
  const size = 140, cx = size / 2, cy = size / 2, radius = 55
  const categories = [
    { key: 'seo', label: 'SEO', angle: -90 },
    { key: 'performance', label: 'PERF', angle: 0 },
    { key: 'accessibility', label: 'A11Y', angle: 90 },
    { key: 'best_practices', label: 'BP', angle: 180 },
  ]
  const toRad = (deg) => (deg * Math.PI) / 180
  const gridCircles = [0.25, 0.5, 0.75, 1.0]
  const gridLines = categories.map((c) => {
    const rad = toRad(c.angle)
    return { x1: cx, y1: cy, x2: cx + radius * Math.cos(rad), y2: cy + radius * Math.sin(rad) }
  })
  const dataPoints = categories.map((c) => {
    const val = (scores[c.key] || 0) / 100
    const rad = toRad(c.angle)
    return { x: cx + radius * val * Math.cos(rad), y: cy + radius * val * Math.sin(rad), label: c.label, score: scores[c.key] || 0 }
  })
  const polyPoints = dataPoints.map((p) => `${p.x},${p.y}`).join(' ')

  return (
    <div className="bg-[#0a0a0f] border border-[#1e1e2e] p-3 flex flex-col items-center">
      <span className="text-[10px] text-[#00f0ff] mb-1 tracking-widest uppercase font-bold self-start">Score Radar</span>
      <svg width="140" height="140" viewBox={`0 0 ${size} ${size}`}>
        {gridCircles.map((r, i) => (
          <circle key={i} cx={cx} cy={cy} r={radius * r} fill="none" stroke="#1e1e2e" strokeWidth="0.5" />
        ))}
        {gridLines.map((l, i) => (
          <line key={i} {...l} stroke="#1e1e2e" strokeWidth="0.5" />
        ))}
        <polygon points={polyPoints} fill="#00f0ff" fillOpacity="0.1" stroke="#00f0ff" strokeWidth="1.2"
          className="transition-all duration-1000 ease-out" />
        {dataPoints.map((p, i) => (
          <g key={i}>
            <circle cx={p.x} cy={p.y} r="3" fill="#00f0ff" fillOpacity="0.8" />
            <text x={p.x + 6} y={p.y + 2} fill="#666680" fontSize="7" fontFamily="monospace">{p.score}</text>
          </g>
        ))}
        {categories.map((c, i) => {
          const rad = toRad(c.angle)
          const lx = cx + (radius + 12) * Math.cos(rad)
          const ly = cy + (radius + 12) * Math.sin(rad)
          return <text key={i} x={lx} y={ly} textAnchor="middle" dominantBaseline="middle" fill="#666680" fontSize="7" fontFamily="monospace">{c.label}</text>
        })}
      </svg>
    </div>
  )
}

function VitalBadge({ label, value, status }) {
  const dotColor = status === 'pass' ? '#00ff88' : status === 'warn' ? '#ffaa00' : '#ff3355'
  const statusText = status === 'pass' ? 'PASS' : status === 'warn' ? 'WARN' : 'FAIL'
  return (
    <div className="p-2 border border-[#1e1e2e] bg-[#12121a]">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[9px] text-[#666680]">{label}</span>
        <span className="text-[8px] font-bold uppercase" style={{ color: dotColor }}>{statusText}</span>
      </div>
      <div className="text-white font-bold text-xs" style={{ color: dotColor }}>{value}</div>
      <div className="flex items-center gap-1 mt-1">
        <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: dotColor }} />
        <span className="text-[8px] text-[#444450]">{label === 'LCP' ? '< 2.5s' : label === 'CLS' ? '< 0.1' : '< 200ms'}</span>
      </div>
    </div>
  )
}

function getVitalStatus(label, value) {
  if (value === 'N/A') return 'warn'
  const num = parseFloat(value)
  if (isNaN(num)) return 'warn'
  if (label === 'LCP') return num <= 2.5 ? 'pass' : num <= 4 ? 'warn' : 'fail'
  if (label === 'CLS') return num <= 0.1 ? 'pass' : num <= 0.25 ? 'warn' : 'fail'
  if (label === 'TBT') return num <= 200 ? 'pass' : num <= 600 ? 'warn' : 'fail'
  if (label === 'FCP') return num <= 1.8 ? 'pass' : num <= 3 ? 'warn' : 'fail'
  if (label === 'SI') return num <= 3.4 ? 'pass' : num <= 5.8 ? 'warn' : 'fail'
  return 'warn'
}

export default function PageSpeedPanel({ visible, data, onClose }) {
  const [selectedIssue, setSelectedIssue] = useState(null)
  const [showPassed, setShowPassed] = useState(false)

  if (!data) return null
  if (data.error) {
    return (
      <SlidePanel visible={visible} direction="right" title="PAGESPEED INSIGHTS"
        accentColor="#00f0ff" onClose={onClose} autoDismissMs={0}>
        <div className="flex items-center justify-center h-full text-[#ff3355] text-xs p-6">{data.error}</div>
      </SlidePanel>
    )
  }

  const { scores = {}, vitals = {}, opportunities = [], passed_audits = [], total_audits = 0, strategy, url } = data
  const totalOpportunities = opportunities.length
  const totalPassed = passed_audits.length
  const totalAudited = total_audits || totalOpportunities + totalPassed

  return (
    <SlidePanel visible={visible} direction="right" title="PAGESPEED INSIGHTS"
      accentColor="#00f0ff" onClose={onClose} autoDismissMs={0}>
      <div className="p-4 space-y-3 font-mono text-[#e0e0e0] select-none custom-scrollbar" style={{ maxHeight: 'calc(100vh - 60px)', overflowY: 'auto' }}>

        {/* URL + Strategy */}
        <div className="text-[10px] text-[#666680] truncate">{url}</div>
        <div className="flex items-center gap-2">
          <span className="text-[9px] text-[#00f0ff] uppercase tracking-wider">Strategy: {strategy || 'desktop'}</span>
        </div>

        {/* Health Bar */}
        <HealthBar passed={totalPassed} total={totalAudited} />

        {/* Score Bars */}
        <div className="bg-[#0a0a0f] border border-[#1e1e2e] p-3 space-y-2">
          <span className="text-[10px] text-[#00f0ff] tracking-widest uppercase font-bold">Category Scores</span>
          <ScoreBar label="SEO" value={scores.seo} />
          <ScoreBar label="Performance" value={scores.performance} />
          <ScoreBar label="Accessibility" value={scores.accessibility} />
          <ScoreBar label="Best Practices" value={scores.best_practices} />
        </div>

        {/* Radar + Vitals row */}
        <div className="grid grid-cols-2 gap-3">
          <RadarChart scores={scores} />
          <div className="space-y-2">
            <div className="bg-[#0a0a0f] border border-[#1e1e2e] p-3">
              <span className="text-[10px] text-[#00f0ff] tracking-widest uppercase font-bold block mb-2">Core Web Vitals</span>
              <div className="space-y-2">
                <VitalBadge label="LCP" value={vitals.lcp} status={getVitalStatus('LCP', vitals.lcp)} />
                <VitalBadge label="CLS" value={vitals.cls} status={getVitalStatus('CLS', vitals.cls)} />
                <VitalBadge label="TBT" value={vitals.tbt} status={getVitalStatus('TBT', vitals.tbt)} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <VitalBadge label="FCP" value={vitals.fcp} status={getVitalStatus('FCP', vitals.fcp)} />
              <VitalBadge label="SI" value={vitals.si} status={getVitalStatus('SI', vitals.si)} />
            </div>
          </div>
        </div>

        {/* Opportunities */}
        <div>
          <div className="text-[11px] text-[#666680] font-bold uppercase tracking-wider mb-2">
            Optimization Opportunities ({totalOpportunities})
          </div>
          <div className="space-y-2 max-h-[280px] overflow-y-auto custom-scrollbar pr-1">
            {totalOpportunities === 0 ? (
              <div className="text-[#00ff88] text-xs text-center py-6 border border-dashed border-[#00ff88]/20 bg-[#00ff88]/5">
                Excellent! No critical issues found.
              </div>
            ) : (
              opportunities.map((opp, i) => {
                const severity = opp.score_impact >= 90 ? 'CRITICAL' : opp.score_impact >= 50 ? 'MAJOR' : 'MINOR'
                const sevColor = opp.score_impact >= 90 ? '#ff3355' : opp.score_impact >= 50 ? '#ffaa00' : '#ffaa00'
                const sevBg = opp.score_impact >= 90 ? '#ff3355/10' : opp.score_impact >= 50 ? '#ffaa00/10' : '#00f0ff/10'
                return (
                  <div key={i}
                    className={`border transition-all ${selectedIssue === i ? 'border-[#00f0ff] bg-[#161622]' : 'border-[#1e1e2e] bg-[#0a0a0f]/40'} cursor-pointer`}
                    onClick={() => setSelectedIssue(selectedIssue === i ? null : i)}>
                    <div className="p-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-bold px-1" style={{ color: sevColor }}>{severity}</span>
                        <span className="text-[#ff3355] text-[10px] font-bold">-{opp.score_impact}pt</span>
                      </div>
                      <div className="flex items-center gap-2 text-xs">
                        <span className="font-medium text-white truncate max-w-[280px]">{opp.title}</span>
                      </div>
                      {/* Mini severity bar */}
                      <div className="mt-1.5 h-1 bg-[#1e1e2e] rounded-none overflow-hidden">
                        <div className="h-full transition-all duration-700 ease-out" style={{ width: `${opp.score_impact}%`, backgroundColor: sevColor, opacity: 0.6 }} />
                      </div>
                    </div>
                    {selectedIssue === i && (
                      <div className="p-3 bg-[#0a0a0f] border-t border-[#1e1e2e] text-[11px] text-[#b0b0cc] space-y-2 leading-relaxed">
                        <p>{opp.issue}</p>
                        <div className="pt-2 border-t border-[#1e1e2e]/60 text-[10px] text-[#666680]">
                          developer.chrome.com/docs/lighthouse
                        </div>
                      </div>
                    )}
                  </div>
                )
              })
            )}
          </div>
        </div>

        {/* Passed Audits */}
        {totalPassed > 0 && (
          <div>
            <button onClick={() => setShowPassed(!showPassed)}
              className="text-[11px] text-[#00ff88] font-bold uppercase tracking-wider hover:text-[#00ffaa] transition-colors w-full text-left">
              {showPassed ? '▾' : '▸'} Passed Audits ({totalPassed})
            </button>
            {showPassed && (
              <div className="mt-2 space-y-1 max-h-[200px] overflow-y-auto custom-scrollbar">
                {passed_audits.map((title, i) => (
                  <div key={i} className="text-[11px] text-[#666680] border-l-2 border-[#00ff88]/30 pl-2 py-1">
                    {title}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Export Buttons */}
        <div className="border-t border-[#1e1e2e] pt-3 mt-3">
          <span className="text-[10px] text-[#00f0ff] tracking-widest uppercase font-bold block mb-2">Export Report</span>
          <div className="grid grid-cols-3 gap-2">
            <button onClick={() => downloadBlob(formatJSON(data), `pagespeed-${data.url?.replace(/[^a-z0-9]/gi,'_')}.json`, 'application/json')}
              className="bg-[#1e1e2e] hover:bg-[#2a2a3a] border border-[#2a2a3a] text-[10px] text-white py-2 transition-all font-bold uppercase tracking-wider">
              JSON
            </button>
            <button onClick={() => downloadBlob(formatMarkdown(data), `pagespeed-${data.url?.replace(/[^a-z0-9]/gi,'_')}.md`, 'text/markdown')}
              className="bg-[#1e1e2e] hover:bg-[#2a2a3a] border border-[#2a2a3a] text-[10px] text-white py-2 transition-all font-bold uppercase tracking-wider">
              MD
            </button>
            <button onClick={() => downloadBlob(formatHTML(data), `pagespeed-${data.url?.replace(/[^a-z0-9]/gi,'_')}.html`, 'text/html')}
              className="bg-[#1e1e2e] hover:bg-[#2a2a3a] border border-[#2a2a3a] text-[10px] text-white py-2 transition-all font-bold uppercase tracking-wider">
              HTML
            </button>
          </div>
        </div>
      </div>
    </SlidePanel>
  )
}
