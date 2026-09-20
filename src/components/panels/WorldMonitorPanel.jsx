import { useState, useEffect, useRef, useCallback } from 'react'

const WORLD_MONITOR_URL = 'http://localhost:3000'

const SECTIONS = [
  { id: 'map', label: 'MAP', path: '/' },
  { id: 'wire', label: 'WIRE', path: '/wire' },
  { id: 'globe', label: 'GLOBE', path: '/globe' },
  { id: 'stocks', label: 'STOCKS', path: '/stocks' },
  { id: 'chat', label: 'CHAT', path: '/chat' },
  { id: 'predictions', label: 'PREDICTIONS', path: '/predictions' },
  { id: 'cameras', label: 'CAMERAS', path: '/cameras' },
  { id: 'defcon', label: 'DEFCON', path: '/defcon' },
  { id: 'outbreaks', label: 'OUTBREAKS', path: '/outbreaks' },
  { id: 'streams', label: 'STREAMS', path: '/streams' },
]

export default function WorldMonitorPanel({ open, onClose }) {
  const iframeRef = useRef(null)
  const [currentSection, setCurrentSection] = useState('map')
  const onCloseRef = useRef(onClose)

  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  const handleClose = useCallback(() => {
    if (onCloseRef.current) onCloseRef.current()
  }, [])

  const handleSectionClick = useCallback((section) => {
    if (!iframeRef.current) return
    const iframe = iframeRef.current
    // Try postMessage first (no page reload), fall back to src change
    if (iframe.contentWindow) {
      iframe.contentWindow.postMessage({ type: 'wm-navigate', section: section.id }, '*')
    }
    setCurrentSection(section.id)
  }, [])

  useEffect(() => {
    if (!open) return
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') handleClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [open, handleClose])

  if (!open) return null

  return (
    <div className="world-monitor-panel">
      <div className="wm-control-bar">
        <div className="wm-brand">
          <span className="wm-brand-dot" />
          WORLD MONITOR
        </div>
        <div className="wm-sections">
          {SECTIONS.map((s) => (
            <button
              key={s.id}
              className={`wm-section-btn ${currentSection === s.id ? 'active' : ''}`}
              onClick={() => handleSectionClick(s)}
              title={`Open ${s.label}`}
            >
              {s.label}
            </button>
          ))}
        </div>
        <button className="wm-close-btn" onClick={handleClose} title="Close controller">
          ✕ CLOSE
        </button>
      </div>
      <iframe
        ref={iframeRef}
        id="world-monitor-iframe"
        src={WORLD_MONITOR_URL}
        className="wm-iframe"
        title="World Monitor"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
      />
    </div>
  )
}
