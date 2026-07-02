import { useEffect, useRef, useCallback } from 'react'

const PHASES = [
  { id: 0, name: 'SIGNAL DETECTED',   start: 0,     dur: 2500 },
  { id: 1, name: 'MESSAGE DECODE',     start: 2500,  dur: 3000 },
  { id: 2, name: 'REMINDER DISPLAY',   start: 5500,  dur: 10000 },
  { id: 3, name: 'STANDBY',            start: 15500, dur: Infinity },
]

export default function WorkflowReminder({ data, onComplete }) {
  const tids = useRef([])
  const rafs = useRef([])
  const hudRef = useRef(null)
  const currentPid = useRef(-1)
  const startTime = useRef(0)
  const dataRef = useRef(data)
  dataRef.current = data

  const ct = useCallback((fn, delay) => {
    const id = setTimeout(fn, delay)
    tids.current.push(id)
    return id
  }, [])

  useEffect(() => {
    return () => {
      tids.current.forEach(clearTimeout)
      rafs.current.forEach(cancelAnimationFrame)
    }
  }, [])

  const e = (sel) => hudRef.current && hudRef.current.querySelector(sel)

  function show(el) { if (el) el.classList.add('active') }
  function hide(el) { if (el) el.classList.remove('active') }

  function typeText(el, text, speed = 40, cb) {
    if (!el) { if (cb) cb(); return }
    el.textContent = ''
    let i = 0
    function tick() {
      if (i >= text.length) { if (cb) cb(); return }
      el.textContent += text[i++]
      const id = requestAnimationFrame(tick)
      rafs.current.push(id)
    }
    tick()
  }

  function activatePhase(pid) {
    currentPid.current = pid
    switch (pid) {
      case 0:
        show(e('.wrem-grid'))
        ct(() => show(e('.wrem-scanline')), 300)
        ct(() => show(e('.wrem-signal-pulse')), 600)
        show(e('.wrem-signal-label'))
        ct(() => show(e('.wrem-corner.tl')), 200)
        ct(() => show(e('.wrem-corner.tr')), 300)
        ct(() => show(e('.wrem-corner.bl')), 400)
        ct(() => show(e('.wrem-corner.br')), 500)
        break

      case 1:
        show(e('.wrem-decoder'))
        ct(() => {
          const msg = dataRef.current?.message || 'No message'
          typeText(e('.wrem-message-text'), msg, 30, () => {
            ct(() => show(e('.wrem-message-cursor')), 500)
          })
        }, 400)
        break

      case 2:
        hide(e('.wrem-decoder'))
        hide(e('.wrem-signal-pulse'))
        hide(e('.wrem-signal-label'))
        const displayBody = e('.wrem-display-body')
        if (displayBody) displayBody.textContent = dataRef.current?.message || 'No message'
        show(e('.wrem-display'))
        break

      case 3:
        break
    }
  }

  useEffect(() => {
    startTime.current = Date.now()
    const unsub = []
    PHASES.forEach((p) => {
      if (p.dur === Infinity) return
      unsub.push(ct(() => activatePhase(p.id), p.start))
      unsub.push(ct(() => {
        const next = PHASES.find((x) => x.id === p.id + 1)
        if (next) activatePhase(next.id)
      }, p.start + p.dur))
    })
    ct(() => activatePhase(0), 10)
    return () => unsub.forEach((id) => clearTimeout(id))
  }, [])

  return (
    <div className="wf-hud wrem-hud" ref={hudRef}>
      <div className="wf-scanline wrem-scanline" />
      <div className="wf-grid-bg wrem-grid" />

      <svg className="wrem-corner tl" viewBox="0 0 40 40">
        <path d="M38 2 H2 V38" fill="none" stroke="var(--wf-cyan)" strokeWidth="2" />
      </svg>
      <svg className="wrem-corner tr" viewBox="0 0 40 40">
        <path d="M2 2 H38 V38" fill="none" stroke="var(--wf-cyan)" strokeWidth="2" />
      </svg>
      <svg className="wrem-corner bl" viewBox="0 0 40 40">
        <path d="M38 38 H2 V2" fill="none" stroke="var(--wf-cyan)" strokeWidth="2" />
      </svg>
      <svg className="wrem-corner br" viewBox="0 0 40 40">
        <path d="M2 38 H38 V2" fill="none" stroke="var(--wf-cyan)" strokeWidth="2" />
      </svg>

      <div className="wrem-signal-area">
        <div className="wrem-signal-pulse">
          <div className="wrem-pulse-ring" />
          <div className="wrem-pulse-ring wrem-pulse-ring-2" />
          <div className="wrem-pulse-dot" />
        </div>
        <div className="wrem-signal-label">REMINDER SIGNAL</div>
      </div>

      <div className="wrem-decoder">
        <div className="wrem-decoder-header">
          <span className="wrem-decoder-icon">◆</span>
          INCOMING MESSAGE
          <span className="wrem-decoder-badge">PRIORITY</span>
        </div>
        <div className="wrem-message-text" />
        <div className="wrem-message-cursor">▌</div>
      </div>

      <div className="wrem-display">
        <div className="wrem-display-bar" />
        <div className="wrem-display-icon">⏰</div>
        <div className="wrem-display-title">REMINDER</div>
        <div className="wrem-display-body" />
      </div>
    </div>
  )
}
