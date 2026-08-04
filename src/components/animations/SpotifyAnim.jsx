export default function SpotifyAnim({ status, data = null }) {
  const isError = status === 'error'
  const isDone = status === 'done'
  const isRunning = status === 'pending' || status === 'running'
  const isIdle = !isRunning && !isDone && !isError
  const accent = '#1DB954' // Spotify green
  const stroke = isError ? 'var(--error)' : accent
  const toolName = data?.tool || ''
  const result = data?.result || data?.message || ''

  return (
    <svg viewBox="0 0 140 140" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="sp-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.15" />
          <stop offset="60%" stopColor={stroke} stopOpacity="0.04" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </radialGradient>
        <linearGradient id="sp-ring-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.2" />
          <stop offset="50%" stopColor={stroke} stopOpacity="0.8" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0.2" />
        </linearGradient>
        <filter id="sp-glow-filter">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="sp-shadow">
          <feDropShadow dx="0" dy="0" stdDeviation="2" floodColor={stroke} floodOpacity="0.4" />
        </filter>
      </defs>

      {/* Background glow */}
      <circle cx="70" cy="70" r="60" fill="url(#sp-glow)" />

      {/* Sound wave rings (pulsing outward when playing) */}
      {isRunning && (
        <g opacity="0.3">
          <circle cx="70" cy="70" r="25" fill="none" stroke={stroke} strokeWidth="0.5"
            style={{ animation: 'sp-pulse-ring 2s ease-out infinite', transformOrigin: '70px 70px' }} />
          <circle cx="70" cy="70" r="35" fill="none" stroke={stroke} strokeWidth="0.4"
            style={{ animation: 'sp-pulse-ring 2s ease-out 0.4s infinite', transformOrigin: '70px 70px' }} />
          <circle cx="70" cy="70" r="45" fill="none" stroke={stroke} strokeWidth="0.3"
            style={{ animation: 'sp-pulse-ring 2s ease-out 0.8s infinite', transformOrigin: '70px 70px' }} />
        </g>
      )}

      {/* Outer ring */}
      <circle cx="70" cy="70" r="42" fill="none" stroke={stroke} strokeWidth="0.5" strokeOpacity="0.15" />

      {/* Rotating segmented ring */}
      <g style={isRunning
        ? { transformOrigin: '70px 70px', animation: 'hud-rotate 3s linear infinite', willChange: 'transform' }
        : isIdle ? { transformOrigin: '70px 70px', animation: 'hud-rotate 12s linear infinite', willChange: 'transform' } : {}
      }>
        <circle cx="70" cy="70" r="42" fill="none" stroke="url(#sp-ring-grad)" strokeWidth="2"
          strokeDasharray="44 220" opacity="0.7" filter="url(#sp-glow-filter)" />
        <circle cx="70" cy="70" r="42" fill="none" stroke={stroke} strokeWidth="1"
          strokeDasharray="8 256" strokeDashoffset="60" opacity="0.3" />
      </g>

      {/* Sound bars (equalizer) */}
      <g transform="translate(70,70)">
        {[0, 1, 2, 3, 4].map(i => {
          const x = (i - 2) * 8
          const baseH = [6, 10, 12, 10, 6][i]
          const animDur = [0.8, 0.6, 0.9, 0.7, 0.85][i]
          return (
            <rect key={i} x={x - 2} y={-baseH / 2} width="4" height={baseH}
              rx="1" fill={stroke} opacity={isRunning ? 0.9 : 0.3}
              filter={isRunning ? 'url(#sp-glow-filter)' : undefined}
              style={isRunning ? {
                transformOrigin: `${x}px 0px`,
                animation: `sp-bar-bounce ${animDur}s ease-in-out infinite alternate`,
              } : {}} />
          )
        })}
      </g>

      {/* Center play triangle (when idle/done) */}
      {(!isRunning || isDone) && (
        <g transform="translate(70,70)" opacity={isDone ? 1 : 0.4}>
          <polygon points="-5,-7 -5,7 7,0" fill={stroke}
            filter="url(#sp-shadow)"
            style={isDone ? { animation: 'sp-play-pop 0.4s cubic-bezier(0.16, 1, 0.3, 1)' } : {}} />
        </g>
      )}

      {/* Pause bars (when running) */}
      {isRunning && (
        <g transform="translate(70,70)" opacity="0.8">
          <rect x="-5" y="-6" width="3" height="12" rx="1" fill={stroke}
            style={{ animation: 'sp-fade-in 0.3s ease-out' }} />
          <rect x="2" y="-6" width="3" height="12" rx="1" fill={stroke}
            style={{ animation: 'sp-fade-in 0.3s ease-out 0.1s both' }} />
        </g>
      )}

      {/* Orbiting music note */}
      <g style={isRunning
        ? { transformOrigin: '70px 70px', animation: 'hud-rotate 4s linear infinite', willChange: 'transform' }
        : { opacity: 0.4 }
      }>
        <circle cx="70" cy="28" r="3" fill={stroke} opacity="0.7" filter="url(#sp-glow-filter)" />
        <circle cx="70" cy="28" r="6" fill={stroke} opacity="0.06" />
      </g>

      {/* Done checkmark */}
      {isDone && !isError && (
        <g>
          <circle cx="70" cy="70" r="20" fill={stroke} fillOpacity="0.04" filter="url(#sp-glow-filter)"
            style={{ animation: 'hud-ring-burst 0.6s ease-out forwards' }} />
          <polyline points="62,68 68,74 78,62" fill="none" stroke={stroke} strokeWidth="2"
            strokeLinecap="round" strokeLinejoin="round"
            style={{ animation: 'hud-check-in 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards' }} />
        </g>
      )}

      {/* Error X */}
      {isError && (
        <g>
          <line x1="63" y1="63" x2="77" y2="77" stroke={stroke} strokeWidth="2"
            strokeLinecap="round" style={{ animation: 'hud-check-in 0.3s ease-out' }} />
          <line x1="77" y1="63" x2="63" y2="77" stroke={stroke} strokeWidth="2"
            strokeLinecap="round" style={{ animation: 'hud-check-in 0.3s ease-out 0.1s both' }} />
        </g>
      )}

      {/* Tool name label */}
      {isDone && toolName && (
        <text x="70" y="105" textAnchor="middle" fill={stroke} fillOpacity="0.5" fontSize="4" fontFamily="monospace"
          style={{ animation: 'hud-card-in 0.3s ease-out' }}>
          {toolName}
        </text>
      )}
      {isDone && result && (
        <text x="70" y="115" textAnchor="middle" fill={stroke} fillOpacity="0.35" fontSize="3" fontFamily="monospace"
          style={{ animation: 'hud-card-in 0.3s ease-out 0.1s both' }}>
          {typeof result === 'string' ? result.slice(0, 18) : 'done'}
        </text>
      )}

      {/* Idle breathing */}
      {isIdle && (
        <circle cx="70" cy="70" r="42" fill="none" stroke={stroke} strokeWidth="0.8" strokeOpacity="0.08"
          style={{ animation: 'hud-idle-breathe 4s ease-in-out infinite' }} />
      )}
    </svg>
  )
}
