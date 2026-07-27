import { useState } from 'react'
import { Search, Download, Globe, MapPin, Star, X, ExternalLink, Monitor } from 'lucide-react'
import SlidePanel from '../SlidePanel'

export default function LeadFinderPanel({ visible, data, onClose, onBuildWebsite }) {
  const [filterSite, setFilterSite] = useState('all')
  const [sortKey, setSortKey] = useState('name')
  const [searchQuery, setSearchQuery] = useState('')

  if (!data) return null

  if (data.error) {
    return (
      <SlidePanel visible={visible} direction="right" title="LEADS" icon={<Search size={11} />}
        accentColor="#ff3355" onClose={onClose} autoDismissMs={0}>
        <div className="flex items-center justify-center h-full text-[#ff3355] text-xs p-6">{data.error}</div>
      </SlidePanel>
    )
  }

  const { query, location, total, without_website, leads = [] } = data
  let filtered = [...leads]
  if (filterSite === 'no_website') filtered = filtered.filter(l => !l.website)
  if (searchQuery) {
    const q = searchQuery.toLowerCase()
    filtered = filtered.filter(l => (l.name || '').toLowerCase().includes(q) || (l.address || '').toLowerCase().includes(q))
  }
  filtered.sort((a, b) => {
    if (sortKey === 'rating') return (b.rating || 0) - (a.rating || 0)
    if (sortKey === 'name') return (a.name || '').localeCompare(b.name || '')
    return 0
  })

  function downloadCSV() {
    const header = 'name,phone,address,website,email,rating,review_count,types\n'
    const rows = filtered.map(l =>
      `"${l.name || ''}","${l.phone || ''}","${l.address || ''}","${l.website || ''}","",${l.rating || ''},${l.review_count || ''},"${(l.types || []).join('; ')}"`
    ).join('\n')
    const blob = new Blob([header + rows], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = 'leads.csv'; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <SlidePanel visible={visible} direction="right" title="LEADS" icon={<Search size={11} />}
      accentColor="#00f0ff" onClose={onClose} autoDismissMs={0}>
      <div className="p-4 space-y-3 font-mono text-[#e0e0e0] select-none custom-scrollbar" style={{ maxHeight: 'calc(100vh - 60px)', overflowY: 'auto' }}>
        <div className="text-[10px] text-[#666680]">{query} {location && `in ${location}`}</div>
        <div className="flex items-center gap-3 text-[11px]">
          <span className="text-[#b0b0cc]">Total: <span className="text-white font-bold">{total}</span></span>
          <span className="text-[#ffaa00]">No website: <span className="font-bold">{without_website}</span></span>
        </div>
        <div className="flex gap-2">
          <div className="flex bg-[#0a0a0f] border border-[#1e1e2e] text-[10px]">
            {['all', 'no_website'].map(f => (
              <button key={f} onClick={() => setFilterSite(f)}
                className={`px-3 py-1.5 uppercase tracking-wider font-bold transition-all ${filterSite === f ? 'bg-[#00f0ff] text-black' : 'text-[#666680] hover:text-white'}`}>
                {f === 'all' ? `All (${total})` : `No site (${without_website})`}
              </button>
            ))}
          </div>
          <select value={sortKey} onChange={e => setSortKey(e.target.value)}
            className="bg-[#0a0a0f] border border-[#1e1e2e] text-[10px] text-white px-2 py-1.5 uppercase outline-none">
            <option value="name">Name</option>
            <option value="rating">Rating</option>
          </select>
        </div>
        <div className="relative">
          <Search size={10} className="absolute left-2 top-1/2 -translate-y-1/2 text-[#666680]" />
          <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
            placeholder="Filter leads..." className="w-full bg-[#0a0a0f] border border-[#1e1e2e] text-[11px] text-white pl-7 pr-2 py-1.5 outline-none focus:border-[#00f0ff]" />
        </div>
        <div className="max-h-[400px] overflow-y-auto custom-scrollbar space-y-1">
          {filtered.map((l, i) => (
            <div key={l.place_id || i}
              className="bg-[#0a0a0f] border border-[#1e1e2e] p-2 hover:border-[#2a2a3a] transition-all cursor-pointer">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-[11px] text-white font-bold flex items-center gap-1.5">
                    {l.name}
                    {!l.website && <span className="text-[8px] text-[#ffaa00] bg-[#ffaa00]/10 px-1 py-0.5 uppercase tracking-wider font-bold">No Site</span>}
                  </div>
                  <div className="text-[9px] text-[#666680] mt-0.5 flex items-center gap-1">
                    <MapPin size={8} /> {l.address || '—'}
                  </div>
                  {l.phone && <div className="text-[9px] text-[#b0b0cc] mt-0.5">{l.phone}</div>}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {l.rating && (
                    <div className="flex items-center gap-1 text-[10px]">
                      <Star size={8} className="text-[#ffaa00]" />
                      <span className="text-[#ffaa00] font-bold">{l.rating}</span>
                    </div>
                  )}
                  {l.website && (
                    <a href={l.website} target="_blank" rel="noopener noreferrer"
                      className="text-[#00f0ff] hover:text-white transition-colors">
                      <ExternalLink size={10} />
                    </a>
                  )}
                </div>
              </div>
              {l.types && l.types.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1">
                  {l.types.slice(0, 3).map(t => (
                    <span key={t} className="text-[8px] text-[#666680] bg-[#1e1e2e] px-1 py-0.5">{t}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
          {filtered.length === 0 && <div className="text-[#666680] text-[10px] text-center py-4 italic">No leads match</div>}
        </div>
        <div className="flex gap-2 border-t border-[#1e1e2e] pt-3">
          <button onClick={downloadCSV}
            className="flex items-center gap-1 bg-[#1e1e2e] hover:bg-[#2a2a3a] border border-[#1e1e2e] text-[10px] text-white px-3 py-2 uppercase tracking-wider font-bold transition-all">
            <Download size={10} /> CSV
          </button>
          {without_website > 0 && onBuildWebsite && (
            <button onClick={() => onBuildWebsite(filtered.filter(l => !l.website))}
              className="flex items-center gap-1 bg-[#00f0ff]/10 hover:bg-[#00f0ff]/20 border border-[#00f0ff]/30 text-[10px] text-[#00f0ff] px-3 py-2 uppercase tracking-wider font-bold transition-all ml-auto">
              <Monitor size={10} /> Build Websites ({without_website})
            </button>
          )}
          <button onClick={onClose} className="flex items-center gap-1 text-[#666680] hover:text-white text-[10px] px-2 transition-all ml-auto">
            <X size={10} /> Close
          </button>
        </div>
      </div>
    </SlidePanel>
  )
}
