import { useEffect, useRef, useCallback } from 'react'

const PHASES = [
  { id: 0, name: 'DATABASE CONNECT',     start: 0,     dur: 3000 },
  { id: 1, name: 'MAINFRAME AUTH',       start: 3000,  dur: 2500 },
  { id: 2, name: 'PROFILE CARD',         start: 5500,  dur: 7500 },
  { id: 3, name: 'FACTS RETRIEVAL',      start: 13000, dur: 7000 },
  { id: 4, name: 'PEOPLE DIRECTORY',     start: 20000, dur: 5000 },
  { id: 5, name: 'LESSONS ARCHIVE',      start: 25000, dur: 5000 },
  { id: 6, name: 'CUSTOM SCHEMAS',       start: 30000, dur: 5000 },
  { id: 7, name: 'STANDBY',              start: 35000, dur: Infinity },
]

const CONNECT_TEXT = 'ACCESSING MEMORY DATABASE'

export default function WorkflowMemoryView({ data, onComplete }) {
  const tids = useRef([])
  const rafs = useRef([])
  const hudRef = useRef(null)
  const currentPid = useRef(-1)
  const startTime = useRef(0)
  const connectIdx = useRef(0)
  const dataRef = useRef(data)
  dataRef.current = data

  const ct = useCallback((fn, delay) => {
    const id = setTimeout(fn, delay)
    tids.current.push(id)
    return id
  }, [])

  const raf = useCallback((fn) => {
    const id = requestAnimationFrame(fn)
    rafs.current.push(id)
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

  function activatePhase(pid) {
    currentPid.current = pid
    switch (pid) {
      case 0:
        show(e('.wf-db-grid'))
        ct(() => show(e('.wf-db-scanline')), 400)
        ct(() => show(e('.wf-db-datastream')), 800)
        show(e('.wf-db-connect'))
        startConnectText()
        show(e('.wf-db-loader'))
        startLoadProgress()
        hide(e('.wf-db-empty'))
        break

      case 1:
        show(e('.wf-db-bracket.tl'))
        show(e('.wf-db-bracket.tr'))
        ct(() => {
          show(e('.wf-db-bracket.bl'))
          show(e('.wf-db-bracket.br'))
        }, 200)
        show(e('.wf-db-title'))
        show(e('.wf-db-status'))
        ct(() => show(e('.wf-db-badge')), 600)
        break

      case 2:
        hide(e('.wf-db-connect'))
        hide(e('.wf-db-loader'))
        show(e('.wf-db-profile'))
        populateProfile()
        ct(() => {
          const s = e('.wf-db-status')
          if (s) s.textContent = 'STATUS: RETRIEVING PROFILE'
        }, 100)
        break

      case 3: {
        hide(e('.wf-db-profile'))
        ct(() => {
          show(e('.wf-db-facts-area'))
          show(e('.wf-db-section-title.facts'))
          populateFacts()
          const fc = data?.facts?.length || 0
          ct(() => {
            const s = e('.wf-db-status')
            if (s) s.textContent = 'STATUS: ' + fc + ' FACTS FOUND'
          }, 100)
        }, 450)
        break
      }

      case 4: {
        hide(e('.wf-db-facts-area'))
        ct(() => {
          show(e('.wf-db-people-area'))
          show(e('.wf-db-section-title.people'))
          populatePeople()
          const pc = data?.people?.length || 0
          ct(() => {
            const s = e('.wf-db-status')
            if (s) s.textContent = 'STATUS: ' + pc + ' CONTACTS IN DIRECTORY'
          }, 100)
        }, 450)
        break
      }

      case 5: {
        hide(e('.wf-db-people-area'))
        ct(() => {
          show(e('.wf-db-lessons-area'))
          show(e('.wf-db-section-title.lessons'))
          populateLessons()
          const lc = data?.lessons?.length || 0
          ct(() => {
            const s = e('.wf-db-status')
            if (s) s.textContent = 'STATUS: ' + lc + ' LESSONS IN ARCHIVE'
          }, 100)
        }, 450)
        break
      }

      case 6: {
        hide(e('.wf-db-lessons-area'))
        ct(() => {
          show(e('.wf-db-schemas-area'))
          show(e('.wf-db-section-title.schemas'))
          populateSchemas()
          const sc = data?.custom_schemas?.schemas?.length || 0
          ct(() => {
            const s = e('.wf-db-status')
            if (s) s.textContent = 'STATUS: ' + sc + ' CUSTOM SCHEMAS'
          }, 100)
        }, 450)
        break
      }

      case 7:
        hide(e('.wf-db-schemas-area'))
        show(e('.wf-db-bottom-line'))
        show(e('.wf-db-summary'))
        ct(() => {
          const s = e('.wf-db-status')
          if (s) s.textContent = 'STATUS: STANDBY — AWAITING INPUT'
        }, 100)
        break
    }
  }

  function startConnectText() {
    const el = e('.wf-db-connect-text')
    if (!el) return
    el.textContent = ''
    connectIdx.current = 0
    function type() {
      if (connectIdx.current < CONNECT_TEXT.length) {
        el.textContent += CONNECT_TEXT[connectIdx.current]
        connectIdx.current++
        ct(type, 55)
      } else {
        const cur = e('.wf-db-connect .cursor')
        if (cur) cur.classList.add('done')
      }
    }
    ct(type, 200)
  }

  function startLoadProgress() {
    const fill = e('.wf-db-loader .fill')
    if (!fill) return
    fill.classList.add('active')
  }

  function populateProfile() {
    const profile = dataRef.current?.profile
    if (!profile) return
    const vn = e('.wf-db-field.name .value')
    const vnat = e('.wf-db-field.nation .value')
    const vc = e('.wf-db-field.creator .value')
    const vl = e('.wf-db-field.lang .value')
    if (vn) vn.textContent = profile.name || '---'
    if (vnat) vnat.textContent = profile.nationality || '---'
    if (vc) vc.textContent = profile.creator || '---'
    if (vl) vl.textContent = profile.language === 'en' ? 'English' : profile.language || '---'

    const prefs = e('.wf-db-prefs')
    if (prefs) {
      prefs.innerHTML = ''
      const entries = Object.entries(profile.preferences || {}).slice(0, 5)
      if (entries.length) {
        entries.forEach(([k, v]) => {
          const chip = document.createElement('span')
          chip.className = 'wf-db-chip'
          chip.textContent = k + ': ' + v
          prefs.appendChild(chip)
        })
        show(prefs)
      }
    }

    document.querySelectorAll('.wf-db-field').forEach((f, i) => {
      ct(() => f.classList.add('active'), i * 200)
    })
    ct(() => {
      if (prefs) show(prefs)
    }, 1000)
  }

  function populateFacts() {
    const grid = e('.wf-db-facts-grid')
    if (!grid) return
    grid.innerHTML = ''
    hide(e('.wf-db-empty'))
    const facts = dataRef.current?.facts
    if (!facts || !facts.length) {
      e('.wf-db-empty .msg').textContent = 'NO FACTS STORED YET — THEY\'LL APPEAR HERE AS WE TALK'
      show(e('.wf-db-empty'))
      return
    }
    facts.forEach((f, i) => {
      const card = document.createElement('div')
      card.className = 'wf-db-fact-card'
      card.innerHTML = '<div class="key">' + (f.key || '').replace(/_/g, ' ') + '</div><div class="val">' + (f.value || '') + '</div>'
      grid.appendChild(card)
      ct(() => card.classList.add('active'), i * 120)
    })
    const s = e('.wf-db-summary .num.facts')
    if (s) s.textContent = facts.length
  }

  function populatePeople() {
    const scroll = e('.wf-db-people-scroll')
    if (!scroll) return
    scroll.innerHTML = ''
    hide(e('.wf-db-empty'))
    const people = dataRef.current?.people
    if (!people || !people.length) {
      e('.wf-db-empty .msg').textContent = 'NO PEOPLE IN DIRECTORY YET — THEY\'LL APPEAR HERE AS WE TALK'
      show(e('.wf-db-empty'))
      return
    }
    people.forEach((p, i) => {
      const card = document.createElement('div')
      card.className = 'wf-db-person-card'
      card.innerHTML = '<div class="name">' + (p.name || '') + '</div><div class="rel">' + ((p.relationship || '?').toUpperCase()) + '</div><div class="traits">' + (p.traits || '') + '</div>'
      scroll.appendChild(card)
      ct(() => card.classList.add('active'), i * 120)
    })
    const s = e('.wf-db-summary .num.people')
    if (s) s.textContent = people.length
  }

  function populateLessons() {
    const list = e('.wf-db-lessons-list')
    if (!list) return
    list.innerHTML = ''
    hide(e('.wf-db-empty'))
    const lessons = dataRef.current?.lessons
    if (!lessons || !lessons.length) {
      e('.wf-db-empty .msg').textContent = 'NO LESSONS RECORDED YET — THEY\'LL APPEAR HERE AS WE TALK'
      show(e('.wf-db-empty'))
      return
    }
    lessons.forEach((l, i) => {
      const entry = document.createElement('div')
      entry.className = 'wf-db-lesson-entry'
      entry.innerHTML = '<div class="sit">' + (l.situation || '') + '</div><div class="cor">' + (l.correction || '') + '</div>'
      list.appendChild(entry)
      ct(() => entry.classList.add('active'), i * 120)
    })
    const s = e('.wf-db-summary .num.lessons')
    if (s) s.textContent = lessons.length
  }

  function populateSchemas() {
    const container = e('.wf-db-schemas-list')
    if (!container) return
    container.innerHTML = ''
    hide(e('.wf-db-empty'))
    const schemas = dataRef.current?.custom_schemas?.schemas
    const entries = dataRef.current?.custom_schemas?.entries || {}
    if (!schemas || !schemas.length) {
      e('.wf-db-empty .msg').textContent = 'NO CUSTOM SCHEMAS CREATED YET — THEY\'LL APPEAR HERE AS WE TALK'
      show(e('.wf-db-empty'))
      return
    }
    schemas.forEach((s, i) => {
      const block = document.createElement('div')
      block.className = 'wf-db-schema-block'
      const name = s.name || 'unnamed'
      const cols = (s.columns || []).map(c => c.name).join(', ')
      const entryList = entries[name] || []
      let html = '<div class="schema-header">■ ' + name.toUpperCase() + '</div>'
      if (cols) html += '<div class="schema-cols">' + cols + '</div>'
      if (s.description) html += '<div class="schema-desc">' + s.description + '</div>'
      if (entryList.length) {
        html += '<div class="schema-entries">'
        entryList.slice(0, 5).forEach(e => {
          const vals = Object.entries(e.data || {}).map(([k, v]) => '<span class="schema-field"><em>' + k + '</em> ' + v + '</span>').join(' ')
          html += '<div class="schema-entry">' + vals + '</div>'
        })
        if (entryList.length > 5) html += '<div class="schema-more">+' + (entryList.length - 5) + ' more</div>'
        html += '</div>'
      }
      block.innerHTML = html
      container.appendChild(block)
      ct(() => block.classList.add('active'), i * 200)
    })
    const s = e('.wf-db-summary .num.schemas')
    if (s) s.textContent = schemas.length
  }

  useEffect(() => {
    startTime.current = performance.now()
    currentPid.current = -1

    function tick(now) {
      const elapsed = now - startTime.current
      const pid = PHASES.reduce((acc, p) => (elapsed >= p.start ? p.id : acc), 0)
      if (pid !== currentPid.current) {
        activatePhase(pid)
      }
      if (pid < 7) {
        rafs.current.push(requestAnimationFrame(tick))
      }
    }
    rafs.current.push(requestAnimationFrame(tick))

    return () => {
      tids.current.forEach(clearTimeout)
      rafs.current.forEach(cancelAnimationFrame)
      tids.current = []
      rafs.current = []
    }
  }, [])

  return (
    <div className="wf-db-hud" ref={hudRef}>
      <div className="wf-db-grid"></div>
      <div className="wf-db-scanline"></div>
      <div className="wf-db-datastream"></div>

      <svg className="wf-db-bracket tl"><line x1="0" y1="22" x2="0" y2="0"/><line x1="0" y1="0" x2="22" y2="0"/></svg>
      <svg className="wf-db-bracket tr"><line x1="0" y1="22" x2="0" y2="0"/><line x1="0" y1="0" x2="22" y2="0"/></svg>
      <svg className="wf-db-bracket bl"><line x1="0" y1="22" x2="0" y2="0"/><line x1="0" y1="0" x2="22" y2="0"/></svg>
      <svg className="wf-db-bracket br"><line x1="0" y1="22" x2="0" y2="0"/><line x1="0" y1="0" x2="22" y2="0"/></svg>

      <div className="wf-db-title">■ MEMORY DATABASE<span className="cursor"></span></div>
      <div className="wf-db-status">STATUS: INITIALIZING</div>

      <div className="wf-db-badge">✓ IDENTITY CONFIRMED</div>

      <div className="wf-db-connect"><span className="wf-db-connect-text"></span><span className="cursor"></span></div>

      <div className="wf-db-loader">
        <div className="label">ACCESSING DATA CORE<span>.</span><span>.</span><span>.</span></div>
        <div className="bar"><div className="fill"></div></div>
      </div>

      <div className="wf-db-profile">
        <div className="header">■ PRIMARY PROFILE RECORD</div>
        <div className="wf-db-field name"><span className="icon">👤</span><span className="label">NAME</span><span className="value">---</span></div>
        <div className="wf-db-field nation"><span className="icon">🌍</span><span className="label">NATIONALITY</span><span className="value">---</span></div>
        <div className="wf-db-field creator"><span className="icon">⚡</span><span className="label">CREATOR</span><span className="value">---</span></div>
        <div className="wf-db-field lang"><span className="icon">🔤</span><span className="label">LANGUAGE</span><span className="value">---</span></div>
        <div className="wf-db-prefs"></div>
      </div>

      <div className="wf-db-facts-area">
        <div className="wf-db-section-title facts">■ STORED FACTS — KEY-VALUE RECORDS</div>
        <div className="wf-db-facts-grid"></div>
      </div>

      <div className="wf-db-people-area">
        <div className="wf-db-section-title people">■ CONTACT DIRECTORY — PEOPLE</div>
        <div className="wf-db-people-scroll"></div>
      </div>

      <div className="wf-db-lessons-area">
        <div className="wf-db-section-title lessons">■ LESSONS ARCHIVE — LEARNED EXPERIENCES</div>
        <div className="wf-db-lessons-list"></div>
      </div>

      <div className="wf-db-schemas-area">
        <div className="wf-db-section-title schemas">■ CUSTOM SCHEMAS — STRUCTURED DATA</div>
        <div className="wf-db-schemas-list"></div>
      </div>

      <div className="wf-db-empty">
        <div className="icon">🗄️</div>
        <div className="msg">NO RECORDS FOUND</div>
      </div>

      <div className="wf-db-bottom-line"></div>

      <div className="wf-db-summary">
        MEMORY DATABASE — <span className="num facts">0</span> FACTS · <span className="num people">0</span> PEOPLE · <span className="num lessons">0</span> LESSONS · <span className="num schemas">0</span> SCHEMAS
      </div>
    </div>
  )
}
