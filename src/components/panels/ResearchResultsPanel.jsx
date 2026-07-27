import { useState } from 'react'
import { FileText, ExternalLink, ChevronDown, ChevronRight, BarChart3, Download, X, Quote } from 'lucide-react'
import SlidePanel from '../SlidePanel'
import BarChartCard from '../charts/BarChartCard'
import PieChartCard from '../charts/PieChartCard'
import LineChartCard from '../charts/LineChartCard'

function SourceCard({ source, index }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="border border-[#1e1e2e] bg-[#0a0a0f]/40 cursor-pointer hover:border-[#2a2a3a] transition-all"
      onClick={() => setExpanded(!expanded)}>
      <div className="p-2 flex items-start gap-2">
        <span className="text-[#666680] text-[9px] w-4 shrink-0 mt-0.5">{index + 1}</span>
        <div className="min-w-0 flex-1">
          <div className="text-[10px] text-white font-bold truncate">{source.title}</div>
          <div className="text-[8px] text-[#666680] truncate mt-0.5">{source.url}</div>
          {expanded && source.snippet && (
            <div className="text-[9px] text-[#b0b0cc] mt-1.5 leading-relaxed border-t border-[#1e1e2e] pt-1.5">{source.snippet}</div>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {expanded ? <ChevronDown size={10} className="text-[#666680]" /> : <ChevronRight size={10} className="text-[#666680]" />}
          {source.url && (
            <a href={source.url} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}
              className="text-[#00f0ff] hover:text-white transition-colors"><ExternalLink size={10} /></a>
          )}
        </div>
      </div>
    </div>
  )
}

function ChartRenderer({ chart, index }) {
  switch (chart.type) {
    case 'bar': return <BarChartCard key={index} title={chart.title} labels={chart.labels} values={chart.values} />
    case 'pie': return <PieChartCard key={index} title={chart.title} data={chart.labels.map((l, i) => ({ name: l, value: chart.values[i] || 0 }))} />
    case 'line': return <LineChartCard key={index} title={chart.title} labels={chart.labels} values={chart.values} />
    default: return null
  }
}

export default function ResearchResultsPanel({ visible, data, onClose }) {
  const [showAllSources, setShowAllSources] = useState(false)
  const [activeTab, setActiveTab] = useState('findings')

  if (!data) return null
  if (data.error) {
    return (
      <SlidePanel visible={visible} direction="right" title="RESEARCH" icon={<FileText size={11} />}
        accentColor="#ff3355" onClose={onClose} autoDismissMs={0}>
        <div className="flex items-center justify-center h-full text-[#ff3355] text-xs p-6">{data.error}</div>
      </SlidePanel>
    )
  }

  const { topic, depth, sources_count, pages_read, search_results = [], synthesis, has_charts, chart_data = [] } = data
  const synthesisObj = typeof synthesis === 'object' ? synthesis : null
  const findings = synthesisObj?.key_findings || []
  const statistics = synthesisObj?.statistics || []
  const quotes = synthesisObj?.quotes || []
  const summary = synthesisObj?.summary || ''
  const displaySources = showAllSources ? search_results : search_results.slice(0, 5)

  const tabs = [
    { id: 'findings', label: 'Findings' },
    { id: 'sources', label: `Sources (${sources_count})` },
    { id: 'charts', label: `Charts (${chart_data.length})`, disabled: !has_charts },
  ]

  function downloadMarkdown() {
    let md = `# Research: ${topic}\n\n`
    md += `**Depth:** ${depth} | **Sources:** ${sources_count} | **Pages read:** ${pages_read}\n\n`
    if (summary) md += `## Summary\n\n${summary}\n\n`
    if (findings.length) {
      md += `## Key Findings\n\n`
      findings.forEach(f => { md += `- ${f.finding || ''} ${f.source_url ? `— ${f.source_url}` : ''}\n` })
      md += '\n'
    }
    if (statistics.length) {
      md += `## Statistics\n\n`
      statistics.forEach(s => { md += `- ${s.label || ''}: ${s.value || ''} ${s.source_url ? `— ${s.source_url}` : ''}\n` })
      md += '\n'
    }
    md += `## Sources\n\n`
    search_results.forEach(s => { md += `- [${s.title || 'Link'}](${s.url})\n` })
    const blob = new Blob([md], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = `${topic.replace(/[^a-z0-9]/gi, '_')}.md`; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <SlidePanel visible={visible} direction="right" title="RESEARCH" icon={<FileText size={11} />}
      accentColor="#00f0ff" onClose={onClose} autoDismissMs={0}>
      <div className="p-4 space-y-3 font-mono text-[#e0e0e0] select-none custom-scrollbar" style={{ maxHeight: 'calc(100vh - 60px)', overflowY: 'auto' }}>
        <div className="text-[12px] text-white font-bold">{topic}</div>
        <div className="flex items-center gap-3 text-[9px] text-[#666680] uppercase tracking-wider">
          <span className={`px-1.5 py-0.5 text-[8px] font-bold ${depth === 'deep' ? 'bg-[#ff3355]/10 text-[#ff3355]' : depth === 'normal' ? 'bg-[#ffaa00]/10 text-[#ffaa00]' : 'bg-[#00ff88]/10 text-[#00ff88]'}`}>{depth}</span>
          <span>{sources_count} sources</span>
          <span>{pages_read} pages read</span>
        </div>
        <div className="flex border-b border-[#1e1e2e]">
          {tabs.filter(t => !t.disabled).map(t => (
            <button key={t.id} onClick={() => setActiveTab(t.id)}
              className={`px-3 py-2 text-[10px] uppercase tracking-wider font-bold border-b-2 transition-all ${activeTab === t.id ? 'border-[#00f0ff] text-[#00f0ff]' : 'border-transparent text-[#666680] hover:text-[#b0b0cc]'}`}>
              {t.label}
            </button>
          ))}
        </div>
        {activeTab === 'findings' && (
          <div className="space-y-3">
            {summary && <div className="text-[11px] text-[#e0e0e0] leading-relaxed">{summary}</div>}
            {findings.length > 0 && (
              <div>
                <div className="text-[10px] text-[#00f0ff] uppercase tracking-widest font-bold mb-2">Key Findings</div>
                <div className="space-y-1">
                  {findings.map((f, i) => (
                    <div key={i} className="flex gap-2 text-[10px] border-l-2 border-[#00f0ff]/30 pl-2 py-1">
                      <span className="text-[#00f0ff] shrink-0">◆</span>
                      <span className="text-[#b0b0cc]">{f.finding || ''}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {statistics.length > 0 && (
              <div>
                <div className="text-[10px] text-[#00ff88] uppercase tracking-widest font-bold mb-2">Statistics</div>
                <div className="grid grid-cols-2 gap-2">
                  {statistics.map((s, i) => (
                    <div key={i} className="bg-[#0a0a0f] border border-[#1e1e2e] p-2">
                      <div className="text-[8px] text-[#666680] uppercase">{s.label || ''}</div>
                      <div className="text-[13px] text-white font-bold mt-0.5">{s.value || ''}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {quotes.length > 0 && (
              <div>
                <div className="flex items-center gap-1 text-[10px] text-[#ffaa00] uppercase tracking-widest font-bold mb-2">
                  <Quote size={10} /> Notable Quotes
                </div>
                {quotes.map((q, i) => (
                  <div key={i} className="border-l-2 border-[#ffaa00]/30 pl-2 py-1 text-[10px] text-[#b0b0cc] italic mb-1">
                    "{q.quote || ''}"
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        {activeTab === 'sources' && (
          <div className="space-y-1">
            {displaySources.map((s, i) => <SourceCard key={i} source={s} index={i} />)}
            {search_results.length > 5 && (
              <button onClick={() => setShowAllSources(!showAllSources)}
                className="text-[10px] text-[#00f0ff] uppercase tracking-wider font-bold hover:text-white transition-colors w-full text-center py-2">
                {showAllSources ? 'Show less' : `Show all ${search_results.length} sources`}
              </button>
            )}
          </div>
        )}
        {activeTab === 'charts' && chart_data.length > 0 && (
          <div className="space-y-3">
            {chart_data.map((c, i) => <ChartRenderer key={i} chart={c} index={i} />)}
          </div>
        )}
        <div className="flex gap-2 border-t border-[#1e1e2e] pt-3">
          <button onClick={downloadMarkdown}
            className="flex items-center gap-1 bg-[#1e1e2e] hover:bg-[#2a2a3a] border border-[#1e1e2e] text-[10px] text-white px-3 py-2 uppercase tracking-wider font-bold transition-all">
            <Download size={10} /> Export MD
          </button>
          <button onClick={onClose} className="flex items-center gap-1 text-[#666680] hover:text-white text-[10px] px-2 transition-all ml-auto">
            <X size={10} /> Close
          </button>
        </div>
      </div>
    </SlidePanel>
  )
}
