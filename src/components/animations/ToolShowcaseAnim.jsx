import { useState, useEffect, useRef } from 'react'

export default function ToolShowcaseAnim({ status, data = null }) {
  const isDone = status === 'done'
  const tools = data?.tools || []
  const total = tools.length

  const [idx, setIdx] = useState(-1)
  const intervalRef = useRef(null)

  const skipToDone = () => {
    setIdx(total - 1)
    if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null }
  }

  useEffect(() => {
    if (!total) return
    if (isDone) { skipToDone(); return }
    setIdx(0)
    intervalRef.current = setInterval(() => {
      setIdx(prev => {
        if (prev >= total - 1) { clearInterval(intervalRef.current); return prev }
        return prev + 1
      })
    }, 120)
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [total, isDone])

  const current = idx >= 0 ? tools[idx] : null
  const currentName = current ? (typeof current === 'string' ? current : current?.name || '') : ''
  const currentDesc = current && typeof current === 'object' ? (current.description || '') : ''
  const allDone = idx >= total - 1 && total > 0

  return (
    <div style={{
      width: '100%', height: '100%', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: 8, overflow: 'hidden',
    }}>
      <div style={{ display: 'flex', gap: 4 }}>
        {[0,1,2,3].map(i => (
          <div key={i} style={{
            width: 4, height: 4, borderRadius: '50%',
            background: '#00fbfb',
            opacity: idx < 0 ? 0.12 : allDone ? 0.3 : 0.5,
            transform: allDone ? 'scale(1)' : `scale(${0.3 + Math.sin((idx * 0.5 + i) * 1.5) * 0.7})`,
            transition: 'transform 0.3s ease, opacity 0.3s ease',
          }} />
        ))}
      </div>

      <div style={{
        minHeight: 36, display: 'flex', alignItems: 'center', justifyContent: 'center',
        transition: 'opacity 0.2s ease',
      }}>
        {idx < 0 ? (
          <span style={{ color: '#00fbfb', fontSize: 10, opacity: 0.5, fontFamily: 'monospace' }}>
            LOADING TOOLS...
          </span>
        ) : allDone ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#00fbfb" strokeWidth="2.5"
              strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            <span style={{ color: '#00fbfb', fontSize: 11, fontWeight: 700, fontFamily: 'monospace', letterSpacing: 2 }}>
              {total} TOOLS
            </span>
            <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: 8, fontFamily: 'monospace' }}>
              ready at your command
            </span>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
            <span style={{
              color: '#00fbfb', fontSize: 11, fontWeight: 700, fontFamily: 'monospace',
              textTransform: 'uppercase', letterSpacing: 1, textAlign: 'center',
              animation: 'hud-fade-in 0.25s ease-out',
            }}>
              {currentName.replace(/_/g, ' ')}
            </span>
            {currentDesc && (
              <span style={{
                color: 'rgba(255,255,255,0.4)', fontSize: 7, fontFamily: 'monospace',
                textAlign: 'center', maxWidth: 200, animation: 'hud-fade-in 0.25s ease-out',
              }}>
                {currentDesc.length > 50 ? currentDesc.slice(0, 49) + '…' : currentDesc}
              </span>
            )}
          </div>
        )}
      </div>

      {idx >= 0 && !allDone && (
        <div style={{
          width: '60%', height: 1, background: 'linear-gradient(90deg, transparent, rgba(0,251,251,0.3), transparent)',
          marginTop: 4,
        }} />
      )}

      {idx >= 0 && !allDone && (
        <div style={{
          display: 'flex', gap: 2, flexWrap: 'wrap', justifyContent: 'center',
          maxWidth: 240, maxHeight: 36, overflow: 'hidden',
        }}>
          {tools.slice(0, idx + 1).map((t, i) => (
            <span key={i} style={{
              fontSize: 6, color: 'rgba(0,251,251,0.3)', fontFamily: 'monospace',
              whiteSpace: 'nowrap', transition: 'color 0.2s ease',
            }}>
              {((typeof t === 'string' ? t : t?.name) || '').replace(/_/g, ' ')}
              {i < idx ? ',' : ''}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
