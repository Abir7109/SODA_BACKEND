import { useEffect, useRef, useCallback } from 'react'

const WORLD_MONITOR_URL = 'https://worldmonitor.app'

const SECTIONS = [
  { id: 'map', label: 'MAP' },
  { id: 'wire', label: 'WIRE' },
  { id: 'globe', label: 'GLOBE' },
  { id: 'stocks', label: 'STOCKS' },
  { id: 'chat', label: 'CHAT' },
  { id: 'predictions', label: 'PREDICTIONS' },
  { id: 'cameras', label: 'CAMERAS' },
  { id: 'defcon', label: 'DEFCON' },
  { id: 'outbreaks', label: 'OUTBREAKS' },
  { id: 'streams', label: 'STREAMS' },
]

export default function WorldMonitorPanel({ open, onClose, onNavigate }) {
  const iframeRef = useRef(null)
  const onCloseRef = useRef(onClose)
  const onNavigateRef = useRef(onNavigate)

  useEffect(() => {
    onCloseRef.current = onClose
    onNavigateRef.current = onNavigate
  }, [onClose, onNavigate])

  const handleClose = useCallback(() => {
    if (onCloseRef.current) onCloseRef.current()
  }, [])

  const handleSectionClick = useCallback((sectionId) => {
    if (onNavigateRef.current) onNavigateRef.current(sectionId)
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
        <div className="wm-sections">
          {SECTIONS.map((s) => (
            <button
              key={s.id}
              className="wm-section-btn"
              onClick={() => handleSectionClick(s.id)}
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
        sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
      />
    </div>
  )
}
