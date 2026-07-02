import { useState, useRef, useCallback, useEffect } from 'react'

export default function FloatingWindow({
  id,
  title = 'WINDOW',
  initialX = 200,
  initialY = 100,
  width = 480,
  height = 360,
  children,
  onClose,
  zIndex = 100,
  onFocus,
  onPositionChange,
}) {
  const [pos, setPos] = useState({ x: initialX, y: initialY })
  const dragRef = useRef(null)
  const dragOrigin = useRef(null)
  const winRef = useRef(null)

  const handleDragStart = useCallback((clientX, clientY) => {
    dragOrigin.current = { mx: clientX, my: clientY, ox: pos.x, oy: pos.y }
  }, [pos])

  const handleDragMove = useCallback((clientX, clientY) => {
    if (!dragOrigin.current) return
    const dx = clientX - dragOrigin.current.mx
    const dy = clientY - dragOrigin.current.my
    const vw = window.innerWidth
    const vh = window.innerHeight
    setPos({
      x: Math.max(0, Math.min(dragOrigin.current.ox + dx, vw - width - 8)),
      y: Math.max(0, Math.min(dragOrigin.current.oy + dy, vh - height - 8)),
    })
  }, [width, height])

  const handleDragEnd = useCallback(() => {
    dragOrigin.current = null
    document.removeEventListener('mousemove', handleMouseMove)
    document.removeEventListener('mouseup', handleMouseUp)
    document.removeEventListener('touchmove', handleTouchMove)
    document.removeEventListener('touchend', handleTouchEnd)
    if (onPositionChange) onPositionChange(id, pos.x, pos.y)
  }, [id, pos, onPositionChange])

  const handleMouseDown = useCallback((e) => {
    if (e.button !== 0) return
    handleDragStart(e.clientX, e.clientY)
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    e.preventDefault()
  }, [handleDragStart])

  const handleMouseMove = useCallback((e) => {
    handleDragMove(e.clientX, e.clientY)
  }, [handleDragMove])

  const handleMouseUp = useCallback(() => {
    handleDragEnd()
  }, [handleDragEnd])

  const handleTouchStart = useCallback((e) => {
    const t = e.touches[0]
    handleDragStart(t.clientX, t.clientY)
    document.addEventListener('touchmove', handleTouchMove, { passive: false })
    document.addEventListener('touchend', handleTouchEnd)
  }, [handleDragStart])

  const handleTouchMove = useCallback((e) => {
    e.preventDefault()
    const t = e.touches[0]
    handleDragMove(t.clientX, t.clientY)
  }, [handleDragMove])

  const handleTouchEnd = useCallback(() => {
    handleDragEnd()
  }, [handleDragEnd])

  useEffect(() => {
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.removeEventListener('touchmove', handleTouchMove)
      document.removeEventListener('touchend', handleTouchEnd)
    }
  }, [handleMouseMove, handleMouseUp, handleTouchMove, handleTouchEnd])

  const handleHeaderClick = useCallback(() => {
    if (onFocus) onFocus(id)
  }, [id, onFocus])

  return (
    <div
      ref={winRef}
      className="floating-window"
      style={{
        left: pos.x,
        top: pos.y,
        width,
        height,
        zIndex,
      }}
      onMouseDown={handleHeaderClick}
    >
      <div className="floating-window-glow" />
      <div className="floating-window-border" />
      <div
        className="floating-window-header"
        onMouseDown={handleMouseDown}
        onTouchStart={handleTouchStart}
      >
        <div className="floating-window-dots">
          <span className="floating-window-dot" style={{ background: '#ff5f57' }} />
          <span className="floating-window-dot" style={{ background: '#febc2e' }} />
          <span className="floating-window-dot" style={{ background: '#28c840' }} />
        </div>
        <span className="floating-window-title">{title}</span>
        <button className="floating-window-close" onClick={() => onClose && onClose(id)}>✕</button>
      </div>
      <div className="floating-window-body">
        {children}
      </div>
    </div>
  )
}
