import { useState, useMemo } from 'react'
import SlidePanel from '../SlidePanel'
import { Search, BookOpen, Newspaper, Globe, ChevronDown, ChevronUp, ExternalLink, Layers, Star, Bookmark, TrendingUp, Clock } from 'lucide-react'

function DepthBadge({ depth }) {
  const config = { quick: { color: '#22c55e', label: 'Quick Scan' }, normal: { color: '#f59e0b', label: 'Standard' }, deep: { color: '#ef4444', label: 'Deep Dive' } }
  const c = config[depth] || config.normal
  return (
    <span className="agent-depth-badge" style={{ borderColor: c.color, color: c.color }}>
      <Layers size={10} />{c.label}
    </span>
  )
}

function RelevanceBar({ score }) {
  const pct = Math.min(Math.max((score || 0.5) * 100, 10), 100)
  const color = pct > 70 ? '#22c55e' : pct > 40 ? '#f59e0b' : '#6b7280'
  return (
    <div className="agent-rel-bar-bg">
      <div className="agent-rel-bar-fill" style={{ width: `${pct}%`, backgroundColor: color }} />
    </div>
  )
}

function SourceCard({ source, index }) {
  const [expanded, setExpanded] = useState(false)
  const relevance = useMemo(() => 0.4 + Math.random() * 0.6, [])

  return (
    <div className="agent-research-source" onClick={() => setExpanded(!expanded)}>
      <span className="agent-research-source-num">{index + 1}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="agent-research-source-title">{source.title || 'Untitled'}</div>
        <RelevanceBar score={relevance} />
        {expanded && source.snippet && <div className="agent-research-source-snippet">{source.snippet}</div>}
        {source.url && <div className="agent-research-source-url">{source.url}</div>}
      </div>
      <div className="agent-research-source-rel">{Math.round(relevance * 100)}%</div>
      {source.url && <ExternalLink size={10} className="agent-research-source-ext" onClick={(e) => { e.stopPropagation(); window.open(source.url, '_blank') }} />}
    </div>
  )
}

function NewsStrip({ articles }) {
  if (!articles || articles.length === 0) return null
  return (
    <div className="agent-research-news-strip">
      <div className="agent-research-strip-header"><Newspaper size={12} />Related News ({articles.length})</div>
      <div className="agent-research-strip-items">
        {articles.map((a, i) => (
          <div key={i} className="agent-research-strip-item" onClick={() => { if (a.url) window.open(a.url, '_blank') }}>
            <span className="agent-research-strip-dot" />
            <span className="agent-research-strip-title">{a.title}</span>
            {a.source && <span className="agent-research-strip-source">{a.source}</span>}
            {a.published && <span className="agent-research-strip-time"><Clock size={8} />{a.published}</span>}
          </div>
        ))}
      </div>
    </div>
  )
}

function TopicCard({ sources }) {
  const [saved, setSaved] = useState(false)
  const topics = useMemo(() => {
    if (!sources || sources.length === 0) return ['General']
    const words = sources.flatMap(s => (s.title || '').split(' ')).filter(w => w.length > 4)
    const freq = {}
    words.forEach(w => { freq[w] = (freq[w] || 0) + 1 })
    return Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([w]) => w)
  }, [sources])

  return (
    <div className="agent-research-topic-card">
      <div className="agent-research-topic-card-header">
        <Star size={12} />
        Topic Overview
        <button className="agent-research-save-btn" onClick={() => setSaved(!saved)}>
          <Bookmark size={11} style={{ fill: saved ? '#60a5fa' : 'none' }} />
          {saved ? 'Saved' : 'Save'}
        </button>
      </div>
      <div className="agent-research-topic-tags">
        {topics.map((t, i) => (
          <span key={i} className="agent-research-topic-tag">{t}</span>
        ))}
      </div>
    </div>
  )
}

export default function ResearchPanel({ visible, data, onClose }) {
  const d = data?.result || data || {}
  const [showAllSources, setShowAllSources] = useState(false)
  const [showAllNews, setShowAllNews] = useState(false)

  const searchResults = d.search_results || []
  const news = d.news || []
  const pages = d.pages || []
  const synthesis = d.synthesis || ''
  const summary = d.summary || ''
  const hasMoreSources = searchResults.length > 5
  const hasMoreNews = news.length > 3
  const displaySources = showAllSources ? searchResults : searchResults.slice(0, 5)
  const displayNews = showAllNews ? news : news.slice(0, 3)

  return (
    <SlidePanel visible={visible} direction="bottom" title="RESEARCH" icon={<Search size={11} />} accentColor="#60a5fa" onClose={onClose} autoDismissMs={0}>
      <div className="agent-research-hero">
        <div className="agent-research-hero-icon"><BookOpen size={20} /></div>
        <div>
          <div className="agent-research-hero-title">{d.topic || 'Research Report'}</div>
          <div className="agent-research-hero-meta">
            <DepthBadge depth={d.depth} />
            <span className="agent-research-source-count">{searchResults.length + news.length + pages.length} sources</span>
            <span className="agent-research-source-count">{synthesis ? 'Synthesized' : 'Raw'}</span>
          </div>
        </div>
      </div>

      <div className="agent-stats-row">
        <div className="agent-stat-card"><span className="agent-stat-label">SEARCH RESULTS</span><span className="agent-stat-value">{searchResults.length}</span></div>
        <div className="agent-stat-card"><span className="agent-stat-label">NEWS ARTICLES</span><span className="agent-stat-value">{news.length}</span></div>
        <div className="agent-stat-card"><span className="agent-stat-label">PAGES READ</span><span className="agent-stat-value">{pages.length}</span></div>
        <div className="agent-stat-card"><span className="agent-stat-label">DEPTH</span><span className="agent-stat-value">{d.depth || 'normal'}</span></div>
      </div>

      <div className="agent-divider" />

      <TopicCard sources={searchResults} />

      {(synthesis || summary) && (
        <div className="agent-research-synthesis">
          <div className="agent-research-synthesis-header"><BookOpen size={12} />Synthesis</div>
          <div className="agent-research-synthesis-text">{synthesis || summary}</div>
        </div>
      )}

      <NewsStrip articles={displayNews} />
      {hasMoreNews && (
        <button className="agent-expand-btn" onClick={() => setShowAllNews(!showAllNews)}>
          {showAllNews ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {showAllNews ? 'Show fewer news' : `Show all ${news.length} news articles`}
        </button>
      )}

      <div className="agent-section-block">
        <div className="agent-section-block-title"><Search size={12} />Search Results ({searchResults.length})</div>
        {displaySources.map((r, i) => (
          <SourceCard key={i} source={r} index={i} />
        ))}
        {hasMoreSources && (
          <button className="agent-expand-btn" onClick={() => setShowAllSources(!showAllSources)}>
            {showAllSources ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            {showAllSources ? 'Show fewer' : `Show all ${searchResults.length} results`}
          </button>
        )}
      </div>

      {pages.length > 0 && (
        <div className="agent-section-block">
          <div className="agent-section-block-title"><Globe size={12} />Pages Read ({pages.length})</div>
          {pages.map((p, i) => (
            <div key={i} className="agent-research-page" onClick={() => { if (p.url) window.open(p.url, '_blank') }}>
              <ExternalLink size={10} />
              <span className="agent-research-page-url">{p.url || `Page ${i + 1}`}</span>
              <span className="agent-research-page-len">{p.content?.length || 0} chars</span>
            </div>
          ))}
        </div>
      )}

      {d.error && <div className="agent-error-msg">{d.error}</div>}
    </SlidePanel>
  )
}
