import { useState, useMemo } from 'react'
import SlidePanel from '../SlidePanel'
import { Newspaper, ExternalLink, Clock, Globe, Bookmark, Share2, Filter, ChevronDown, ChevronUp, Eye } from 'lucide-react'

const SOURCE_COLORS = {
  'BBC': { color: '#ff0050', bg: 'rgba(255,0,80,0.08)' },
  'CNN': { color: '#cc0000', bg: 'rgba(204,0,0,0.08)' },
  'Reuters': { color: '#ff8000', bg: 'rgba(255,128,0,0.08)' },
  'AP': { color: '#0057b7', bg: 'rgba(0,87,183,0.08)' },
  'New York Times': { color: '#000000', bg: 'rgba(0,0,0,0.08)' },
  'Guardian': { color: '#052962', bg: 'rgba(5,41,98,0.08)' },
  'Al Jazeera': { color: '#003366', bg: 'rgba(0,51,102,0.08)' },
  'Bloomberg': { color: '#002137', bg: 'rgba(0,33,55,0.08)' },
  'Fox News': { color: '#003366', bg: 'rgba(0,51,102,0.08)' },
  'NPR': { color: '#003366', bg: 'rgba(0,51,102,0.08)' },
  'Sky News': { color: '#003399', bg: 'rgba(0,51,153,0.08)' },
}

function SourceBadge({ source, size }) {
  const key = Object.keys(SOURCE_COLORS).find(k => (source || '').toLowerCase().includes(k.toLowerCase()))
  const { color, bg } = key ? SOURCE_COLORS[key] : { color: '#6b7280', bg: 'rgba(107,114,128,0.08)' }
  return (
    <span className="agent-news-source-badge" style={{ borderColor: color, color, backgroundColor: bg }}>
      {source || 'Unknown'}
    </span>
  )
}

function RelativeTime({ dateStr }) {
  if (!dateStr) return null
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return <span className="agent-news-date">{dateStr}</span>
    const now = new Date()
    const diffMs = now - d
    const diffMin = Math.floor(diffMs / 60000)
    const diffHrs = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)
    let label = ''
    if (diffMin < 1) label = 'Just now'
    else if (diffMin < 60) label = `${diffMin}m ago`
    else if (diffHrs < 24) label = `${diffHrs}h ago`
    else if (diffDays < 2) label = 'Yesterday'
    else if (diffDays < 7) label = `${diffDays}d ago`
    else label = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    return (
      <span className="agent-news-date" title={d.toLocaleString()}>
        <Clock size={9} />
        {label}
      </span>
    )
  } catch { return null }
}

function SentimentDot({ text }) {
  const score = useMemo(() => {
    if (!text) return 0
    const positive = ['up', 'rise', 'gain', 'growth', 'success', 'win', 'positive', 'good', 'great', 'breakthrough', 'record'].filter(w => text.toLowerCase().includes(w)).length
    const negative = ['down', 'fall', 'drop', 'loss', 'fail', 'crisis', 'negative', 'bad', 'crash', 'war', 'conflict', 'death'].filter(w => text.toLowerCase().includes(w)).length
    if (positive > negative) return 1
    if (negative > positive) return -1
    return 0
  }, [text])

  const colors = { '-1': '#ef4444', '0': '#6b7280', '1': '#22c55e' }
  const labels = { '-1': 'Negative', '0': 'Neutral', '1': 'Positive' }

  return (
    <span className="agent-news-sentiment" style={{ color: colors[score] }} title={labels[score]}>
      <span className="agent-news-sentiment-dot" style={{ backgroundColor: colors[score] }} />
    </span>
  )
}

function ArticleCard({ article, index }) {
  const [expanded, setExpanded] = useState(false)
  const [bookmarked, setBookmarked] = useState(false)
  const readTime = Math.max(1, Math.ceil((article.description || '').split(' ').length / 200))

  return (
    <div className={`agent-news-card ${expanded ? 'expanded' : ''}`}>
      <div className="agent-news-card-main" onClick={() => setExpanded(!expanded)}>
        <div className="agent-news-card-rank">{index + 1}</div>
        <div className="agent-news-card-body">
          <div className="agent-news-card-top">
            <SourceBadge source={article.source} />
            <RelativeTime dateStr={article.published} />
            <SentimentDot text={article.title + ' ' + (article.description || '')} />
          </div>
          <div className="agent-news-card-title">{article.title || 'Untitled'}</div>
          {expanded && article.description && (
            <div className="agent-news-card-desc">{article.description}</div>
          )}
          <div className="agent-news-card-meta">
            <span className="agent-news-card-readtime"><Eye size={9} />{readTime} min</span>
          </div>
        </div>
        <div className="agent-news-card-actions">
          <button className="agent-news-action-btn" onClick={(e) => { e.stopPropagation(); setBookmarked(!bookmarked) }}>
            <Bookmark size={11} style={{ fill: bookmarked ? '#ffe2ab' : 'none' }} />
          </button>
          {article.url && (
            <button className="agent-news-action-btn" onClick={(e) => { e.stopPropagation(); window.open(article.url, '_blank') }}>
              <ExternalLink size={11} />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function CategoryFilter({ categories, active, onSelect }) {
  return (
    <div className="agent-news-filters">
      <Filter size={10} />
      {categories.map((cat, i) => (
        <button key={i} className={`agent-news-filter-btn ${active === cat ? 'active' : ''}`} onClick={() => onSelect(active === cat ? null : cat)}>
          {cat}
        </button>
      ))}
    </div>
  )
}

export default function NewsPanel({ visible, data, onClose }) {
  const d = data?.result || data || {}
  const articles = d.articles || []
  const query = d.query || ''
  const [activeCategory, setActiveCategory] = useState(null)
  const [showCount, setShowCount] = useState(8)

  const categories = useMemo(() => {
    const cats = new Set()
    articles.forEach(a => {
      const src = (a.source || '').toLowerCase()
      if (['bbc', 'cnn', 'reuters', 'ap', 'npr'].includes(src)) cats.add('Major')
      else if (['techcrunch', 'the verge', 'wired', 'ars technica', 'zdnet'].some(t => src.includes(t))) cats.add('Tech')
      else cats.add('Other')
    })
    return ['Major', 'Tech', 'Other'].filter(c => cats.has(c))
  }, [articles])

  const filtered = useMemo(() => {
    let list = articles
    if (activeCategory === 'Major') list = list.filter(a => ['bbc', 'cnn', 'reuters', 'ap', 'npr'].some(s => (a.source || '').toLowerCase().includes(s)))
    if (activeCategory === 'Tech') list = list.filter(a => ['techcrunch', 'the verge', 'wired', 'ars technica', 'zdnet'].some(s => (a.source || '').toLowerCase().includes(s)))
    if (activeCategory === 'Other') list = list.filter(a => !['bbc', 'cnn', 'reuters', 'ap', 'npr', 'techcrunch', 'the verge', 'wired', 'ars technica', 'zdnet'].some(s => (a.source || '').toLowerCase().includes(s)))
    return list
  }, [articles, activeCategory])

  return (
    <SlidePanel visible={visible} direction="bottom" title="NEWS" icon={<Newspaper size={11} />} accentColor="#ffe2ab" onClose={onClose} autoDismissMs={0}>
      <div className="agent-news-header">
        <div className="agent-news-header-left">
          <div className="agent-news-header-icon"><Globe size={18} /></div>
          <div>
            <div className="agent-news-header-title">{query ? `News: ${query}` : 'Latest Headlines'}</div>
            <div className="agent-news-header-sub">{articles.length} articles · {activeCategory || 'All sources'}</div>
          </div>
        </div>
      </div>

      {categories.length > 1 && (
        <CategoryFilter categories={categories} active={activeCategory} onSelect={setActiveCategory} />
      )}

      <div className="agent-divider" />

      {filtered.length === 0 ? (
        <div className="agent-empty">No articles match this filter</div>
      ) : (
        <div className="agent-news-list">
          {filtered.slice(0, showCount).map((a, i) => (
            <ArticleCard key={i} article={a} index={i} />
          ))}
        </div>
      )}

      {filtered.length > showCount && (
        <button className="agent-expand-btn" onClick={() => setShowCount(showCount + 8)}>
          <ChevronDown size={12} />
          Show {Math.min(8, filtered.length - showCount)} more of {filtered.length}
        </button>
      )}
      {showCount > 8 && filtered.length <= showCount && (
        <button className="agent-expand-btn" onClick={() => setShowCount(8)}>
          <ChevronUp size={12} />
          Show fewer
        </button>
      )}
    </SlidePanel>
  )
}
