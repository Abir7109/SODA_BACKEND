import { useState, useMemo } from 'react'
import SlidePanel from '../SlidePanel'
import { Brain, User, BookOpen, Users, Database, Search, X } from 'lucide-react'

const TABS = [
  { id: 'profile', label: 'Profile', icon: <User size={14} /> },
  { id: 'facts', label: 'Facts', icon: <Brain size={14} /> },
  { id: 'people', label: 'People', icon: <Users size={14} /> },
  { id: 'lessons', label: 'Lessons', icon: <BookOpen size={14} /> },
  { id: 'custom', label: 'Custom', icon: <Database size={14} /> },
]

function ProfileTab({ profile }) {
  if (!profile || Object.keys(profile).length === 0) {
    return <div className="mem-empty">No profile data</div>
  }
  const fields = Object.entries(profile).filter(([_, v]) => v != null && v !== '')
  return (
    <div className="mem-section-list">
      {fields.map(([k, v]) => (
        <div key={k} className="mem-field-row">
          <span className="mem-field-key">{k.replace(/_/g, ' ')}</span>
          <span className="mem-field-val">{String(v)}</span>
        </div>
      ))}
    </div>
  )
}

function FactsTab({ facts }) {
  if (!facts || facts.length === 0) {
    return <div className="mem-empty">No stored facts</div>
  }
  return (
    <div className="mem-section-list">
      {facts.map((f, i) => (
        <div key={i} className="mem-entry-card">
          <div className="mem-entry-title">{f.key || f.fact || f.title || `Fact #${i + 1}`}</div>
          <div className="mem-entry-desc">{f.value || f.content || f.description || ''}</div>
          <div className="mem-entry-meta">{f.created_at || f.created || f.timestamp || ''}</div>
        </div>
      ))}
    </div>
  )
}

function PeopleTab({ people }) {
  if (!people || people.length === 0) {
    return <div className="mem-empty">No people remembered</div>
  }
  return (
    <div className="mem-section-list">
      {people.map((p, i) => (
        <div key={i} className="mem-entry-card">
          <div className="mem-entry-title">{p.name || `Person #${i + 1}`}</div>
          {p.relationship && <div className="mem-entry-tag">{p.relationship}</div>}
          {p.traits && <div className="mem-entry-desc">{p.traits}</div>}
          {p.preferences && <div className="mem-entry-desc">Prefers: {p.preferences}</div>}
          {p.notes && <div className="mem-entry-desc">{p.notes}</div>}
          <div className="mem-entry-meta">{p.created_at || p.created || ''}</div>
        </div>
      ))}
    </div>
  )
}

function LessonsTab({ lessons }) {
  if (!lessons || lessons.length === 0) {
    return <div className="mem-empty">No lessons recorded</div>
  }
  return (
    <div className="mem-section-list">
      {lessons.map((l, i) => (
        <div key={i} className="mem-entry-card">
          <div className="mem-entry-desc">{l.lesson || l.content || l.message || `Lesson #${i + 1}`}</div>
          {l.context && <div className="mem-entry-meta" style={{ marginTop: 4 }}>Context: {l.context}</div>}
          <div className="mem-entry-meta">{l.created_at || l.created || ''}</div>
        </div>
      ))}
    </div>
  )
}

function CustomTab({ customSchemas }) {
  const schemas = customSchemas?.schemas || []
  const entries = customSchemas?.entries || {}
  if (schemas.length === 0 && Object.keys(entries).length === 0) {
    return <div className="mem-empty">No custom memory schemas</div>
  }
  return (
    <div className="mem-section-list">
      {schemas.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div className="mem-section-label">Schemas ({schemas.length})</div>
          {schemas.map((s, i) => (
            <div key={i} className="mem-entry-card">
              <div className="mem-entry-title">{s.name || s}</div>
              {s.description && <div className="mem-entry-desc">{s.description}</div>}
              {s.fields && <div className="mem-entry-desc">Fields: {s.fields.join(', ')}</div>}
            </div>
          ))}
        </div>
      )}
      {Object.entries(entries).map(([name, items]) => (
        items.length > 0 && (
          <div key={name} style={{ marginBottom: 12 }}>
            <div className="mem-section-label">{name} ({items.length})</div>
            {items.map((item, i) => (
              <div key={i} className="mem-entry-card">
                {Object.entries(item).filter(([k]) => k !== 'id' && k !== 'created_at').map(([k, v]) => (
                  <div key={k} className="mem-field-row">
                    <span className="mem-field-key">{k}</span>
                    <span className="mem-field-val">{String(v)}</span>
                  </div>
                ))}
                <div className="mem-entry-meta">{item.created_at || ''}</div>
              </div>
            ))}
          </div>
        )
      ))}
    </div>
  )
}

export default function MemoryPanel({ visible, data, onClose }) {
  const [activeTab, setActiveTab] = useState('profile')
  const [search, setSearch] = useState('')

  if (!data) return null

  const profile = data.profile || null
  const facts = useMemo(() => {
    const items = data.facts || []
    if (!search) return items
    const q = search.toLowerCase()
    return items.filter(f => (f.key || f.fact || '').toLowerCase().includes(q) || (f.value || '').toLowerCase().includes(q))
  }, [data.facts, search])

  const people = useMemo(() => {
    const items = data.people || []
    if (!search) return items
    const q = search.toLowerCase()
    return items.filter(p => (p.name || '').toLowerCase().includes(q) || (p.relationship || '').toLowerCase().includes(q) || (p.traits || '').toLowerCase().includes(q))
  }, [data.people, search])

  const lessons = useMemo(() => {
    const items = data.lessons || []
    if (!search) return items
    const q = search.toLowerCase()
    return items.filter(l => (l.lesson || l.content || '').toLowerCase().includes(q))
  }, [data.lessons, search])

  const customSchemas = data.custom_schemas || data.custom_memory || null

  const counts = {
    profile: profile ? Object.keys(profile).filter(k => profile[k] != null && profile[k] !== '').length : 0,
    facts: data.facts?.length || 0,
    people: data.people?.length || 0,
    lessons: data.lessons?.length || 0,
    custom: (customSchemas?.schemas?.length || 0) + Object.keys(customSchemas?.entries || {}).length,
  }

  return (
    <SlidePanel visible={visible} direction="bottom" title="MEMORY DATABASE"
      icon={<Brain size={11} />} accentColor="#fff176" onClose={onClose} autoDismissMs={0}>
      {/* Search bar */}
      <div className="mem-search-wrap">
        <Search size={13} className="mem-search-icon" />
        <input className="mem-search-input" type="text" placeholder="Search memory..." value={search}
          onChange={e => setSearch(e.target.value)} />
        {search && <button className="mem-search-clear" onClick={() => setSearch('')}><X size={13} /></button>}
      </div>

      {/* Tab bar */}
      <div className="mem-tab-bar">
        {TABS.map(tab => (
          <button key={tab.id} className={`mem-tab ${activeTab === tab.id ? 'mem-tab-active' : ''}`}
            onClick={() => { setActiveTab(tab.id); setSearch('') }}>
            {tab.icon}
            <span className="mem-tab-label">{tab.label}</span>
            {counts[tab.id] > 0 && <span className="mem-tab-count">{counts[tab.id]}</span>}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="mem-content">
        {activeTab === 'profile' && <ProfileTab profile={profile} />}
        {activeTab === 'facts' && <FactsTab facts={facts} />}
        {activeTab === 'people' && <PeopleTab people={people} />}
        {activeTab === 'lessons' && <LessonsTab lessons={lessons} />}
        {activeTab === 'custom' && <CustomTab customSchemas={customSchemas} />}
      </div>
    </SlidePanel>
  )
}
