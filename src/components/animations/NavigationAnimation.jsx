export default function NavigationAnimation({ status, variant = 'route', data = null }) {
  const isError = status === 'error'
  const isDone = status === 'done'
  const isRunning = status === 'pending' || status === 'running'
  const stroke = isError ? 'var(--error)' : '#00d4ff'
  const route = data?.best_route || data?.routes?.[0]
  const traffic = route?.traffic_score || 'clear'
  const dist = route?.distance_km || 0
  const duration = route?.duration_min || 0

  return (
    <svg viewBox="0 0 140 140" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="nav-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.12" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </radialGradient>
        <filter id="nav-glow-filter">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      <rect x="4" y="4" width="132" height="132" fill="url(#nav-glow)" />

      {/* Corner brackets */}
      <g stroke={stroke} strokeWidth="1.2" strokeOpacity="0.2" fill="none"
        style={isRunning ? { animation: 'hud-bracket-in 0.4s ease-out' } : {}}>
        <path d="M 8 14 L 8 8 L 14 8" />
        <path d="M 132 8 L 126 8 L 126 14" />
        <path d="M 8 126 L 8 132 L 14 132" />
        <path d="M 132 126 L 132 132 L 126 132" />
      </g>

      {/* Grid */}
      <g stroke={stroke} strokeWidth="0.3" strokeOpacity="0.04">
        <line x1="20" y1="0" x2="20" y2="140" />
        <line x1="40" y1="0" x2="40" y2="140" />
        <line x1="60" y1="0" x2="60" y2="140" />
        <line x1="80" y1="0" x2="80" y2="140" />
        <line x1="100" y1="0" x2="100" y2="140" />
        <line x1="120" y1="0" x2="120" y2="140" />
        <line x1="0" y1="20" x2="140" y2="20" />
        <line x1="0" y1="40" x2="140" y2="40" />
        <line x1="0" y1="60" x2="140" y2="60" />
        <line x1="0" y1="80" x2="140" y2="80" />
        <line x1="0" y1="100" x2="140" y2="100" />
        <line x1="0" y1="120" x2="140" y2="120" />
      </g>

      {/* Origin pin */}
      <circle cx="25" cy="100" r="5" fill={stroke} fillOpacity="0.3" stroke={stroke} strokeWidth="1.5"
        style={isRunning ? { animation: 'nav-pin-pulse 1.5s ease-in-out infinite' } : {}} />
      <circle cx="25" cy="100" r="2" fill={stroke} />
      <text x="25" y="94" fill={stroke} fontSize="5" textAnchor="middle" opacity="0.5">A</text>

      {/* Destination pin */}
      <g filter="url(#nav-glow-filter)">
        <circle cx="115" cy="40" r="7" fill="none" stroke={stroke} strokeWidth="1.5"
          style={isRunning ? { animation: 'nav-pin-pulse 1.5s ease-in-out infinite 0.5s' } : {}} />
        <polygon points="115,33 119,43 111,43" fill={stroke} fillOpacity="0.6" />
        <circle cx="115" cy="40" r="2.5" fill={stroke} />
      </g>
      <text x="115" y="28" fill={stroke} fontSize="5" textAnchor="middle" opacity="0.5">B</text>

      {/* Route line — drawn with path (curved route A→B) */}
      <path d="M 25 100 Q 40 85 55 80 Q 70 75 85 65 Q 100 55 115 40"
        fill="none" stroke={stroke} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
        strokeDasharray={isRunning ? "4 4" : "0"}
        opacity={isRunning ? 0.8 : 1}
        style={isRunning ? { animation: 'nav-route-dash 1s linear infinite', willChange: 'stroke-dashoffset' } : {}} />

      {/* Route glow underlay */}
      <path d="M 25 100 Q 40 85 55 80 Q 70 75 85 65 Q 100 55 115 40"
        fill="none" stroke={stroke} strokeWidth="6" strokeLinecap="round" strokeLinejoin="round"
        opacity="0.08" />

      {/* Intermediate dots along route */}
      {[1, 2, 3, 4].map((_, i) => {
        const t = (i + 1) / 5
        const x = 25 + t * 90
        const y = 100 - t * 60
        return <circle key={i} cx={x} cy={y} r="1.5" fill={stroke} opacity="0.3" />
      })}

      {/* Traffic indicator ring */}
      {isDone && (
        <g>
          <circle cx="70" cy="70" r="55" fill="none"
            stroke={traffic === 'clear' ? '#00ff88' : traffic === 'light' ? '#88ff00' : traffic === 'moderate' ? '#ffaa00' : '#ff3b3b'}
            strokeWidth="0.5" opacity="0.15" />
          <circle cx="70" cy="70" r="53" fill="none"
            stroke={traffic === 'clear' ? '#00ff88' : traffic === 'light' ? '#88ff00' : traffic === 'moderate' ? '#ffaa00' : '#ff3b3b'}
            strokeWidth="2" opacity="0.05"
            strokeDasharray="2 4" />
        </g>
      )}

      {/* Stats overlay on bottom */}
      {isDone && (
        <g>
          <text x="70" y="122" fill={stroke} fontSize="7" textAnchor="middle" fontWeight="700" opacity="0.7">
            {dist.toFixed(1)} km
          </text>
          <text x="70" y="132" fill={stroke} fontSize="5" textAnchor="middle" opacity="0.4">
            {Math.round(duration)} min
          </text>
        </g>
      )}

      {/* Running pulsing center */}
      {isRunning && (
        <circle cx="70" cy="70" r="12" fill="none" stroke={stroke} strokeWidth="0.5" opacity="0.15"
          style={{ animation: 'nav-ripple 2s ease-out infinite' }} />
      )}
    </svg>
  )
}
