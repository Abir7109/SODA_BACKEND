import { useEffect, useRef } from 'react'

export default function WakeSequence({ active, onComplete }) {
  const timerRef = useRef(null)

  useEffect(() => {
    if (!active) return
    timerRef.current = setTimeout(() => {
      onComplete?.()
    }, 1500)
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [active, onComplete])

  if (!active) return null

  return (
    <div className="fixed inset-0 z-[9999] pointer-events-none flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.35)', animation: 'ws-fade-in 0.15s ease-out' }}>
      {/* Scan line */}
      <div className="absolute inset-0"
        style={{
          height: '3px', background: 'linear-gradient(to bottom, transparent, rgba(0,251,251,0.6), transparent)',
          boxShadow: '0 0 15px rgba(0,251,251,0.4)',
          animation: 'ws-scan 0.6s ease-out forwards',
          top: 0, left: 0, right: 0,
        }} />

      {/* Splash rings */}
      <svg className="absolute w-96 h-96" viewBox="0 0 200 200">
        <circle cx="100" cy="100" fill="none" stroke="#00fbfb"
          style={{ animation: 'ws-splash-ring 0.8s ease-out 0.15s forwards' }} />
        <circle cx="100" cy="100" fill="none" stroke="#0064ff"
          style={{ animation: 'ws-splash-ring 0.8s ease-out 0.35s forwards' }} />
      </svg>

      {/* Cyberpunk glitch text */}
      <div className="absolute flex flex-col items-center gap-2"
        style={{ animation: 'ws-fade-in 0.2s ease-out 0.5s both' }}>
        <div className="text-2xl font-bold tracking-[0.3em] uppercase"
          style={{
            color: '#00fbfb', fontFamily: 'JetBrains Mono, monospace',
            animation: 'ws-glitch-flicker 1.2s ease-out 0.5s both, ws-glitch-slice 0.8s steps(10) 0.5s both',
            textShadow: '0 0 8px #0ff, 0 0 20px #0ff, 0 0 40px #06f',
          }}>
          SODA ONLINE
        </div>
        <div className="text-[10px] tracking-[0.2em] uppercase"
          style={{ color: 'rgba(0,251,251,0.5)', fontFamily: 'JetBrains Mono, monospace' }}>
          System rebooting
        </div>
      </div>

      {/* HUD brackets */}
      <div className="absolute top-6 left-6 w-12 h-12"
        style={{ borderTop: '1.5px solid rgba(0,251,251,0.5)', borderLeft: '1.5px solid rgba(0,251,251,0.5)', animation: 'ws-bracket-in 0.4s ease-out 0.7s both' }} />
      <div className="absolute top-6 right-6 w-12 h-12"
        style={{ borderTop: '1.5px solid rgba(0,251,251,0.5)', borderRight: '1.5px solid rgba(0,251,251,0.5)', animation: 'ws-bracket-in 0.4s ease-out 0.7s both' }} />
      <div className="absolute bottom-6 left-6 w-12 h-12"
        style={{ borderBottom: '1.5px solid rgba(0,251,251,0.5)', borderLeft: '1.5px solid rgba(0,251,251,0.5)', animation: 'ws-bracket-in 0.4s ease-out 0.7s both' }} />
      <div className="absolute bottom-6 right-6 w-12 h-12"
        style={{ borderBottom: '1.5px solid rgba(0,251,251,0.5)', borderRight: '1.5px solid rgba(0,251,251,0.5)', animation: 'ws-bracket-in 0.4s ease-out 0.7s both' }} />
    </div>
  )
}
