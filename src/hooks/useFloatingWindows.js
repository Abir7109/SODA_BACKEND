import { useState, useRef, useCallback } from 'react'

export default function useFloatingWindows() {
  const [floatingWindows, setFloatingWindows] = useState([])
  const nextZRef = useRef(100)
  const floatOffsetRef = useRef(0)

  const findFreeFloatPosition = useCallback((w, h) => {
    const leftZone = { x: 0, y: 0, w: 440, h: 10000 }
    const rightZone = { x: window.innerWidth - 420, y: 0, w: 420, h: 10000 }

    const tries = [
      { x: Math.max(460, window.innerWidth - w - 440), y: 60 },
      { x: 460, y: 60 },
      { x: Math.max(460, window.innerWidth - w - 440), y: window.innerHeight - h - 40 },
      { x: 460, y: window.innerHeight - h - 160 },
      { x: 300, y: 120 },
      { x: 500, y: 200 },
    ]

    const existing = floatingWindows.map(fw => ({ x: fw.x, y: fw.y, w: fw.w, h: fw.h }))

    for (const pos of tries) {
      const overlapsAny = existing.some(e =>
        pos.x < e.x + e.w && pos.x + w > e.x &&
        pos.y < e.y + e.h && pos.y + h > e.y
      )
      const inLeftZone = pos.x < leftZone.x + leftZone.w
      const inRightZone = pos.x + w > rightZone.x
      if (!overlapsAny && !inLeftZone && !inRightZone) {
        return { x: pos.x, y: pos.y }
      }
    }

    const offset = floatOffsetRef.current
    floatOffsetRef.current += 40
    return { x: 460 + offset, y: 100 + offset }
  }, [floatingWindows])

  const getFloatPosition = useCallback((key) => {
    try {
      const saved = localStorage.getItem('float_pos_' + key)
      if (saved) return JSON.parse(saved)
    } catch {}
    return null
  }, [])

  const saveFloatPosition = useCallback((key, x, y) => {
    try {
      localStorage.setItem('float_pos_' + key, JSON.stringify({ x, y }))
    } catch {}
  }, [])

  const positionKeyFromContent = (content) => {
    return content?.positionKey || content?.type || 'window'
  }

  const openFloatingWindow = useCallback((id, title, content, preferredX, preferredY, w, h) => {
    const z = nextZRef.current++
    const pKey = positionKeyFromContent(content)
    const saved = getFloatPosition(pKey)
    let x, y
    if (saved) {
      x = saved.x
      y = saved.y
    } else if (preferredX !== undefined && preferredY !== undefined) {
      const vw = window.innerWidth
      x = Math.max(0, Math.min(preferredX, vw - (w || 320) - 8))
      y = Math.max(0, preferredY)
    } else {
      const pos = findFreeFloatPosition(w || 480, h || 360)
      x = pos.x
      y = pos.y
    }
    setFloatingWindows(prev => {
      const existing = prev.find(fw => fw.id === id)
      if (existing) {
        return prev.map(fw => fw.id === id ? { ...fw, zIndex: z, title, content } : fw)
      }
      return [...prev, { id, title, content, x, y, w, h, zIndex: z, positionKey: pKey }]
    })
  }, [findFreeFloatPosition, getFloatPosition])

  const closeFloatingWindow = useCallback((id) => {
    setFloatingWindows(prev => prev.filter(fw => fw.id !== id))
  }, [])

  const focusFloatingWindow = useCallback((id) => {
    const z = nextZRef.current++
    setFloatingWindows(prev => prev.map(fw => fw.id === id ? { ...fw, zIndex: z } : fw))
  }, [])

  const openUrlInFloatingWindow = useCallback((url, webviewId) => {
    if (!url) return
    const id = webviewId || `web_${Date.now()}`
    const shortUrl = url.replace(/^https?:\/\//, '').slice(0, 50)
    openFloatingWindow(id, shortUrl, { type: 'web', url, id }, 80, 60, 680, 520)
  }, [openFloatingWindow])

  return {
    floatingWindows, setFloatingWindows,
    openFloatingWindow, closeFloatingWindow, focusFloatingWindow,
    openUrlInFloatingWindow, saveFloatPosition,
  }
}
