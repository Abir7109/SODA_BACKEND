import { useEffect, useRef, useState, useCallback } from 'react'
import SlidePanel from '../SlidePanel'
import { Music, Disc, User, Headphones } from 'lucide-react'

const TYPE_ICONS = {
  song: <Music size={11} />,
  artist: <User size={11} />,
  album: <Disc size={11} />,
  playlist: <Headphones size={11} />,
}

export default function SpotifySearchPanel({ visible, query, results, onClose }) {
  const scrollRef = useRef(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const autoScrollRef = useRef(true)

  const stopAutoScroll = useCallback(() => {
    setAutoScroll(false)
    autoScrollRef.current = false
  }, [])

  useEffect(() => {
    if (!visible || !results || results.length === 0) return
    autoScrollRef.current = true
    setAutoScroll(true)
    const el = scrollRef.current
    if (!el) return
    let scrollIndex = 0
    const itemEls = () => el.querySelectorAll('.sp-result-card')
    let timer
    const step = () => {
      if (!autoScrollRef.current) return
      const cards = itemEls()
      if (scrollIndex >= cards.length) return
      cards[scrollIndex]?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      scrollIndex++
      timer = setTimeout(step, 600)
    }
    timer = setTimeout(step, 400)
    return () => clearTimeout(timer)
  }, [visible, results])

  return (
    <SlidePanel
      visible={visible}
      direction="right"
      title="SPOTIFY RESULTS"
      icon={<Music size={11} />}
      accentColor="#1DB954"
      onClose={onClose}
      autoDismissMs={0}
    >
      {query && (
        <div className="sp-search-query">
          <span className="sp-label">QUERY</span>
          <span className="sp-value">{query}</span>
        </div>
      )}

      <div ref={scrollRef} onMouseDown={stopAutoScroll} onTouchStart={stopAutoScroll}
        style={{ maxHeight: '60vh', overflowY: 'auto' }}>
        {!results || results.length === 0 ? (
          <div className="sp-empty">Searching...</div>
        ) : (
          <div className="sp-results-list">
            {results.map((r, i) => (
              <div key={i} className="sp-result-card" style={{ cursor: 'default' }}>
                <div className="sp-result-number">{i + 1}</div>
                <div className="sp-result-icon">
                  {TYPE_ICONS[r.type?.toLowerCase()] || <Music size={11} />}
                </div>
                <div className="sp-result-content">
                  <div className="sp-result-title">{r.title || 'Untitled'}</div>
                  {r.type && <div className="sp-result-url" style={{ textTransform: 'capitalize' }}>{r.type}</div>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {results && results.length > 0 && (
        <div className="sp-search-prompt">
          {autoScroll ? 'Auto-scrolling — touch to stop · ' : ''}
          Tell SODA which number to play
        </div>
      )}
    </SlidePanel>
  )
}