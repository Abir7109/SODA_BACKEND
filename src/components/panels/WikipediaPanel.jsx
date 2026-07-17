import { useState, useMemo } from 'react'
import SlidePanel from '../SlidePanel'
import { BookOpen, ExternalLink, Search, Clock, Hash, Layers, ChevronDown, ChevronUp, Bookmark } from 'lucide-react'

function StatusCard({ label, value, color }) {
  return (
    <div className="agent-stat-card">
      <span className="agent-stat-label">{label}</span>
      <span className="agent-stat-value" style={color ? { color } : {}}>{value}</span>
    </div>
  )
}

function SectionBlock({ title, children, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen !== false)
  return (
    <div className="agent-section-block">
      <div className="agent-section-block-title" onClick={() => setOpen(!open)} style={{ cursor: 'pointer' }}>
        <span>{title}</span>
        {open ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
      </div>
      {open && children}
    </div>
  )
}

function ReadingTime({ text }) {
  const wordCount = (text || '').split(/\s+/).filter(Boolean).length
  const readTime = Math.max(1, Math.ceil(wordCount / 200))
  const pct = Math.min(100, (wordCount / 2000) * 100)
  return (
    <div className="agent-wiki-reading">
      <div className="agent-wiki-reading-header">
        <Clock size={10} />
        <span>{readTime} min read</span>
        <span className="agent-wiki-reading-words">{wordCount} words</span>
      </div>
      <div className="agent-wiki-reading-bar">
        <div className="agent-wiki-reading-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function CategoryTags({ title }) {
  const categories = useMemo(() => {
    if (!title) return []
    const tags = []
    const titleWords = title.split(' ')
    if (titleWords.length > 1) tags.push(titleWords[0])
    if (title.toLowerCase().includes('programming') || title.toLowerCase().includes('language')) tags.push('Technology')
    if (title.toLowerCase().includes('science') || title.toLowerCase().includes('physics')) tags.push('Science')
    if (title.toLowerCase().includes('history') || title.toLowerCase().includes('war')) tags.push('History')
    if (title.toLowerCase().includes('film') || title.toLowerCase().includes('music')) tags.push('Arts')
    if (title.toLowerCase().includes('country') || title.toLowerCase().includes('city')) tags.push('Geography')
    if (title.toLowerCase().includes('person') || title.toLowerCase().includes('president')) tags.push('Biography')
    if (title.toLowerCase().includes('philosophy') || title.toLowerCase().includes('theory')) tags.push('Philosophy')
    if (tags.length === 0) tags.push('Reference')
    return tags
  }, [title])

  return (
    <div className="agent-wiki-tags">
      {categories.map((cat, i) => (
        <span key={i} className="agent-wiki-tag">{cat}</span>
      ))}
    </div>
  )
}

function RelatedTopicsCard({ title }) {
  const [expanded, setExpanded] = useState(false)
  const related = useMemo(() => {
    if (!title) return []
    const t = title.toLowerCase()
    if (t.includes('python')) return ['JavaScript', 'Java', 'C++', 'Ruby', 'TypeScript', 'Go (programming language)', 'Rust (programming language)']
    if (t.includes('javascript')) return ['TypeScript', 'Node.js', 'React (JavaScript library)', 'Angular (web framework)', 'Vue.js']
    if (t.includes('artificial')) return ['Machine learning', 'Deep learning', 'Natural language processing', 'Computer vision', 'Robotics']
    if (t.includes('quantum')) return ['Quantum mechanics', 'Schrödinger equation', 'Quantum entanglement', 'Quantum computing']
    if (t.includes('photosynthesis')) return ['Chloroplast', 'Light-dependent reactions', 'Calvin cycle', 'C3 carbon fixation', 'C4 carbon fixation']
    if (t.includes('world war')) return ['World War I', 'World War II', 'Cold War', 'League of Nations', 'United Nations']
    return []
  }, [title])

  if (related.length === 0) return null

  return (
    <div className="agent-section-block">
      <div className="agent-section-block-title" onClick={() => setExpanded(!expanded)} style={{ cursor: 'pointer' }}>
        <Hash size={10} />
        <span>Related Topics ({related.length})</span>
        {expanded ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
      </div>
      {expanded && (
        <div className="agent-wiki-related">
          {related.map((topic, i) => (
            <div key={i} className="agent-wiki-related-item">{topic}</div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function WikipediaPanel({ visible, data, onClose }) {
  const d = data?.result || data || {}
  const [bookmarked, setBookmarked] = useState(false)

  const extractSections = (extract) => {
    if (!extract) return []
    const lines = extract.split('\n').filter(l => l.trim())
    const sections = []
    let current = { heading: 'Summary', content: [] }
    for (const line of lines) {
      const trimmed = line.trim()
      if (trimmed.endsWith('.') && trimmed.length < 80 && !trimmed.endsWith('..') && /^[A-Z]/.test(trimmed)) {
        sections.push(current)
        current = { heading: trimmed, content: [] }
      } else {
        current.content.push(trimmed)
      }
    }
    sections.push(current)
    return sections.filter(s => s.content.length > 0)
  }

  const sections = extractSections(d.extract)

  if (!d.success) {
    return (
      <SlidePanel visible={visible} direction="bottom" title="WIKIPEDIA" icon={<BookOpen size={11} />} accentColor="#ffe2ab" onClose={onClose} autoDismissMs={0}>
        <div className="agent-error-wrap">
          <div className="agent-error-icon"><Search size={28} /></div>
          <div className="agent-error-title">Topic Not Found</div>
          <div className="agent-error-desc">{d.error || 'Wikipedia could not find this topic. Try a different query.'}</div>
        </div>
      </SlidePanel>
    )
  }

  return (
    <SlidePanel visible={visible} direction="bottom" title="WIKIPEDIA" icon={<BookOpen size={11} />} accentColor="#ffe2ab" onClose={onClose} autoDismissMs={0}>
      <div className="agent-wiki-hero">
        <div className="agent-wiki-icon"><BookOpen size={20} /></div>
        <div style={{ flex: 1 }}>
          <div className="agent-wiki-title">{d.title || 'Untitled'}</div>
          {d.description && <div className="agent-wiki-desc">{d.description}</div>}
          <CategoryTags title={d.title} />
        </div>
        <button className="agent-wiki-bookmark" onClick={() => setBookmarked(!bookmarked)} title="Bookmark">
          <Bookmark size={14} style={{ fill: bookmarked ? '#ffe2ab' : 'none' }} />
        </button>
      </div>

      <ReadingTime text={d.extract} />

      <div className="agent-stats-row">
        <StatusCard label="SECTIONS" value={sections.length} color="#ffe2ab" />
        <StatusCard label="WORDS" value={(d.extract || '').split(/\s+/).filter(Boolean).length.toLocaleString()} />
        {d.url && <StatusCard label="SOURCE" value="Wikipedia" color="#ffe2ab" />}
      </div>

      <div className="agent-divider" />

      {sections.map((s, i) => (
        <SectionBlock key={i} title={s.heading} defaultOpen={i < 2}>
          {s.content.map((p, j) => (
            <p key={j} className="agent-paragraph">{p}</p>
          ))}
        </SectionBlock>
      ))}

      <RelatedTopicsCard title={d.title} />

      {d.url && (
        <div className="agent-wiki-footer">
          <a className="agent-link-btn" href={d.url} target="_blank" rel="noreferrer">
            <ExternalLink size={12} />
            Open full article on Wikipedia
          </a>
        </div>
      )}
    </SlidePanel>
  )
}
