export default function BackgroundCommandAnim({ status, variant = 'exec', data = null }) {
  const isError = status === 'error'
  const isDone = status === 'done'
  const isRunning = status === 'pending' || status === 'running'
  const stroke = isError ? 'var(--error)' : '#00fbfb'

  const cmd = data?.command || ''
  const output = data?.output || ''
  const outLines = output.split('\n').filter(Boolean)
  const attempt = data?.attempt || 0
  const totalAttempts = data?.total_attempts || 1
  const cmdPhase = data?.phase || 'running'

  return (
    <svg viewBox="0 0 140 140" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="bg-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.12" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </radialGradient>
        <filter id="bg-glow-filter">
          <feGaussianBlur stdDeviation="1" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <pattern id="bg-grid" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
          <line x1="20" y1="0" x2="20" y2="20" stroke={stroke} strokeWidth="0.3" strokeOpacity="0.04" />
          <line x1="0" y1="20" x2="20" y2="20" stroke={stroke} strokeWidth="0.3" strokeOpacity="0.04" />
        </pattern>
      </defs>

      <rect x="4" y="4" width="132" height="132" fill="url(#bg-grid)"
        style={isRunning ? { animation: 'hud-grid-pulse 4s ease-in-out infinite' } : {}} />

      <circle cx="70" cy="70" r="60" fill="url(#bg-glow)" />

      <g stroke={stroke} strokeWidth="1.2" strokeOpacity="0.25" fill="none"
        style={{ animation: 'hud-bracket-in 0.4s ease-out' }}>
        <path d="M 8 14 L 8 8 L 14 8" />
        <path d="M 132 8 L 126 8 L 126 14" />
        <path d="M 8 126 L 8 132 L 14 132" />
        <path d="M 132 126 L 132 132 L 126 132" />
      </g>

      <rect x="20" y="25" width="100" height="85" rx="2" fill={stroke} fillOpacity="0.04" stroke={stroke} strokeWidth="1" strokeOpacity="0.4" />

      {/* ── THINKING phase ── */}
      {isRunning && cmdPhase === 'thinking' && (
        <g>
          {/* Scanline */}
          <rect x="20" y="25" width="3" height="85" fill={stroke} fillOpacity="0.08">
            <animate attributeName="x" values="20;117;20" dur="3s" repeatCount="indefinite" />
          </rect>
          <text x="40" y="62" fill={stroke} fillOpacity="0.7" fontSize="5" fontFamily="monospace" fontWeight="700"
            style={{ animation: 'hud-signal 1.2s step-end infinite' }}>
            ANALYZING
          </text>
          <text x="34" y="76" fill={stroke} fillOpacity="0.35" fontSize="3.5" fontFamily="monospace">
            DEVISING STRATEGY
          </text>
          <circle cx="70" cy="95" r="4" fill="none" stroke={stroke} strokeWidth="0.8" strokeOpacity="0.3">
            <animate attributeName="r" values="3;5;3" dur="1.5s" repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.3;0.8;0.3" dur="1.5s" repeatCount="indefinite" />
          </circle>
        </g>
      )}

      {/* ── RETRYING phase ── */}
      {isRunning && cmdPhase === 'retrying' && (
        <g>
          <rect x="22" y="26" width="96" height="12" fill={stroke} fillOpacity="0.06" />
          <text x="26" y="35" fill={stroke} fillOpacity="0.5" fontSize="3.5" fontFamily="monospace" fontWeight="600">
            ATTEMPT {attempt}/{totalAttempts}
          </text>

          {/* Attempt counter rings */}
          {[1, 2, 3, 4, 5].map((i) => (
            <circle key={i} cx={30 + i * 17} cy="52" r="5" fill="none"
              stroke={i < attempt ? '#00ff88' : i === attempt ? stroke : stroke}
              strokeWidth={i === attempt ? '1.5' : '0.8'}
              strokeOpacity={i < attempt ? '0.5' : i === attempt ? '0.9' : '0.15'}>
              {i === attempt && (
                <animate attributeName="strokeOpacity" values="0.9;0.4;0.9" dur="1s" repeatCount="indefinite" />
              )}
            </circle>
          ))}

          {/* Current command */}
          <text x="26" y="72" fill={stroke} fillOpacity="0.8" fontSize="3.8" fontFamily="monospace" fontWeight="500">
            {'>'} {cmd.slice(0, 28)}
          </text>

          {/* Loading dots */}
          <text x="26" y="84" fill={stroke} fillOpacity="0.35" fontSize="3" fontFamily="monospace">
            executing
            <animate attributeName="fillOpacity" values="0.35;0.8;0.35" dur="1.5s" repeatCount="indefinite" />
          </text>
        </g>
      )}

      {/* ── RUNNING phase (no retry data) ── */}
      {isRunning && (cmdPhase === 'running' || (!cmdPhase || cmdPhase === 'pending')) && (
        <g>
          <text x="26" y="44" fill={stroke} fillOpacity="0.6" fontSize="4" fontFamily="monospace" fontWeight="600">{'>'}_</text>
          <rect x="30" y="48" width="70" height="3" rx="1" fill={stroke} fillOpacity="0.06">
            <animate attributeName="width" values="70;80;70" dur="1s" repeatCount="indefinite" />
          </rect>
          <rect x="26" y="56" width="60" height="2.5" rx="1" fill={stroke} fillOpacity="0.08" />
          <rect x="26" y="62" width="45" height="2.5" rx="1" fill={stroke} fillOpacity="0.06" />
          <rect x="26" y="68" width="55" height="2.5" rx="1" fill={stroke} fillOpacity="0.08" />
          <rect x="26" y="75" width="8" height="2.5" rx="1" fill={stroke} fillOpacity="0.8"
            style={{ animation: 'hud-signal 0.8s step-end infinite' }} />
        </g>
      )}

      {/* ── DONE phase ── */}
      {isDone && (cmd || outLines.length > 0) && (
        <g>
          {/* Attempt summary badge */}
          {data?.total_attempts > 1 && (
            <g>
              <rect x="88" y="26" width="30" height="10" rx="1" fill={stroke} fillOpacity="0.08" stroke={stroke} strokeWidth="0.5" strokeOpacity="0.3" />
              <text x="90" y="33" fill={stroke} fillOpacity="0.5" fontSize="3" fontFamily="monospace" fontWeight="600">
                {data.total_attempts} att
              </text>
            </g>
          )}

          <text x="26" y="44" fill={stroke} fillOpacity="0.9" fontSize="4" fontFamily="monospace" fontWeight="600">
            {'>'} {cmd.slice(0, 28)}
          </text>
          {outLines.slice(0, 5).map((line, i) => (
            <text key={i} x="26" y={54 + i * 12} fill={stroke} fillOpacity={0.6 - i * 0.08} fontSize="3.5" fontFamily="monospace"
              style={{ animation: `hud-card-in 0.25s ${i * 0.06}s ease-out both` }}>
              {line.slice(0, 28)}
            </text>
          ))}
          {outLines.length > 5 && (
            <text x="26" y={54 + 5 * 12} fill={stroke} fillOpacity="0.35" fontSize="3" fontFamily="monospace">
              +{outLines.length - 5} lines
            </text>
          )}
          {data?.success === false && (
            <text x="26" y="105" fill="#ffb4ab" fillOpacity="0.8" fontSize="3.5" fontFamily="monospace">exit code 1</text>
          )}
        </g>
      )}

      {isDone && !cmd && outLines.length === 0 && !isError && (
        <g style={{ animation: 'hud-check-in 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards' }}>
          <text x="26" y="58" fill={stroke} fillOpacity="0.6" fontSize="4.5" fontFamily="monospace" fontWeight="600">Done</text>
          <circle cx="110" cy="100" r="7" fill="none" stroke={stroke} strokeWidth="1.5" />
          <polyline points="106,100 109,103 114,97" fill="none" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" />
        </g>
      )}

      {isError && (
        <g>
          <rect x="20" y="25" width="100" height="85" fill="#ffb4ab" fillOpacity="0.03" stroke="#ffb4ab" strokeWidth="0.8" strokeOpacity="0.3" />
          <text x="26" y="58" fill="#ffb4ab" fillOpacity="0.8" fontSize="4" fontFamily="monospace" fontWeight="700">FAILED</text>
          <text x="26" y="70" fill="#ffb4ab" fillOpacity="0.5" fontSize="3.5" fontFamily="monospace">
            {data?.total_attempts ? `${data.total_attempts} attempts` : 'error'}
          </text>
          <text x="26" y="84" fill="#ffb4ab" fillOpacity="0.35" fontSize="3" fontFamily="monospace">
            {output ? output.slice(0, 40) : (data?.error || '').slice(0, 40)}
          </text>
        </g>
      )}
    </svg>
  )
}
