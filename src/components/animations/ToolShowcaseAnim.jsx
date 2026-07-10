import { useState, useEffect, useRef } from 'react'

export default function ToolShowcaseAnim({ status, data = null }) {
  const isError = status === 'error'
  const isDone = status === 'done'
  const stroke = isError ? 'var(--error)' : '#00fbfb'
  const tools = data?.tools || []
  const total = tools.length

  const [displayed, setDisplayed] = useState([])
  const [phase, setPhase] = useState('idle')
  const [entering, setEntering] = useState(null)
  const intervalRef = useRef(null)
  const enteringTimerRef = useRef(null)

  const skipToDone = () => {
    setDisplayed(tools)
    setPhase('done')
    if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null }
    if (enteringTimerRef.current) { clearTimeout(enteringTimerRef.current); enteringTimerRef.current = null }
  }

  useEffect(() => {
    if (!total) return
    if (isDone) { skipToDone(); return }
    setPhase('cycle')
    setDisplayed([tools[0]])
    setEntering(0)
    enteringTimerRef.current = setTimeout(() => setEntering(null), 80)
    return () => {
      if (enteringTimerRef.current) clearTimeout(enteringTimerRef.current)
    }
  }, [total, isDone])

  useEffect(() => {
    if (phase !== 'cycle' || total <= 1) return
    intervalRef.current = setInterval(() => {
      setDisplayed(prev => {
        if (prev.length >= total) {
          setPhase('done')
          return prev
        }
        return [...prev, tools[prev.length]]
      })
      setEntering(prev => prev !== null ? prev + 1 : null)
      if (enteringTimerRef.current) clearTimeout(enteringTimerRef.current)
      enteringTimerRef.current = setTimeout(() => setEntering(null), 80)
    }, 120)
    return () => {
      if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null }
    }
  }, [phase, total])

  useEffect(() => {
    if (phase === 'cycle' && total === 1) {
      const t = setTimeout(() => setPhase('done'), 600)
      return () => clearTimeout(t)
    }
  }, [phase, total])

  useEffect(() => {
    if (isDone && phase !== 'done') skipToDone()
    return () => {
      if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null }
      if (enteringTimerRef.current) { clearTimeout(enteringTimerRef.current); enteringTimerRef.current = null }
    }
  }, [isDone])

  return (
    <svg viewBox="0 0 140 140" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="tsc-glow" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0" />
          <stop offset="50%" stopColor={stroke} stopOpacity="0.14" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
        <filter id="tsc-blur">
          <feGaussianBlur stdDeviation="1.5" />
        </filter>
        <filter id="tsc-glow-filter">
          <feGaussianBlur stdDeviation="1.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* HUD Corner brackets */}
      <g stroke={stroke} strokeWidth="1.2" strokeOpacity={phase === 'idle' ? '0.08' : '0.25'} fill="none"
        style={{ animation: 'hud-bracket-in 0.4s ease-out' }}>
        <path d="M 8 14 L 8 8 L 14 8" />
        <path d="M 132 8 L 126 8 L 126 14" />
        <path d="M 8 126 L 8 132 L 14 132" />
        <path d="M 132 126 L 132 132 L 126 132" />
      </g>

      {/* Subtle background crosshair grid */}
      <line x1="70" y1="4" x2="70" y2="136" stroke={stroke} strokeWidth="0.3" strokeOpacity="0.04" />
      <line x1="4" y1="70" x2="136" y2="70" stroke={stroke} strokeWidth="0.3" strokeOpacity="0.04" />
      <circle cx="70" cy="70" r="50" fill="none" stroke={stroke} strokeWidth="0.3" strokeOpacity="0.03" />
      <circle cx="70" cy="70" r="30" fill="none" stroke={stroke} strokeWidth="0.3" strokeOpacity="0.03" />

      {phase === 'idle' && (
        <text x={70} y={74} textAnchor="middle" fill={stroke} fillOpacity="0.5"
          fontSize={7} fontFamily="monospace" letterSpacing="1.5">
          LOADING TOOLS...
        </text>
      )}

      {displayed.map((tool, idx) => {
        const toolName = (typeof tool === 'string' ? tool : tool?.name) || ''
        const toolDesc = (typeof tool === 'object' && tool ? tool.description : '') || ''
        const isCurrent = idx === displayed.length - 1 && phase === 'cycle'
        const isEntering = entering === idx
        const stackIdx = displayed.length - 2 - idx
        const yOffset = isCurrent
          ? (isEntering ? 28 : 0)
          : -(4 + stackIdx * 16)
        const opacity = phase === 'idle' ? 0 : isCurrent
          ? (isEntering ? 0 : 1)
          : Math.max(0.1, 0.35 - stackIdx * 0.07)
        const scale = isCurrent ? 1 : 0.78

        return (
          <g key={toolName || idx}
            style={{
              transform: `translateY(${yOffset}px) scale(${scale})`,
              transformOrigin: '70px 66px',
              opacity,
              transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s ease',
              willChange: 'transform, opacity',
            }}
          >
            {isCurrent ? (
              <>
                <rect x={4} y={42} width={132} height={52} rx={2}
                  fill="url(#tsc-glow)" stroke={stroke} strokeWidth={1.2} strokeOpacity={0.6}
                  filter={isEntering ? 'url(#tsc-glow-filter)' : undefined}
                />
                <g style={{ animation: 'hud-scan-svg 2s ease-in-out infinite' }}>
                  <line x1="6" y1={94} x2="134" y2={94} stroke={stroke} strokeWidth="0.3" strokeOpacity="0.08" />
                </g>
                <text x={70} y={64} textAnchor="middle" fill={stroke} fillOpacity={0.95}
                  fontSize={8.5} fontFamily="monospace" fontWeight="700">
                  {toolName.replace(/_/g, ' ')}
                </text>
                {toolDesc && (
                  <text x={70} y={80} textAnchor="middle" fill={stroke} fillOpacity={0.55}
                    fontSize={5} fontFamily="monospace">
                    {toolDesc.length > 40 ? toolDesc.slice(0, 39) + '…' : toolDesc}
                  </text>
                )}
              </>
            ) : (
              <>
                <rect x={16} y={44} width={108} height={16} rx={2}
                  fill={stroke} fillOpacity={0.05} stroke={stroke} strokeWidth={0.3} strokeOpacity={0.15}
                />
                <text x={70} y={56} textAnchor="middle" fill={stroke} fillOpacity={0.25}
                  fontSize={5} fontFamily="monospace">
                  {toolName.replace(/_/g, ' ')}
                </text>
              </>
            )}
          </g>
        )
      })}

      {phase === 'done' && (
        <g
          style={{
            opacity: 0,
            animation: 'hud-card-in 0.4s cubic-bezier(0.16, 1, 0.3, 1) 0.1s forwards',
          }}
        >
          {/* Rotating bracket rings on done */}
          <g style={{ transformOrigin: '70px 70px', animation: 'hud-rotate-reverse 8s linear infinite' }}>
            <rect x="22" y="22" width="96" height="96" rx="2" fill="none" stroke={stroke} strokeWidth="0.5"
              strokeOpacity="0.12" strokeDasharray="4 8" />
          </g>
          <g style={{ transformOrigin: '70px 70px', animation: 'hud-rotate 12s linear infinite' }}>
            <rect x="26" y="26" width="88" height="88" rx="2" fill="none" stroke={stroke} strokeWidth="0.3"
              strokeOpacity="0.06" strokeDasharray="2 12" />
          </g>

          {/* Glow behind checkmark */}
          <circle cx="70" cy={44} r={20} fill={stroke} fillOpacity="0.04" filter="url(#tsc-blur)" />
          <circle cx="70" cy={44} r={14} fill="none" stroke={stroke} strokeWidth={1.5} strokeOpacity={0.5}
            style={{
              transformOrigin: '70px 44px',
              animation: 'hud-pulse 2s ease-in-out infinite',
            }}
          />
          <polyline points="62,44 68,50 78,38" fill="none" stroke={stroke} strokeWidth={2.5}
            strokeLinecap="round" strokeLinejoin="round"
            filter="url(#tsc-glow-filter)"
          />
          {/* Decorative lines */}
          <line x1="35" y1="70" x2="50" y2="70" stroke={stroke} strokeWidth="0.5" strokeOpacity="0.2" />
          <line x1="90" y1="70" x2="105" y2="70" stroke={stroke} strokeWidth="0.5" strokeOpacity="0.2" />
          <text x={70} y={82} textAnchor="middle" fill={stroke} fillOpacity={0.95}
            fontSize={11} fontFamily="monospace" fontWeight="700" letterSpacing="3">
            {total} TOOLS
          </text>
          <text x={70} y={97} textAnchor="middle" fill={stroke} fillOpacity={0.4}
            fontSize={4.5} fontFamily="monospace" letterSpacing="1.5">
            ready at your command
          </text>
        </g>
      )}
    </svg>
  )
}
