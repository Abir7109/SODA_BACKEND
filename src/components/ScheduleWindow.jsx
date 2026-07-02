import { useState, useEffect, useRef } from 'react'

function getMonthGrid(year, month) {
  const first = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const grid = []
  let day = 1
  for (let r = 0; r < 6; r++) {
    const row = []
    for (let c = 0; c < 7; c++) {
      if ((r === 0 && c < first) || day > daysInMonth) {
        row.push(null)
      } else {
        row.push(day++)
      }
    }
    grid.push(row)
    if (day > daysInMonth) break
  }
  return grid
}

const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December']
const DAYS = ['Su','Mo','Tu','We','Th','Fr','Sa']

function AnalogClock() {
  const [time, setTime] = useState(new Date())
  const reqRef = useRef(null)

  useEffect(() => {
    const tick = () => {
      setTime(new Date())
      reqRef.current = requestAnimationFrame(tick)
    }
    reqRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(reqRef.current)
  }, [])

  const h = time.getHours() % 12
  const m = time.getMinutes()
  const s = time.getSeconds() + time.getMilliseconds() / 1000
  const hDeg = (h / 12) * 360 + (m / 60) * 30
  const mDeg = (m / 60) * 360 + (s / 60) * 6
  const sDeg = (s / 60) * 360

  return (
    <svg width="100" height="100" viewBox="0 0 130 130">
      <defs>
        <filter id="clockGlow">
          <feGaussianBlur stdDeviation="1.5" result="blur"/>
          <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>
      <circle cx="65" cy="65" r="60" fill="none" stroke="var(--accent, #00fbfb)" strokeWidth="2" opacity="0.3"/>
      <circle cx="65" cy="65" r="58" fill="rgba(0,0,0,0.6)" stroke="var(--accent, #00fbfb)" strokeWidth="1"/>
      {[...Array(12)].map((_, i) => {
        const ang = (i * 30 - 90) * Math.PI / 180
        const outer = i % 3 === 0 ? 52 : 54
        const inner = i % 3 === 0 ? 46 : 50
        return (
          <line key={i}
            x1={65 + outer * Math.cos(ang)} y1={65 + outer * Math.sin(ang)}
            x2={65 + inner * Math.cos(ang)} y2={65 + inner * Math.sin(ang)}
            stroke={i % 3 === 0 ? 'var(--accent, #00fbfb)' : 'rgba(200,200,200,0.4)'}
            strokeWidth={i % 3 === 0 ? 2 : 1}
          />
        )
      })}
      {[12, 3, 6, 9].map(n => {
        const ang = ((n / 12) * 360 - 90) * Math.PI / 180
        const r2 = 38
        return (
          <text key={n}
            x={65 + r2 * Math.cos(ang)} y={65 + r2 * Math.sin(ang)}
            textAnchor="middle" dominantBaseline="central"
            fill="var(--accent, #00fbfb)" fontSize="9" fontWeight="600"
            fontFamily="monospace"
          >{n}</text>
        )
      })}
      <line x1="65" y1="65" x2={65 + 28 * Math.cos((hDeg - 90) * Math.PI / 180)}
            y2={65 + 28 * Math.sin((hDeg - 90) * Math.PI / 180)}
            stroke="white" strokeWidth="3" strokeLinecap="round" style={{ filter: 'url(#clockGlow)' }}/>
      <line x1="65" y1="65" x2={65 + 40 * Math.cos((mDeg - 90) * Math.PI / 180)}
            y2={65 + 40 * Math.sin((mDeg - 90) * Math.PI / 180)}
            stroke="white" strokeWidth="2" strokeLinecap="round" style={{ filter: 'url(#clockGlow)' }}/>
      <line x1="65" y1="65" x2={65 + 44 * Math.cos((sDeg - 90) * Math.PI / 180)}
            y2={65 + 44 * Math.sin((sDeg - 90) * Math.PI / 180)}
            stroke="#ff4444" strokeWidth="1.2" strokeLinecap="round"/>
      <circle cx="65" cy="65" r="2.5" fill="#ff4444"/>
    </svg>
  )
}

function Calendar({ schedules, highlightDate }) {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth())
  const [animDate, setAnimDate] = useState(null)
  const grid = getMonthGrid(year, month)

  const schedDates = new Set(
    (schedules || []).map(s => s.date).filter(Boolean)
  )

  useEffect(() => {
    if (highlightDate) {
      setAnimDate(highlightDate)
      const timer = setTimeout(() => setAnimDate(null), 2000)
      return () => clearTimeout(timer)
    }
  }, [highlightDate])

  const today = now.toISOString().slice(0, 10)

  return (
    <div style={{ width: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <button onClick={() => setMonth(m => m === 0 ? (setYear(y => y - 1), 11) : m - 1)}
          style={navBtnStyle}>&lt;</button>
        <span style={{ color: 'var(--text-primary)', fontSize: 12, fontWeight: 600 }}>
          {MONTHS[month]} {year}
        </span>
        <button onClick={() => setMonth(m => m === 11 ? (setYear(y => y + 1), 0) : m + 1)}
          style={navBtnStyle}>&gt;</button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 0 }}>
        {DAYS.map(d => (
          <div key={d} style={{ color: 'var(--text-dim)', fontSize: 8, textAlign: 'center', padding: '2px 0' }}>{d}</div>
        ))}
        {grid.flat().map((day, i) => {
          if (day === null) return <div key={`e${i}`}/>
          const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
          const hasSched = schedDates.has(dateStr)
          const isToday = dateStr === today
          const isHighlight = highlightDate === dateStr
          return (
            <div key={dateStr} style={{
              position: 'relative', textAlign: 'center', padding: '2px 0', fontSize: 10,
              color: isToday ? 'var(--accent, #00fbfb)' : 'var(--text-primary)',
              fontWeight: isToday ? 700 : 400,
              background: isToday ? 'rgba(0,251,251,0.08)' : 'transparent',
              borderRadius: 3,
              animation: isHighlight ? 'schedPulse 2s ease-out' : 'none',
            }}>
              {day}
              {hasSched && (
                <div style={{
                  width: 4, height: 4, borderRadius: '50%',
                  background: 'var(--accent, #00fbfb)',
                  margin: '1px auto 0',
                  boxShadow: isHighlight ? '0 0 6px var(--accent, #00fbfb)' : 'none',
                }}/>
              )}
            </div>
          )
        })}
      </div>
      <style>{`
        @keyframes schedPulse {
          0% { box-shadow: 0 0 0 0 rgba(0,251,251,0.6); }
          70% { box-shadow: 0 0 0 8px rgba(0,251,251,0); }
          100% { box-shadow: 0 0 0 0 rgba(0,251,251,0); }
        }
      `}</style>
    </div>
  )
}

const navBtnStyle = {
  background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
  color: 'var(--text-secondary)', borderRadius: 3, cursor: 'pointer',
  fontSize: 11, padding: '2px 8px', lineHeight: '16px',
}

export default function ScheduleWindow({ data }) {
  const schedule = data?.schedule || null
  const allSchedules = data?.all_schedules || []
  const highlightDate = schedule?.date || null

  const [schedules, setSchedules] = useState(allSchedules)

  const handleDelete = async (sid) => {
    try {
      const res = await fetch('/api/tool', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool: 'delete_schedule', args: { id: sid } }),
      })
      const result = await res.json()
      if (result.success) {
        setSchedules(prev => prev.filter(s => s.id !== sid))
      }
    } catch {}
  }

  return (
    <div style={{ padding: 12, height: '100%', display: 'flex', flexDirection: 'column', gap: 12, overflow: 'hidden' }}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', flexWrap: 'wrap', justifyContent: 'center' }}>
        <div style={{ flexShrink: 0 }}>
          <AnalogClock />
        </div>
        <div style={{ flex: '1 1 200px', minWidth: 0 }}>
          <Calendar schedules={schedules} highlightDate={highlightDate} />
        </div>
      </div>

      <div style={{
        flex: 1, overflowY: 'auto', minHeight: 0,
        borderTop: '1px solid rgba(255,255,255,0.06)',
        paddingTop: 8,
      }}>
        <div style={{ color: 'var(--text-dim)', fontSize: 10, marginBottom: 6, fontWeight: 600 }}>
          SCHEDULES ({schedules.length})
        </div>
        {schedules.length === 0 ? (
          <div style={{ color: 'var(--text-dim)', fontSize: 11, fontStyle: 'italic', padding: '12px 0', textAlign: 'center' }}>
            No schedules saved yet
          </div>
        ) : (
          schedules.map(s => (
            <div key={s.id} style={{
              display: 'flex', gap: 8, padding: '6px 8px', marginBottom: 4,
              background: 'rgba(255,255,255,0.03)', borderRadius: 4,
              border: '1px solid rgba(255,255,255,0.05)',
              alignItems: 'flex-start',
            }}>
              <div style={{
                flexShrink: 0, width: 36, textAlign: 'center',
                background: 'rgba(0,251,251,0.1)', borderRadius: 4, padding: '3px 4px',
              }}>
                <div style={{ color: 'var(--accent, #00fbfb)', fontSize: 10, fontWeight: 700 }}>
                  {s.date ? s.date.slice(8, 10) : '--'}
                </div>
                <div style={{ color: 'var(--text-dim)', fontSize: 8 }}>
                  {s.date ? new Date(s.date + 'T12:00:00').toLocaleString('en', { month: 'short' }) : ''}
                </div>
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ color: 'var(--text-primary)', fontSize: 11, fontWeight: 600 }}>{s.title}</div>
                {s.time && <div style={{ color: 'var(--accent, #00fbfb)', fontSize: 9 }}>{s.time}</div>}
                {s.details && <div style={{ color: 'var(--text-dim)', fontSize: 9, marginTop: 1 }}>{s.details}</div>}
              </div>
              <button onClick={() => handleDelete(s.id)}
                style={{
                  background: 'none', border: 'none', color: 'rgba(255,80,80,0.5)', cursor: 'pointer',
                  fontSize: 12, padding: 2, lineHeight: '14px', flexShrink: 0,
                }}
                title="Delete schedule">✕</button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
