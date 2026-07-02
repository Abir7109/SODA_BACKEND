import { useState, useRef, useEffect, useCallback } from 'react'

export default function BackgroundWidget({ speakingState, onRestore, widgetMode }) {
  const [displayState, setDisplayState] = useState('idle')
  const [rightPos, setRightPos] = useState(() => window.innerWidth - 150)
  const dragRef = useRef(null)
  const rafRef = useRef(null)

  useEffect(() => {
    const onResize = () => setRightPos(window.innerWidth - 150)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  useEffect(() => {
    if (speakingState === 'wake') {
      setDisplayState('wake')
      const t = setTimeout(() => setDisplayState('idle'), 300)
      return () => clearTimeout(t)
    }
    setDisplayState(speakingState || 'idle')
  }, [speakingState])

  const handleMouseDown = useCallback((e) => {
    if (widgetMode && window.electron?.widgetDrag) {
      e.preventDefault()
      dragRef.current = { mx: e.screenX, my: e.screenY }
      const handleMove = (ev) => {
        if (!dragRef.current) return
        const dpr = window.devicePixelRatio || 1
        const dx = (ev.screenX - dragRef.current.mx) / dpr
        const dy = (ev.screenY - dragRef.current.my) / dpr
        if (Math.abs(dx) > 0 || Math.abs(dy) > 0) {
          window.electron.widgetDrag(Math.round(dx), Math.round(dy))
          dragRef.current = { mx: ev.screenX, my: ev.screenY }
        }
      }
      const handleUp = () => {
        dragRef.current = null
        document.removeEventListener('mousemove', handleMove)
        document.removeEventListener('mouseup', handleUp)
        if (rafRef.current) cancelAnimationFrame(rafRef.current)
      }
      document.addEventListener('mousemove', handleMove)
      document.addEventListener('mouseup', handleUp)
    }
  }, [widgetMode])

  const handleClick = useCallback(() => {
    if (!dragRef.current && onRestore) onRestore()
  }, [onRestore])

  const bars = [0, 1, 2].map((i) => {
    const isUser = displayState === 'user'
    const isModel = displayState === 'model'
    const idle = displayState === 'idle'
    const base = idle ? 10 : 8
    const range = isUser ? 12 : isModel ? 8 : 2
    return { height: `${base + range}px`, delay: `${i * 0.15}s` }
  })

  const wakeFlash = displayState === 'wake'

  return (
    <div
      className={`bgw-pill${wakeFlash ? ' bgw-wake' : ''}${widgetMode ? ' bgw-widget-mode' : ''}`}
      style={widgetMode ? {} : { left: rightPos, top: 8 }}
      onMouseDown={handleMouseDown}
      onClick={handleClick}
    >
      <div className="bgw-brand">SODA</div>
      <div className="bgw-bars">
        {bars.map((b, i) => (
          <div
            key={i}
            className={`bgw-bar bgw-bar-${displayState}`}
            style={{ height: b.height, animationDelay: b.delay }}
          />
        ))}
      </div>
    </div>
  )
}
