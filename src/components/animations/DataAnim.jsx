export default function DataAnim({ status, variant = 'weather', data = null }) {
  const isError = status === 'error'
  const isDone = status === 'done'
  const isRunning = status === 'pending' || status === 'running'
  const stroke = isError ? 'var(--error)' : '#00fbfb'

  const renderVariant = () => {
    switch (variant) {

      case 'weather': {
        const temp = data?.temperature != null ? Math.round(data.temperature) : '--'
        const humidity = data?.humidity ?? '--'
        const wind = data?.wind_speed ?? '--'
        const loc = data?.location || ''
        return (
          <g>
            <circle cx="55" cy="50" r="12" fill={stroke} fillOpacity="0.15" stroke={stroke} strokeWidth="1" strokeOpacity="0.5"
              style={isRunning ? { transformOrigin: '55px 50px', animation: 'soda-sun-rotate 6s linear infinite' } : {}} />
            {[0, 45, 90, 135, 180, 225, 270, 315].map((deg, i) => {
              const rad = (deg * Math.PI) / 180
              return <line key={i} x1={55 + 15 * Math.cos(rad)} y1={50 + 15 * Math.sin(rad)}
                x2={55 + 20 * Math.cos(rad)} y2={50 + 20 * Math.sin(rad)}
                stroke={stroke} strokeWidth="1.2" strokeOpacity="0.3"
                style={isRunning ? { transformOrigin: '55px 50px', animation: `soda-ray-pulse 1.5s ${i * 0.15}s ease-in-out infinite` } : {}} />
            })}
            <g style={isRunning ? { animation: 'soda-cloud-drift 3.5s ease-in-out infinite' } : {}}>
              <circle cx="82" cy="46" r="7" fill={stroke} fillOpacity="0.06" />
              <circle cx="90" cy="44" r="9" fill={stroke} fillOpacity="0.05" />
              <circle cx="97" cy="48" r="6" fill={stroke} fillOpacity="0.07" />
            </g>
            {isDone && <text x="70" y="85" textAnchor="middle" fill={stroke} fillOpacity="0.8" fontSize="8" fontFamily="Space Grotesk" fontWeight="700">{temp}°</text>}
            {isDone && loc && <text x="70" y="98" textAnchor="middle" fill={stroke} fillOpacity="0.4" fontSize="3.5" fontFamily="monospace">{loc.slice(0, 15)}</text>}
            {isDone && <text x="70" y="110" textAnchor="middle" fill={stroke} fillOpacity="0.3" fontSize="3" fontFamily="monospace">H:{humidity}% W:{wind}km/h</text>}
          </g>
        )
      }

      case 'news': {
        const articles = data?.results || data?.articles || []
        return (
          <g>
            {isRunning && [0, 1, 2].map((i) => (
              <g key={i} style={{ animation: `hud-card-in 0.35s ${i * 0.12}s ease-out both` }}>
                <rect x="20" y={32 + i * 28} width="100" height="20" rx="2" fill={stroke} fillOpacity="0.04" stroke={stroke} strokeWidth="0.6" strokeOpacity="0.15" />
                <rect x="26" y={38 + i * 28} width={50 - i * 10} height="3" rx="1" fill={stroke} fillOpacity="0.2" />
                <rect x="26" y={44 + i * 28} width={70 - i * 15} height="2" rx="1" fill={stroke} fillOpacity="0.1" />
              </g>
            ))}
            {isDone && articles.slice(0, 4).map((a, i) => (
              <g key={i} style={{ animation: `hud-card-in 0.25s ${i * 0.08}s ease-out both` }}>
                <rect x="20" y={30 + i * 25} width="100" height="18" rx="2" fill={stroke} fillOpacity="0.04" stroke={stroke} strokeWidth="0.5" strokeOpacity="0.12" />
                <text x="26" y={41 + i * 25} fill={stroke} fillOpacity={0.7 - i * 0.1} fontSize="3.5" fontFamily="monospace" fontWeight="500">
                  {(a.title || '').slice(0, 26)}
                </text>
                <text x="26" y={47 + i * 25} fill={stroke} fillOpacity={0.25} fontSize="2.5" fontFamily="monospace">
                  {(a.source || a.published || '').slice(0, 20)}
                </text>
              </g>
            ))}
            {articles.length > 4 && (
              <text x="20" y="135" fill={stroke} fillOpacity="0.35" fontSize="3" fontFamily="monospace">+{articles.length - 4} more</text>
            )}
          </g>
        )
      }

      case 'currency': {
        const from = data?.from || data?.base || 'USD'
        const to = data?.to || data?.target || 'INR'
        const rate = data?.rate ?? data?.exchange_rate ?? '--'
        return (
          <g>
            <text x="30" y="55" fill={stroke} fillOpacity="0.6" fontSize="10" fontFamily="Space Grotesk" fontWeight="700">{from}</text>
            <g style={isRunning ? { animation: 'soda-arrow-pulse 0.8s ease-in-out infinite' } : isDone ? { animation: 'soda-arrow-pulse 0.5s ease-out' } : {}}>
              <line x1="55" y1="52" x2="80" y2="52" stroke={stroke} strokeWidth="1.5" strokeOpacity="0.5" />
              <polygon points="77,48 85,52 77,56" fill={stroke} fillOpacity="0.5" />
            </g>
            <text x="92" y="55" fill={stroke} fillOpacity="0.6" fontSize="10" fontFamily="Space Grotesk" fontWeight="700">{to}</text>
            {isRunning && <rect x="25" y="72" width="90" height="4" rx="2" fill={stroke} fillOpacity="0.08" />}
            {isDone && (
              <g>
                <text x="70" y="80" textAnchor="middle" fill={stroke} fillOpacity="0.8" fontSize="7" fontFamily="Space Grotesk" fontWeight="600">
                  1 {from} = {rate} {to}
                </text>
                <rect x="25" y="90" width="90" height="4" rx="2" fill={stroke} fillOpacity="0.08" />
                <rect x="25" y="90" width="60" height="4" rx="2" fill={stroke} fillOpacity="0.4"
                  style={{ animation: 'soda-bar-fill 0.8s ease-out' }} />
              </g>
            )}
          </g>
        )
      }

      case 'system': {
        const cpu = data?.cpu_percent ?? 0
        const ram = data?.ram_percent ?? 0
        const disk = data?.disk_percent ?? null
        return (
          <g>
            <circle cx="45" cy="50" r="18" fill="none" stroke={stroke} strokeWidth="2" strokeOpacity="0.1" />
            <circle cx="45" cy="50" r="18" fill="none" stroke={stroke} strokeWidth="2.5" strokeOpacity="0.6"
              strokeDasharray="113" strokeDashoffset={isDone ? 113 - (cpu / 100) * 113 : isRunning ? 80 : 113}
              strokeLinecap="round" transform="rotate(-90 45 50)"
              style={{ transition: 'stroke-dashoffset 0.8s ease-out' }} />
            <text x="45" y="54" textAnchor="middle" fill={stroke} fillOpacity={isDone ? 0.8 : 0.4} fontSize="6" fontFamily="monospace" fontWeight="600">
              {isDone ? `${Math.round(cpu)}%` : 'CPU'}
            </text>
            <circle cx="95" cy="50" r="18" fill="none" stroke={stroke} strokeWidth="2" strokeOpacity="0.1" />
            <circle cx="95" cy="50" r="18" fill="none" stroke={stroke} strokeWidth="2.5" strokeOpacity="0.6"
              strokeDasharray="113" strokeDashoffset={isDone ? 113 - (ram / 100) * 113 : isRunning ? 80 : 113}
              strokeLinecap="round" transform="rotate(-90 95 50)"
              style={{ transition: 'stroke-dashoffset 0.8s 0.15s ease-out' }} />
            <text x="95" y="54" textAnchor="middle" fill={stroke} fillOpacity={isDone ? 0.8 : 0.4} fontSize="6" fontFamily="monospace" fontWeight="600">
              {isDone ? `${Math.round(ram)}%` : 'RAM'}
            </text>
            {disk != null && (
              <g>
                <rect x="25" y="82" width="90" height="4" rx="2" fill={stroke} fillOpacity="0.08" />
                <rect x="25" y="82" width={isDone ? `${disk}%` : '20%'} height="4" rx="2" fill={stroke} fillOpacity="0.4"
                  style={{ transition: 'width 0.8s 0.3s ease-out' }} />
                <text x="70" y="95" textAnchor="middle" fill={stroke} fillOpacity={isDone ? 0.5 : 0.3} fontSize="3.5" fontFamily="monospace">
                  {isDone ? `DISK ${Math.round(disk)}%` : 'DISK'}
                </text>
              </g>
            )}
          </g>
        )
      }

      case 'processes': {
        const procs = data?.processes || []
        return (
          <g>
            {isRunning && [0, 1, 2, 3, 4].map((i) => (
              <g key={i} style={{ animation: `hud-card-in 0.25s ${i * 0.08}s ease-out both` }}>
                <rect x="20" y={30 + i * 17} width="60" height="4" rx="2" fill={stroke} fillOpacity="0.04" />
                <rect x="85" y={30 + i * 17} width="35" height="4" rx="2" fill={stroke} fillOpacity="0.08" />
              </g>
            ))}
            {isDone && procs.slice(0, 6).map((p, i) => (
              <g key={i} style={{ animation: `hud-card-in 0.2s ${i * 0.05}s ease-out both` }}>
                <text x="22" y={35 + i * 15} fill={stroke} fillOpacity={0.6 - i * 0.06} fontSize="3" fontFamily="monospace">
                  {(p.name || '?').slice(0, 14)}
                </text>
                <rect x="85" y={30 + i * 15} width="35" height="4" rx="2" fill={stroke} fillOpacity="0.08" />
                <rect x="85" y={30 + i * 15} width={Math.min((p.memory_percent || p.memory || 0), 100) / 100 * 35} height="4" rx="2"
                  fill={stroke} fillOpacity="0.35"
                  style={{ transition: 'width 0.6s ease-out' }} />
              </g>
            ))}
            {procs.length > 6 && (
              <text x="22" y="135" fill={stroke} fillOpacity="0.3" fontSize="3" fontFamily="monospace">+{procs.length - 6}</text>
            )}
          </g>
        )
      }

      case 'network': {
        const ip = data?.ip || data?.query || '--'
        const city = data?.city || ''
        const country = data?.country || data?.country_name || ''
        const org = data?.org || data?.isp || ''
        return (
          <g>
            <circle cx="70" cy="48" r="18" fill="none" stroke={stroke} strokeWidth="1.2" strokeOpacity="0.3" />
            <ellipse cx="70" cy="48" rx="18" ry="9" fill="none" stroke={stroke} strokeWidth="0.8" strokeOpacity="0.2" />
            <line x1="70" y1="30" x2="70" y2="66" stroke={stroke} strokeWidth="0.8" strokeOpacity="0.2" />
            <g style={isRunning ? { transformOrigin: '70px 48px', animation: 'soda-pin-bounce 0.8s ease-in-out infinite' } : {}}>
              <circle cx="70" cy="42" r="4" fill={stroke} fillOpacity="0.3" />
              <polygon points="70,46 67,52 73,52" fill={stroke} fillOpacity="0.3" />
            </g>
            {isDone && ip && (
              <text x="70" y="80" textAnchor="middle" fill={stroke} fillOpacity="0.8" fontSize="5" fontFamily="monospace" fontWeight="600">{ip}</text>
            )}
            {isDone && (city || country) && (
              <text x="70" y="90" textAnchor="middle" fill={stroke} fillOpacity="0.4" fontSize="3.5" fontFamily="monospace">{[city, country].filter(Boolean).join(', ').slice(0, 20)}</text>
            )}
            {isDone && org && (
              <text x="70" y="100" textAnchor="middle" fill={stroke} fillOpacity="0.3" fontSize="3" fontFamily="monospace">{org.slice(0, 22)}</text>
            )}
          </g>
        )
      }

      case 'define': {
        const word = data?.word || ''
        const def = data?.definition || data?.definitions?.[0] || ''
        return (
          <g>
            <path d="M 38 32 L 38 90 L 102 90 L 102 32 L 70 37 L 38 32 Z" fill={stroke} fillOpacity="0.04" stroke={stroke} strokeWidth="1" strokeOpacity="0.4" rx="2" />
            <line x1="70" y1="37" x2="70" y2="90" stroke={stroke} strokeWidth="0.6" strokeOpacity="0.2" />
            {isRunning && [48, 56, 64, 72, 80].map((y, i) => (
              <rect key={i} x="44" y={y} width={14 + i * 8} height="3" rx="1" fill={stroke} fillOpacity="0.12"
                style={{ animation: `hud-card-in 0.25s ${i * 0.08}s ease-out both` }} />
            ))}
            {isDone && (
              <g>
                <text x="46" y="48" fill={stroke} fillOpacity="0.85" fontSize="5" fontFamily="Space Grotesk" fontWeight="700">
                  {(word || '').slice(0, 14)}
                </text>
                <text x="46" y="60" fill={stroke} fillOpacity="0.5" fontSize="3" fontFamily="monospace">
                  {('/' + (data?.pronunciation || '') + '/').slice(0, 20)}
                </text>
                <text x="46" y="72" fill={stroke} fillOpacity="0.6" fontSize="3.5" fontFamily="monospace">
                  {(def || '').slice(0, 22)}
                </text>
                {(def || '').length > 22 && (
                  <text x="46" y="80" fill={stroke} fillOpacity="0.4" fontSize="3" fontFamily="monospace">
                    {(def || '').slice(22, 45)}
                  </text>
                )}
              </g>
            )}
          </g>
        )
      }

      case 'wiki': {
        const title = data?.title || ''
        const summary = data?.summary || ''
        return (
          <g>
            <circle cx="70" cy="45" r="20" fill="none" stroke={stroke} strokeWidth="1.2" strokeOpacity="0.25" />
            {isRunning && <text x="70" y="51" textAnchor="middle" fill={stroke} fillOpacity="0.5" fontSize="14" fontFamily="serif" fontWeight="700"
              style={{ animation: 'hud-glow-pulse 1.5s ease-in-out infinite' }}>W</text>}
            {isDone && <text x="70" y="51" textAnchor="middle" fill={stroke} fillOpacity="0.7" fontSize="14" fontFamily="serif" fontWeight="700">W</text>}
            {isDone && title && (
              <text x="70" y="75" textAnchor="middle" fill={stroke} fillOpacity="0.8" fontSize="4.5" fontFamily="Space Grotesk" fontWeight="600">
                {title.slice(0, 20)}
              </text>
            )}
            {isRunning && [83, 91, 99].map((y, i) => (
              <rect key={i} x="35" y={y} width={12 + i * 20} height="3" rx="1" fill={stroke} fillOpacity="0.12"
                style={{ animation: `hud-card-in 0.25s ${i * 0.1}s ease-out both` }} />
            ))}
            {isDone && summary && (
              <text x="35" y="88" fill={stroke} fillOpacity="0.5" fontSize="3" fontFamily="monospace">
                {(summary || '').slice(0, 24)}
              </text>
            )}
          </g>
        )
      }

      case 'speed': {
        const seo = data?.scores?.seo ?? 0
        const perf = data?.scores?.performance ?? 0
        const a11y = data?.scores?.accessibility ?? 0
        const bp = data?.scores?.best_practices ?? 0
        const opps = data?.opportunities?.length ?? 0
        const arcs = [
          { angle: 20, score: seo, label: 'SEO' },
          { angle: 80, score: perf, label: 'PERF' },
          { angle: 140, score: a11y, label: 'A11Y' },
          { angle: 200, score: bp, label: 'BP' },
        ]
        const cx = 70, cy = 62
        return (
          <g>
            {/* Scan line (radar sweep) */}
            {isRunning && (
              <line x1={cx} y1={cy} x2={cx + 48} y2={cy}
                stroke={stroke} strokeWidth="1" strokeOpacity="0.35"
                style={{ transformOrigin: `${cx}px ${cy}px`, animation: 'soda-sun-rotate 2.5s linear infinite' }} />
            )}
            {/* Grid rings */}
            {[16, 32, 48].map((r) => (
              <circle key={r} cx={cx} cy={cy} r={r} fill="none" stroke={stroke} strokeWidth="0.5" strokeOpacity="0.1" />
            ))}
            {/* Score arcs */}
            {arcs.map((a, i) => {
              const rad = ((a.angle - 90) * Math.PI) / 180
              const x = cx + 44 * Math.cos(rad)
              const y = cy + 44 * Math.sin(rad)
              const color = a.score >= 90 ? '#00ff88' : a.score >= 50 ? '#ffaa00' : '#ff3355'
              return (
                <g key={i}>
                  <circle cx={x} cy={y} r="5" fill={color} fillOpacity={isRunning ? 0.2 : 0.4}
                    stroke={color} strokeWidth="1"
                    style={isRunning ? { animation: `hud-glow-pulse 1.5s ${i * 0.3}s ease-in-out infinite` } : {}} />
                  {isDone && (
                    <g>
                      <text x={x} y={y - 9} textAnchor="middle" fill={color} fontSize="5" fontFamily="monospace" fontWeight="700">{a.score}</text>
                      <text x={x} y={y + 13} textAnchor="middle" fill={color} fillOpacity="0.5" fontSize="3" fontFamily="monospace">{a.label}</text>
                    </g>
                  )}
                  {isRunning && <text x={x} y={y + 13} textAnchor="middle" fill={stroke} fillOpacity="0.3" fontSize="3" fontFamily="monospace">{a.label}</text>}
                </g>
              )
            })}
            {/* Center glow */}
            <circle cx={cx} cy={cy} r="8" fill="none" stroke={stroke} strokeWidth="1.2" strokeOpacity="0.2"
              style={isRunning ? { transformOrigin: `${cx}px ${cy}px`, animation: 'soda-glow-pulse 2s ease-in-out infinite' } : {}} />
            <circle cx={cx} cy={cy} r="3" fill={stroke} fillOpacity="0.3" />
            {/* Bottom stats */}
            {isDone && (
              <g>
                <text x={cx} y={cy + 22} textAnchor="middle" fill={stroke} fillOpacity="0.4" fontSize="3.5" fontFamily="monospace">
                  {opps} optimization{opps !== 1 ? 's' : ''} found
                </text>
                <text x={cx} y={cy + 30} textAnchor="middle" fill={stroke} fillOpacity="0.2" fontSize="2.8" fontFamily="monospace">
                  Core Web Vitals analyzed
                </text>
              </g>
            )}
          </g>
        )
      }

      case 'email': {
        const emails = data?.emails || []
        return (
          <g>
            <g stroke={stroke} strokeWidth="1.2" fill="none" strokeOpacity="0.3">
              <rect x="28" y="32" width="84" height="14" rx="2" />
              <polyline points="28,32 70,42 112,32" strokeOpacity="0.5" />
              <rect x="28" y="50" width="84" height="10" rx="1.5" strokeOpacity="0.15" />
              <rect x="28" y="64" width="84" height="10" rx="1.5" strokeOpacity="0.12" />
              <rect x="28" y="78" width="84" height="10" rx="1.5" strokeOpacity="0.1" />
            </g>
            {isRunning && (
              <g>
                <rect x="34" y="54" width="40" height="2" rx="1" fill={stroke} fillOpacity="0.15" />
                <rect x="34" y="68" width="60" height="2" rx="1" fill={stroke} fillOpacity="0.12" />
                <rect x="34" y="82" width="50" height="2" rx="1" fill={stroke} fillOpacity="0.1" />
              </g>
            )}
            {isDone && emails.length > 0 && (
              <g>
                <text x="34" y="58" fill={stroke} fillOpacity="0.5" fontSize="3.5" fontFamily="monospace">
                  {(emails[0]?.from || '').slice(0, 14)}
                </text>
                <text x="34" y="72" fill={stroke} fillOpacity="0.6" fontSize="3.5" fontFamily="monospace">
                  {(emails[0]?.subject || '').slice(0, 16)}
                </text>
                <text x="70" y="100" textAnchor="middle" fill={stroke} fillOpacity="0.35" fontSize="3" fontFamily="monospace">
                  +{emails.length - 1} more
                </text>
              </g>
            )}
            {isDone && emails.length === 0 && (
              <text x="70" y="80" textAnchor="middle" fill={stroke} fillOpacity="0.35" fontSize="3.5" fontFamily="monospace">
                No emails
              </text>
            )}
          </g>
        )
      }

      default:
        return (
          <circle cx="70" cy="70" r="20" fill="none" stroke={stroke} strokeWidth="1.5"
            style={isRunning ? { transformOrigin: '70px 70px', animation: 'hud-glow-pulse 1.5s ease-in-out infinite' } : {}} />
        )
    }
  }

  return (
    <svg viewBox="0 0 140 140" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="d-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.12" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </radialGradient>
        <filter id="d-glow-filter">
          <feGaussianBlur stdDeviation="1.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <pattern id="d-grid" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
          <line x1="20" y1="0" x2="20" y2="20" stroke={stroke} strokeWidth="0.3" strokeOpacity="0.04" />
          <line x1="0" y1="20" x2="20" y2="20" stroke={stroke} strokeWidth="0.3" strokeOpacity="0.04" />
        </pattern>
      </defs>

      <rect x="4" y="4" width="132" height="132" fill="url(#d-grid)"
        style={isRunning ? { animation: 'hud-grid-pulse 4s ease-in-out infinite' } : {}} />

      <circle cx="70" cy="70" r="60" fill="url(#d-glow)" />

      <g stroke={stroke} strokeWidth="1.2" strokeOpacity="0.25" fill="none"
        style={{ animation: 'hud-bracket-in 0.4s ease-out' }}>
        <path d="M 8 14 L 8 8 L 14 8" />
        <path d="M 132 8 L 126 8 L 126 14" />
        <path d="M 8 126 L 8 132 L 14 132" />
        <path d="M 132 126 L 132 132 L 126 132" />
      </g>

      {renderVariant()}

      {isDone && !isError && variant !== 'showcase' && (
        <g style={{ animation: 'hud-check-in 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards' }}>
          <circle cx="70" cy="70" r="16" fill={stroke} fillOpacity="0.03" filter="url(#d-glow-filter)" />
          <circle cx="115" cy="110" r="6" fill="none" stroke={stroke} strokeWidth="1.5" strokeOpacity="0.5" />
          <polyline points="111,110 114,113 119,107" fill="none" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" />
        </g>
      )}
    </svg>
  )
}
