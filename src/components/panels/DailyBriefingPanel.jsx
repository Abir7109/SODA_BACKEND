import { useState, useEffect, useRef, useCallback } from 'react'
import { animate, createTimeline, stagger } from 'animejs'
import SlidePanel from '../SlidePanel'
import { Sun, CalendarDays, Bell, Mail, Newspaper, Brain, Clock, Thermometer, Droplets, Wind, MapPin } from 'lucide-react'

const SECTION_ICONS = {
  weather: Sun,
  schedule: CalendarDays,
  reminders: Bell,
  emails: Mail,
  news: Newspaper,
  memory: Brain,
  activity: Clock,
}

const PHASE_TITLES = {
  morning: 'MORNING BRIEF',
  day: 'DAY RECAP',
  night: 'NIGHT RECAP',
}

const PHASE_ACCENTS = {
  morning: '#00fbfb',
  day: '#fff176',
  night: '#a78bfa',
}

function fmtTime(secs) {
  if (secs == null) return ''
  const s = Math.max(0, Math.round(secs))
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m`
  return `${Math.floor(m / 60)}h ${m % 60}m`
}

function fmtClock(d) {
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function SectionCard({ type, title, data, accent }) {
  const Icon = SECTION_ICONS[type] || Sun
  if (!data || (Array.isArray(data) && data.length === 0) || (typeof data === 'object' && Object.keys(data).length === 0)) {
    return (
      <div className="db-section" data-type={type}>
        <div className="db-section-label">
          <Icon size={10} />
          <span>{title}</span>
        </div>
        <div className="sp-empty">Nothing to report</div>
      </div>
    )
  }

  return (
    <div className="db-section" data-type={type}>
      <div className="db-section-label">
        <Icon size={10} />
        <span>{title}</span>
      </div>

      {type === 'weather' && (
        <div className="sp-weather-panel">
          <div className="sp-weather-main">
            <div className="db-weather-location">
              <MapPin size={10} /> {data.location}
            </div>
            <div className="sp-weather-temp db-weather-temp">{Math.round(data.temperature)}°C</div>
            <div className="sp-weather-location">Feels like {Math.round(data.feels_like)}°C</div>
          </div>
          <div className="sp-weather-details">
            <div className="sp-weather-detail">
              <span className="sp-weather-detail-label">Humidity</span>
              <span className="sp-weather-detail-value">{data.humidity}%</span>
            </div>
            <div className="sp-weather-detail">
              <span className="sp-weather-detail-label">Wind</span>
              <span className="sp-weather-detail-value">{data.wind_speed} km/h</span>
            </div>
            <div className="sp-weather-detail">
              <span className="sp-weather-detail-label">Clouds</span>
              <span className="sp-weather-detail-value">{data.cloud_cover}%</span>
            </div>
          </div>
        </div>
      )}

      {type === 'schedule' && (
        <div className="db-timeline">
          {data.map((s, i) => (
            <div key={s.id || i} className="db-timeline-row">
              <div className="db-timeline-rail">
                <div className="db-timeline-node" />
                {i < data.length - 1 && <div className="db-timeline-line" />}
              </div>
              <div className="db-timeline-body">
                <div className="db-timeline-time">{s.time || '--:--'}</div>
                <div className="db-timeline-title">{s.title}</div>
                {s.details && <div className="db-timeline-detail">{s.details}</div>}
              </div>
            </div>
          ))}
        </div>
      )}

      {type === 'reminders' && (
        <div className="db-list">
          {data.map(r => (
            <div key={r.id} className="db-list-row">
              <span className="db-list-message">{r.message}</span>
              <span className="db-list-badge">{fmtTime(r.seconds_until_fire)}</span>
            </div>
          ))}
        </div>
      )}

      {type === 'emails' && (
        <div className="db-list">
          {data.map((e, i) => (
            <div key={e.id || i} className="db-list-row db-email-row">
              <div className="db-email-main">
                <span className="db-email-subject">{e.subject}</span>
                <span className="db-email-from">{e.from}</span>
              </div>
              <span className="db-unread-badge">{i === 0 ? 'NEW' : 'UNREAD'}</span>
            </div>
          ))}
        </div>
      )}

      {type === 'news' && (
        <div className="sp-news-panel">
          {data.map((n, i) => (
            <div key={n.id || i} className="sp-news-panel-card">
              <div className="sp-news-panel-index">{i + 1}</div>
              <div className="sp-news-panel-content">
                <div className="sp-news-panel-title">{n.title}</div>
                {n.description && <div className="sp-news-panel-desc">{n.description}</div>}
                {n.time && <div className="sp-news-panel-meta"><span className="sp-news-panel-source">{n.time}</span></div>}
              </div>
            </div>
          ))}
        </div>
      )}

      {type === 'memory' && (
        <div className="sp-memory-container">
          <div className="sp-memory-section">
            {data.facts && data.facts.length > 0 ? (
              data.facts.map((f, i) => (
                <div key={i} className="sp-memory-row">
                  <span className="sp-memory-key">{f.key}:</span>
                  <span className="sp-memory-val">{f.value}</span>
                </div>
              ))
            ) : (
              <div className="sp-empty">No saved facts yet</div>
            )}
            <div className="sp-memory-more">{data.fact_count} facts in memory</div>
          </div>
        </div>
      )}

      {type === 'activity' && (
        <div className="db-list">
          {data.length === 0 ? (
            <div className="sp-empty">Quiet so far today</div>
          ) : (
            data.map((e, i) => (
              <div key={i} className="db-list-row db-activity-row">
                <span className="db-activity-time">{e.ts ? e.ts.slice(11, 16) : ''}</span>
                <span className="db-activity-label">{e.label}</span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

export default function DailyBriefingPanel({ visible, data, onClose }) {
  const [now, setNow] = useState(new Date())
  const bodyRef = useRef(null)
  const headerRef = useRef(null)
  const timerRef = useRef(null)

  useEffect(() => {
    if (!visible) return
    timerRef.current = setInterval(() => setNow(new Date()), 30000)
    return () => clearInterval(timerRef.current)
  }, [visible])

  useEffect(() => {
    if (!visible || !bodyRef.current) return
    const ctx = bodyRef.current
    const sections = ctx.querySelectorAll('.db-section')

    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReduced) {
      ctx.querySelectorAll('.db-section').forEach(el => { el.style.opacity = 1 })
      return
    }

    const tl = createTimeline({ defaults: { ease: 'outExpo' } })

    tl.add(animate(headerRef.current, {
      opacity: [0, 1],
      translateY: [10, 0],
      duration: 350,
    }), 0)

    tl.add(animate(sections, {
      opacity: [0, 1],
      translateX: [26, 0],
      duration: 420,
      delay: stagger(70),
    }), 0.1)

    const tempEl = ctx.querySelector('.db-weather-temp')
    if (tempEl) {
      tl.add(animate(tempEl, {
        innerHTML: [0, parseInt(tempEl.textContent || '0', 10)],
        modifiers: { innerHTML: (v) => Math.round(v) + '°C' },
        duration: 900,
        ease: 'outExpo',
      }), 0.5)
    }

    const timelineLines = ctx.querySelectorAll('.db-timeline-line')
    if (timelineLines.length) {
      tl.add(animate(timelineLines, {
        scaleY: [0, 1],
        transformOrigin: 'top center',
        duration: 300,
        ease: 'outCubic',
        delay: stagger(90),
      }), 0.45)
    }

    const timelineNodes = ctx.querySelectorAll('.db-timeline-node')
    if (timelineNodes.length) {
      tl.add(animate(timelineNodes, {
        scale: [0, 1],
        duration: 200,
        ease: 'outBack(2)',
        delay: stagger(90),
      }), 0.5)
    }

    return () => {
      tl.pause()
      tl.seek(0)
    }
  }, [visible, data])

  const handleClose = useCallback(() => { onClose?.() }, [onClose])
  const phase = data?.phase || 'morning'
  const accent = PHASE_ACCENTS[phase] || '#00fbfb'

  return (
    <SlidePanel
      visible={visible}
      direction="right"
      title={PHASE_TITLES[phase] || 'BRIEFING'}
      icon={<Sun size={11} />}
      accentColor={accent}
      onClose={handleClose}
      autoDismissMs={20000}
    >
      <div ref={headerRef} className="db-header" style={{ opacity: 0 }}>
        <div className="db-header-row">
          <div className="db-header-date">{data?.date || ''}</div>
          <div className="db-header-time"><Clock size={9} /> {data?.time || fmtClock(now)}</div>
        </div>
        <div className="db-header-greeting" style={{ color: accent }}>{data?.greeting || ''}</div>
      </div>

      <div ref={bodyRef}>
        {(data?.sections || []).map((s, i) => (
          <SectionCard key={i} type={s.type} title={s.title} data={s.data} accent={accent} />
        ))}
      </div>
    </SlidePanel>
  )
}
