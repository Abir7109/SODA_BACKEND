import { useState, useEffect, useRef, useCallback, Suspense, Component } from 'react'
import socket from './services/SocketService'
import { getCategory, CATEGORIES, getAnimationForTool, getVariantForTool, getSpecializedPanel } from './components/animations'

function getCapacitorNotifications() {
  try {
    const cap = window.Capacitor
    if (cap && cap.Plugins && cap.Plugins.LocalNotifications) {
      return cap.Plugins.LocalNotifications
    }
  } catch (e) { /* not in Capacitor */ }
  return null
}

async function showNotification(title, body, id) {
  const ln = getCapacitorNotifications()
  if (!ln) return
  try {
    await ln.requestPermissions()
    await ln.schedule({
      notifications: [{
        id: id || Math.floor(Math.random() * 1000000),
        title,
        body,
        schedule: { at: new Date() },
        smallIcon: 'ic_stat_soda',
        iconColor: '#0a0a0f',
        channelId: 'soda-reminders',
      }]
    })
  } catch (e) { /* notification failed */ }
}

async function prescheduleNotification(id, title, body, fireAt) {
  const ln = getCapacitorNotifications()
  if (!ln) return
  try {
    console.log('[Preschedule]', { id, title, fireAt })
    const result = await ln.schedule({
      notifications: [{
        id,
        title,
        body,
        schedule: { at: new Date(fireAt) },
        smallIcon: 'ic_stat_soda',
        iconColor: '#0a0a0f',
        channelId: 'soda-reminders',
      }]
    })
    console.log('[Preschedule] Success', JSON.stringify(result))
  } catch (e) { console.error('[Preschedule] Error', e) }
}

async function requestNotifPermission() {
  const ln = getCapacitorNotifications()
  if (!ln) return
  try {
    await ln.requestPermissions()
  } catch (e) { /* permission denied */ }
  try {
    await ln.createChannel({
      id: 'soda-reminders',
      name: 'SODA Reminders',
      importance: 4,
      visibility: 1,
      sound: 'default',
      vibration: true,
      lights: true
    })
  } catch (e) { /* channel exists or not supported */ }
}
import SearchResultsPanel from './components/panels/SearchResultsPanel'
import FileOutputPanel from './components/panels/FileOutputPanel'
import InfoPanel from './components/panels/InfoPanel'
import ToolOutputPanel from './components/panels/ToolOutputPanel'
import WebpageSummaryPanel from './components/panels/WebpageSummaryPanel'
import FileBrowserPanel from './components/panels/FileBrowserPanel'

import WeatherPanel from './components/panels/WeatherPanel'
import SystemStatusPanel from './components/panels/SystemStatusPanel'
import CurrencyPanel from './components/panels/CurrencyPanel'
import FloatingWindow from './components/FloatingWindow'
import WebviewWindow from './components/WebviewWindow'
import ScrapedDataPanel from './components/panels/ScrapedDataPanel'
import ProcessListPanel from './components/panels/ProcessListPanel'
import NetworkInfoPanel from './components/panels/NetworkInfoPanel'
import TaskTerminalPanel from './components/panels/TaskTerminalPanel'
import PentestResultsPanel from './components/panels/PentestResultsPanel'
import PentestProgressIndicator from './components/PentestProgressIndicator'
import GitHubPanel from './components/panels/GitHubPanel'
import DeployPanel from './components/panels/DeployPanel'
import PageSpeedPanel from './components/panels/PageSpeedPanel'
import EmailPanel from './components/panels/EmailPanel'
import MemoryPanel from './components/panels/MemoryPanel'
import IELTSDashboardPanel from './components/panels/IELTSDashboardPanel'
import IELTSWritingPanel from './components/panels/IELTSWritingPanel'
import IELTSSpeakingPanel from './components/panels/IELTSSpeakingPanel'
import IELTSReadingPanel from './components/panels/IELTSReadingPanel'
import IELTSVocabPanel from './components/panels/IELTSVocabPanel'
import IELTSProgressPanel from './components/panels/IELTSProgressPanel'
import SpotifySearchPanel from './components/panels/SpotifySearchPanel'
import NavigationPanel from './components/panels/NavigationPanel'
import { PanelSpaceProvider } from './contexts/PanelSpaceContext'
import WebviewActionService from './services/WebviewActionService'
import SlidePanel from './components/SlidePanel'
import CameraCapture from './components/CameraCapture'
import HolographicOrb from './components/HolographicOrb'
import Notepad from './components/Notepad'
import BackgroundWidget from './components/BackgroundWidget'
import PasteBox from './components/pastebox/PasteBox'
import CameraWidget from './components/CameraWidget'
import useBrowserMic, { resumeMicAudio } from './services/useBrowserMic'
// --- Frontend Error Logging ---
if (typeof socket !== 'undefined') {
  window.onerror = (msg, url, line, col, err) => {
    socket.emit('client_log', {
      level: 'error',
      message: msg,
      location: url ? `${url}:${line}:${col}` : `${line}:${col}`,
      stack: err?.stack || ''
    })
  }
  window.onunhandledrejection = (event) => {
    socket.emit('client_log', {
      level: 'error',
      message: event.reason?.message || String(event.reason),
      stack: event.reason?.stack || ''
    })
  }
}
import ScheduleWindow from './components/ScheduleWindow'

const STATUS_LABELS = {
  pending: 'awaiting',
  running: 'running',
  done: 'complete',
  error: 'failed',
  cancelled: 'cancelled'
}

class AnimationErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }
  static getDerivedStateFromError() {
    return { hasError: true }
  }
  componentDidCatch(error, info) {
    console.warn('[SODA] Animation error caught:', error?.message)
  }
  render() {
    if (this.state.hasError) {
      return this.props.fallback || null
    }
    return this.props.children
  }
}

class RootErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }
  componentDidCatch(error) {
    console.error('[SODA] Root error:', error)
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          height: '100vh', background: 'var(--bg)', color: 'var(--text)',
          fontFamily: 'monospace', textAlign: 'center', padding: '2rem'
        }}>
          <h1 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>SODA encountered an error</h1>
          <p style={{ color: 'var(--text-dim)', marginBottom: '1.5rem', maxWidth: '500px', fontSize: '0.85rem' }}>
            {this.state.error?.message || 'Unknown error'}
          </p>
          <button onClick={() => { this.setState({ hasError: false, error: null }); window.location.reload() }}
            style={{
              padding: '0.5rem 1.5rem', border: '1px solid var(--accent)', borderRadius: '4px',
              background: 'transparent', color: 'var(--accent)', cursor: 'pointer'
            }}>
            Reload SODA
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

const STATUS_COLORS = {
  pending: 'var(--accent)',
  running: 'var(--accent)',
  done: 'var(--success)',
  error: 'var(--error)',
  cancelled: 'var(--text-dim)'
}

const TOOLS_WITH_OUTPUT = new Set([
  'write_file', 'read_file', 'read_directory',
  'clipboard_read', 'clipboard_write', 'screenshot',
  'run_code', 'list_processes', 'get_active_window',
  'create_project', 'switch_project', 'list_projects',
])

const TOOLS_WITH_INFO_PANEL = new Set([
  'get_news', 'get_bangladeshi_news', 'get_ip_info',
  'get_exchange_rate', 'define_word', 'get_wikipedia_summary',
  'remember_fact', 'recall_facts',
  'get_user_profile', 'set_preference',
  'forget_fact', 'list_memory',
  'remember_person', 'recall_person', 'remember_lesson',
  'list_reminders', 'cancel_reminder',
  'create_memory_schema', 'list_custom_schemas',
  'store_custom_memory', 'query_custom_memory',
])

const AI_CARD_TOOLS = new Set([
  'get_system_status', 'get_weather', 'terminal_execute', 'set_reminder', 'search_and_send_telegram', 'shutdown_soda',
])

const VISION_TOOLS = new Set([
  'screenshot', 'analyze_screen', 'read_screen_text', 'take_photo', 'recognize_face', 'remember_face',
])

function AnimationStage({ category, status, toolName, data }) {
  const AnimComponent = getAnimationForTool(toolName)
  const variant = getVariantForTool(toolName)
  return (
    <AnimationErrorBoundary fallback={null}>
      <Suspense fallback={null}>
        <AnimComponent status={status} variant={variant} data={data} />
      </Suspense>
    </AnimationErrorBoundary>
  )
}

function TerminalPanel({ visible, command, output, success, onClose, attempts, total_attempts }) {
  const scrollRef = useRef(null)
  const [pos, setPos] = useState({ x: 12, y: 12 })
  const dragRef = useRef(null)

  const handleMouseDown = (e) => {
    if (e.target.closest('.terminal-close')) return
    dragRef.current = { mx: e.clientX, my: e.clientY, ox: pos.x, oy: pos.y }
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    e.preventDefault()
  }

  const handleMouseMove = (e) => {
    if (!dragRef.current) return
    setPos({
      x: Math.max(0, Math.min(dragRef.current.ox + e.clientX - dragRef.current.mx, window.innerWidth - 408)),
      y: Math.max(0, Math.min(dragRef.current.oy + e.clientY - dragRef.current.my, window.innerHeight - 60)),
    })
  }

  const handleMouseUp = () => {
    dragRef.current = null
    document.removeEventListener('mousemove', handleMouseMove)
    document.removeEventListener('mouseup', handleMouseUp)
  }

  useEffect(() => {
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [output])

  return (
    <div
      className="terminal-panel"
      style={{
        left: pos.x,
        top: pos.y,
        transform: visible ? 'translateX(0)' : 'translateX(-110%)',
        opacity: visible ? 1 : 0,
      }}
    >
      <div
        className="terminal-header"
        onMouseDown={handleMouseDown}
      >
        <div className="terminal-header-left">
          <span className="terminal-dot" style={{ background: '#ff5f57' }} />
          <span className="terminal-dot" style={{ background: '#febc2e' }} />
          <span className="terminal-dot" style={{ background: '#28c840' }} />
        </div>
        <span className="terminal-title">TERMINAL</span>
        {total_attempts > 1 && (
          <span className="text-[9px] font-mono opacity-50 ml-2">{total_attempts} attempt{total_attempts > 1 ? 's' : ''}</span>
        )}
        <button className="terminal-close" onClick={onClose}>✕</button>
      </div>

      <div className="terminal-body" ref={scrollRef}>
        {command && (
          <div className="terminal-line">
            <span className="terminal-prompt">❯ </span>
            <span className="terminal-command">{command}</span>
          </div>
        )}
        {output && (
          <pre className="terminal-output" style={{ color: success === false ? '#ffb4ab' : '#c8c8c8' }}>
            {output}
          </pre>
        )}
        {!output && (
          <div className="terminal-cursor-line">
            <span className="terminal-prompt">❯ </span>
            <span className="terminal-blink-cursor">█</span>
          </div>
        )}
      </div>

      <div className="terminal-status-bar">
        <span style={{ color: success === false ? '#ffb4ab' : '#00fbfb' }}>
          {output ? (success === false ? 'FAILED' : 'DONE') : 'RUNNING...'}
        </span>
      </div>
    </div>
  )
}

function FloatingContent({ content }) {
  const webviewRef = useRef(null)

  useEffect(() => {
    if (content?.type === 'web' && content?.id) {
      const wv = webviewRef.current
      if (!wv) return
      const onReady = () => WebviewActionService.register(content.id, wv)
      wv.addEventListener('dom-ready', onReady)
      wv.addEventListener('did-finish-load', onReady)
      return () => {
        wv.removeEventListener('dom-ready', onReady)
        wv.removeEventListener('did-finish-load', onReady)
        WebviewActionService.unregister(content.id)
      }
    }
  }, [content?.type, content?.id])

  if (!content) return <div className="sp-empty">no data</div>

  switch (content.type) {
    case 'terminal':
      return (
        <>
          {content.command && (
            <div className="terminal-line">
              <span className="terminal-prompt">❯ </span>
              <span className="terminal-command">{content.command}</span>
            </div>
          )}
          <pre className="terminal-output" style={{ color: content.success === false ? '#ffb4ab' : '#c8c8c8' }}>
            {content.output || 'No output.'}
          </pre>
        </>
      )

    case 'notepad':
      return <Notepad id={content.id || 'notepad'} initialTabs={content.tabs || []} />

    case 'web': {
      const url = content.url
      if (!url) return <div className="sp-empty">no url</div>
      return <WebviewWindow webviewRef={webviewRef} url={url} id={content.id} />
    }

    case 'search':
      return (
        <>
          <div className="sp-search-query">
            <span className="sp-label">QUERY</span>
            <span className="sp-value">{content.query}</span>
          </div>
          <div className="sp-results-list">
            {(content.results || []).map((r, i) => (
              <div key={i} className="sp-result-card" style={{ border: '1px solid rgba(0,251,251,0.1)', padding: '8px 10px', marginBottom: 4 }}>
                <div className="sp-result-title">{r.title}</div>
                {r.url && <div className="sp-result-url">{r.url}</div>}
                {r.snippet && <div className="sp-result-snippet">{r.snippet}</div>}
              </div>
            ))}
            {(!content.results || content.results.length === 0) && (
              <div className="sp-empty">no results</div>
            )}
          </div>
        </>
      )

    case 'webpage':
      return (
        <>
          {content.url && (
            <div className="sp-search-query">
              <span className="sp-label">URL</span>
              <span className="sp-value" style={{ fontSize: 11, wordBreak: 'break-all' }}>{content.url}</span>
            </div>
          )}
          {content.images && content.images.length > 0 && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 10 }}>
              {content.images.map((img, i) => (
                <div key={i} style={{ border: '1px solid rgba(0,251,251,0.1)', overflow: 'hidden', aspectRatio: '16/10' }}>
                  <img src={img} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                </div>
              ))}
            </div>
          )}
          <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.85)', lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {content.content || 'No content.'}
          </div>
        </>
      )

    case 'files':
      return (
        <>
          {content.path && (
            <div className="sp-search-query">
              <span className="sp-label">PATH</span>
              <span className="sp-value" style={{ fontSize: 11 }}>{content.path}</span>
            </div>
          )}
          <div className="sp-file-list">
            {(content.items || []).map((item, i) => (
              <div key={i} className="sp-file-item" style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 6px', borderBottom: '1px solid rgba(0,251,251,0.05)' }}>
                <span className="sp-file-number">{item.number || i + 1}</span>
                <span className="sp-file-name" style={{ fontSize: 12, flex: 1 }}>{item.name || item}</span>
                {item.type && <span className="sp-file-meta" style={{ fontSize: 10, opacity: 0.5 }}>{item.type}</span>}
                {item.size && <span className="sp-file-meta" style={{ fontSize: 10, opacity: 0.5 }}>{item.size}</span>}
              </div>
            ))}
            {(!content.items || content.items.length === 0) && (
              <div className="sp-empty">empty directory</div>
            )}
          </div>
        </>
      )

    case 'output':
      return (
        <pre className="sp-output-pre" style={{ color: content.success === false ? '#ffb4ab' : '#c8c8c8' }}>
          {content.content || 'No output.'}
        </pre>
      )

    case 'text':
      return (
        <pre className="sp-output-pre" style={{ color: '#c8c8c8' }}>
          {content.text || 'No data.'}
        </pre>
      )

    case 'file_viewer':
      if (content.mediaType === 'image') {
        return (
          <div className="floating-file-viewer" style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#000', overflow: 'hidden' }}>
            <img src={`data:${content.mime};base64,${content.content}`} alt={content.path} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
          </div>
        )
      }
      if (content.mediaType === 'video') {
        return (
          <div className="floating-file-viewer" style={{ width: '100%', height: '100%', background: '#000', overflow: 'hidden' }}>
            <video src={`data:${content.mime};base64,${content.content}`} controls autoPlay style={{ width: '100%', height: '100%' }} />
          </div>
        )
      }
      return (
        <div className="floating-file-viewer" style={{ width: '100%', height: '100%', overflow: 'auto', background: '#0a0e12' }}>
          <pre className="sp-output-pre" style={{ margin: 0, minHeight: '100%', color: '#c8c8c8', whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: 12, lineHeight: 1.5 }}>
            {content.content || 'No content.'}
          </pre>
        </div>
      )

    case 'error':
      return (
        <div style={{ textAlign: 'center', padding: 20 }}>
          <div style={{ color: '#ffb4ab', fontSize: 14, marginBottom: 8 }}>⚠ ERROR</div>
          <div style={{ color: 'rgba(255,180,171,0.7)', fontSize: 12 }}>{content.msg}</div>
        </div>
      )

    case 'schedule':
      return <ScheduleWindow data={content.data} />

    case 'pastebox':
      return <PasteBox id={content.id} />

    case 'camera':
      return <CameraWidget socket={socket} />

    default:
      return (
        <pre className="sp-output-pre" style={{ color: '#c8c8c8' }}>
          {JSON.stringify(content, null, 2)}
        </pre>
      )
  }
}

function WidgetApp() {
  const [speakingState, setSpeakingState] = useState('idle')
  const [ready, setReady] = useState(false)

  useEffect(() => {
    document.body.classList.add('widget-mode')
    return () => document.body.classList.remove('widget-mode')
  }, [])

  useEffect(() => {
    socket.connect()
    const onConnect = () => { setReady(true) }
    const onSpeakingState = (data) => {
      if (data && data.state) setSpeakingState(data.state)
    }
    const onBackgroundMode = (data) => {
      if (data && data.active === false && window.electron?.exitBackground) {
        window.electron.exitBackground()
      }
    }
    socket.on('connect', onConnect)
    socket.on('speaking_state', onSpeakingState)
    socket.on('background_mode', onBackgroundMode)
    return () => {
      socket.off('connect', onConnect)
      socket.off('speaking_state', onSpeakingState)
      socket.off('background_mode', onBackgroundMode)
    }
  }, [])

  const handleRestore = () => {
    socket.emit('wake_up')
  }

  if (!ready) return null

  return <BackgroundWidget speakingState={speakingState} onRestore={handleRestore} widgetMode={true} />
}

const isWidgetMode = typeof window !== 'undefined' && new URLSearchParams(window.location.search).has('widget')

export default function App() {
  if (isWidgetMode) return <WidgetApp />

  const [connectionStatus, setConnectionStatus] = useState('disconnected')
  const [agentState, setAgentState] = useState(null)
  const [task, setTask] = useState(null)
  const [taskData, setTaskData] = useState(null)
  const pendingIdRef = useRef(null)
  const clearTimerRef = useRef(null)

  // Terminal panel state (left)
  const [terminal, setTerminal] = useState({ visible: false, command: '', output: '', success: null, attempts: [], total_attempts: 1 })
  const terminalTimerRef = useRef(null)

  // Search results panel state (right)
  const [search, setSearch] = useState({ visible: false, query: '', results: [] })
  const searchTimerRef = useRef(null)

  // Spotify search results panel state (right)
  const [spotifySearch, setSpotifySearch] = useState({ visible: false, query: '', results: [] })
  const spotifySearchTimerRef = useRef(null)

  // File/clipboard/code output panel state (bottom)
  const [fileOutput, setFileOutput] = useState({ visible: false, type: 'file', title: '', content: '', success: null })
  const fileTimerRef = useRef(null)

  // Info panel state (top) — weather, news, API results
  const [infoPanel, setInfoPanel] = useState({ visible: false, type: 'info', data: null })
  const infoTimerRef = useRef(null)

  // Tool output / confirmation panel (bottom)
  const [toolPanel, setToolPanel] = useState({ visible: false, toolName: '', status: 'running', output: null, args: null })

  // Webpage summary panel state (bottom)
  const [webpageSummary, setWebpageSummary] = useState({ visible: false, url: '', content: '', success: null, images: [] })
  const webpageTimerRef = useRef(null)

  // File browser panel state (bottom)
  const [fileBrowser, setFileBrowser] = useState({ visible: false, path: '', items: [], success: null, searchQuery: '' })
  const fileBrowserTimerRef = useRef(null)
  const toolTimerRef = useRef(null)
  const clearTaskTimeoutRef = useRef(null)

  // Tool showcase panel state (right)

  // Scraped data panel state (bottom)
  const [scrapedData, setScrapedData] = useState({ visible: false, data: null, url: '' })

  // Specialized data panels
  const [weatherPanel, setWeatherPanel] = useState({ visible: false, data: null })
  const [systemStatusPanel, setSystemStatusPanel] = useState({ visible: false, data: null })
  const [memoryPanel, setMemoryPanel] = useState({ visible: false, data: null })
  const [currencyPanel, setCurrencyPanel] = useState({ visible: false, data: null })
  const [processPanel, setProcessPanel] = useState({ visible: false, data: null })
  const [networkPanel, setNetworkPanel] = useState({ visible: false, data: null })
  const [taskTerminalVisible, setTaskTerminalVisible] = useState(false)
  const [pentestVisible, setPentestVisible] = useState(false)
  const [pentestActive, setPentestActive] = useState(false)
  const [pentestProgress, setPentestProgress] = useState(null)
  const [pentestResult, setPentestResult] = useState(null)
  const [gitHubPanel, setGitHubPanel] = useState({ visible: false, data: null })
  const [deployPanel, setDeployPanel] = useState({ visible: false, data: null })
  const [pageSpeedPanel, setPageSpeedPanel] = useState({ visible: false, data: null })
  const [emailPanel, setEmailPanel] = useState({ visible: false, data: null })
  const [navigation, setNavigation] = useState({ visible: false, data: null })
  const [ieltsDashboard, setIeltsDashboard] = useState({ visible: false, data: null, direction: 'right' })
  const [ieltsWriting, setIeltsWriting] = useState({ visible: false, data: null, direction: 'right' })
  const [ieltsSpeaking, setIeltsSpeaking] = useState({ visible: false, data: null, direction: 'right' })
  const [ieltsReading, setIeltsReading] = useState({ visible: false, data: null, direction: 'right' })
  const [ieltsVocab, setIeltsVocab] = useState({ visible: false, data: null, direction: 'right' })
  const [ieltsProgress, setIeltsProgress] = useState({ visible: false, data: null, direction: 'right' })
  const [orbMicLevel, setOrbMicLevel] = useState(0)
  const [remoteCount, setRemoteCount] = useState(0)

  // Personality / mood system
  const [personalityText, setPersonalityText] = useState(null)
  const [personalityMood, setPersonalityMood] = useState('neutral')
  const [idleMode, setIdleMode] = useState(false)
  const [backgroundMode, setBackgroundMode] = useState(false)
  const [speakingState, setSpeakingState] = useState('idle')
  const personalityTimerRef = useRef(null)

  // ── Browser mic capture (web) ──
  const { micActive: browserMicActive, micError: browserMicError, start: startBrowserMic, stop: stopBrowserMic } = useBrowserMic(socket)

  // ── Frontend audio playback via Web Audio API ──
  const audioCtxRef = useRef(null)
  const audioNextTime = useRef(0)
  const audioReadyRef = useRef(false)

  function stopAudio() {
    audioNextTime.current = 0
    if (audioCtxRef.current && audioCtxRef.current.state !== 'closed') {
      audioCtxRef.current.close().catch(() => {})
      audioCtxRef.current = null
    }
  }

  function initAudioCtx() {
    if (!audioCtxRef.current) {
      const AC = window.AudioContext || window.webkitAudioContext
      if (!AC) return null
      audioCtxRef.current = new AC()
      console.log('[Audio] Created AudioContext')
    }
    if (audioCtxRef.current.state === 'suspended') {
      audioCtxRef.current.resume().catch(e => console.warn('[Audio] resume failed:', e))
    }
    return audioCtxRef.current
  }

  function playPcmBytes(bytes) {
    if (!bytes || !bytes.length) return
    const ctx = initAudioCtx()
    if (!ctx) {
      console.warn('[Audio] No AudioContext available')
      return
    }
    const len = Math.floor(bytes.length / 2)
    if (len === 0) return
    const float32 = new Float32Array(len)
    for (let i = 0; i < len; i++) {
      const val = bytes[i * 2] | (bytes[i * 2 + 1] << 8)
      float32[i] = (val << 16 >> 16) / 32768.0
    }
    try {
      const buffer = ctx.createBuffer(1, float32.length, 24000)
      buffer.copyToChannel(float32, 0)
      const source = ctx.createBufferSource()
      source.buffer = buffer
      source.connect(ctx.destination)
      let startTime = audioNextTime.current
      if (startTime < ctx.currentTime) {
        startTime = ctx.currentTime
      }
      source.start(startTime)
      audioNextTime.current = startTime + buffer.duration
    } catch (e) {
      console.warn('[Audio] Playback error:', e)
    }
  }

  const connectGuardRef = useRef(false)
  const requestLiveLocationRef = useRef(null)

  useEffect(() => {
    const onConnect = () => {
      setConnectionStatus('connected')
      if (connectGuardRef.current) return
      connectGuardRef.current = true
      requestLiveLocation()
      // Emit saved location from localStorage if available
      try {
        const saved = localStorage.getItem('soda-location')
        if (saved) {
          const loc = JSON.parse(saved)
          if (loc.lat && loc.lon) socket.emit('live_location', { lat: loc.lat, lon: loc.lon })
        }
      } catch {}
      socket.emit('start_audio')
      startBrowserMic()
      if (!audioReadyRef.current) {
        audioReadyRef.current = true
        setTimeout(() => {
          const ctx = initAudioCtx()
          if (ctx) {
            try {
              const t = ctx.currentTime
              const osc = ctx.createOscillator()
              const gain = ctx.createGain()
              osc.type = 'sine'
              osc.frequency.value = 660
              gain.gain.setValueAtTime(0.04, t)
              gain.gain.exponentialRampToValueAtTime(0.001, t + 0.08)
              osc.connect(gain).connect(ctx.destination)
              osc.start(t)
              osc.stop(t + 0.08)
            } catch (e) {}
          }
        }, 500)
      }
    }
    const onDisconnect = () => {
      setConnectionStatus('disconnected')
      connectGuardRef.current = false
    }
    const onConnectError = (err) => {
      console.warn('[SODA] Socket connection error:', err.message)
      setConnectionStatus('disconnected')
    }

    const onConfirm = (data) => {
      if (!data || !data.id) return
      pendingIdRef.current = data.id
      if (clearTimerRef.current) clearTimeout(clearTimerRef.current)
      if (clearTaskTimeoutRef.current) clearTimeout(clearTaskTimeoutRef.current)

      const toolName = data.tool || 'unknown'
      const isTerminal = toolName === 'terminal_execute'
      const needsPreview = !data.auto_allowed && (
        toolName === 'write_file' || toolName === 'send_whatsapp' || toolName === 'whatsapp_find_and_message' || toolName === 'send_discord'
      )

      setTask({
        id: data.id,
        tool: toolName,
        name: toolName,
        args: data.args || {},
        status: data.auto_allowed ? 'running' : 'pending',
        category: getCategory(toolName)
      })

      // Show terminal panel for terminal_execute
      if (isTerminal) {
        if (terminalTimerRef.current) clearTimeout(terminalTimerRef.current)
        setTerminal({
          visible: true,
          command: data.args?.command || '',
          output: '',
          success: null,
          attempts: [],
          total_attempts: 1,
        })
      }

      // Show tool panel with confirmation for serious operations
      if (needsPreview) {
        if (toolTimerRef.current) clearTimeout(toolTimerRef.current)
        setToolPanel({
          visible: true,
          toolName,
          status: 'pending',
          output: null,
          args: data.args || {}
        })
      }

    }

    const handleResolve = (event) => {
      const id = pendingIdRef.current
      if (!id) return
      const detail = event && event.detail
      const confirmed = detail && typeof detail.confirmed === 'boolean' ? detail.confirmed : true
      setTask((prev) => {
        if (!prev || prev.id !== id) return prev
        if (prev.status === 'done' || prev.status === 'error' || prev.status === 'cancelled') return prev
        if (!confirmed) {
          pendingIdRef.current = null
          // Close tool panel if it was showing confirmation
          setToolPanel(prev => ({ ...prev, visible: false }))
          return { ...prev, status: 'cancelled' }
        }
        // Switch tool panel to running
        setToolPanel(prev => ({ ...prev, status: 'running' }))
        return { ...prev, status: 'running' }
      })
    }

    const onCommandOutput = (data) => {
      markDone()
      setTaskData({
        ...data,
        phase: 'done',
        total_attempts: data.total_attempts || 1,
        attempt: data.total_attempts || 1,
      })

      setTerminal((prev) => ({
        ...prev,
        visible: true,
        command: data.command || prev.command,
        output: data.output || 'Command completed with no output.',
        success: data.success,
        attempts: data.attempts || [],
        total_attempts: data.total_attempts || 1,
      }))

      if (terminalTimerRef.current) clearTimeout(terminalTimerRef.current)
      const dismissMs = data.total_attempts > 1 ? 8000 : (data.success !== false ? 4000 : 10000)
      terminalTimerRef.current = setTimeout(() => {
        setTerminal((prev) => ({ ...prev, visible: false }))
      }, dismissMs)
    }



    const onSearchResults = (data) => {
      markDone()
      setTaskData(data)

      if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
      setSearch({
        visible: true,
        query: data.query || '',
        results: data.results || []
      })
    }

    const onScrapedData = (data) => {
      if (!data || !data.data) return
      setScrapedData({ visible: true, data: data.data, url: data.url || '' })
    }
    socket.on('scraped_data', onScrapedData)

    const onWebpageContent = (data) => {
      markDone()
      setTaskData(data)

      if (webpageTimerRef.current) clearTimeout(webpageTimerRef.current)
      setWebpageSummary({
        visible: true,
        url: data.url || '',
        content: data.content || '',
        success: data.success !== false,
        images: data.images || []
      })
    }

    const onFileList = (data) => {
      markDone()
      setTaskData(data)

      if (fileBrowserTimerRef.current) clearTimeout(fileBrowserTimerRef.current)
      setFileBrowser({
        visible: true,
        path: data.path || '',
        items: data.items || [],
        success: data.success !== false,
        searchQuery: data.searchQuery || ''
      })
      // No auto-dismiss — user needs time to pick a file
    }

    const onToolResult = (data) => {
      if (!data || !data.tool) return

      // Suppress popup for camera tools — Gemini handles these via speech
      if (data.tool === 'camera_control' || data.tool === 'open_camera') return

      const persistentAnims = new Set([
        'get_system_status', 'get_weather', 'get_news', 'get_bangladeshi_news', 'get_exchange_rate',
        'list_files', 'browse_webpage',
        'github_list_repos', 'github_get_repo', 'github_list_issues',
        'netlify_list_sites', 'vercel_list_projects',
        'list_processes', 'get_ip_info', 'define_word', 'get_wikipedia_summary',
        'show_memory', 'create_memory_schema', 'list_custom_schemas',
        'store_custom_memory', 'query_custom_memory',
      ])
      if (!persistentAnims.has(data.tool)) {
        markDone(data.tool === 'play_music')
      } else {
        setTask((prev) => {
          if (!prev || prev.status === 'done' || prev.status === 'error' || prev.status === 'cancelled') return prev
          return { ...prev, status: 'done' }
        })
        if (clearTaskTimeoutRef.current) clearTimeout(clearTaskTimeoutRef.current)
        clearTaskTimeoutRef.current = setTimeout(clearTask, 2000)
      }
      setTaskData(data.result || data)

      // Detect agent errors — update agentState + show persistent indicator
      const result = data.result || {}
      const resultStr = JSON.stringify(result).toLowerCase()
      if (resultStr.includes('local agent') || resultStr.includes('agent did not respond') || resultStr.includes('agent is not connected')) {
        setAgentState({ connected: false, error: true, machine_id: null, tools_count: 0, reason: 'timeout_or_not_connected' })
      }

      const toolName = data.tool

      // Pre-schedule native notification for set_reminder with future time
      if (toolName === 'set_reminder' && result) {
        let parsed = result
        if (typeof result.result === 'string') {
          try { parsed = JSON.parse(result.result) } catch (e) { parsed = result }
        }
        const reminder = parsed.reminder || parsed
        const nextFire = reminder.next_fire
        if (nextFire) {
          prescheduleNotification(
            parseInt(reminder.id || '0', 36) % 1000000 || Math.floor(Math.random() * 1000000),
            'SODA Reminder',
            reminder.message || 'Reminder triggered',
            new Date(nextFire * 1000).toISOString()
          )
        }
      }

      // Check for specialized panel first
      const specializedPanel = getSpecializedPanel(toolName)
      if (specializedPanel) {
        switch (specializedPanel) {
          case 'WeatherPanel':
            setWeatherPanel({ visible: true, data: result })
            return
          case 'SystemStatusPanel':
            setSystemStatusPanel({ visible: true, data: result })
            return
          case 'MemoryPanel':
            setMemoryPanel({ visible: true, data: result.result || result })
            return
          case 'CurrencyPanel':
            setCurrencyPanel({ visible: true, data: result })
            return
          case 'ProcessListPanel':
            setProcessPanel({ visible: true, data: result })
            return
          case 'NetworkInfoPanel':
            setNetworkPanel({ visible: true, data: result })
            return
          case 'GitHubPanel':
            setGitHubPanel({ visible: true, data: result })
            return
          case 'DeployPanel':
            setDeployPanel({ visible: true, data: result })
            return
          case 'PageSpeedPanel':
            setPageSpeedPanel({ visible: true, data: result })
            return
          case 'EmailPanel':
            setEmailPanel({ visible: true, data: result.result || result })
            return
          case 'NavigationPanel':
            if (result.success) setNavigation({ visible: true, data: result })
            return
        }
      }

      // Route to appropriate panel based on tool type
      if (TOOLS_WITH_INFO_PANEL.has(toolName)) {
        let infoType = 'info'
        if (toolName === 'get_weather') infoType = 'weather'
        else if (toolName === 'get_news') infoType = 'news'

        if (infoTimerRef.current) clearTimeout(infoTimerRef.current)
        setInfoPanel({ visible: true, type: infoType, data: result })
        infoTimerRef.current = setTimeout(() => {
          setInfoPanel(prev => ({ ...prev, visible: false }))
        }, 3000)
      } else if (TOOLS_WITH_OUTPUT.has(toolName)) {
        // File, clipboard, code output → bottom panel
        let fileType = 'file'
        if (toolName === 'clipboard_read' || toolName === 'clipboard_write') fileType = 'clipboard'
        else if (toolName === 'run_code') fileType = 'code'

        let content = ''
        if (toolName === 'write_file') content = result.result || 'File written.'
        else if (toolName === 'read_file') content = result.result?.length > 500 ? `${result.result.slice(0, 500)}...\n\n[truncated, ${result.result.length} chars total]` : (result.result || 'File read.')
        else if (toolName === 'read_directory') content = result.result || 'Directory listed.'
        else if (toolName === 'clipboard_read') content = result.text || '(empty)'
        else if (toolName === 'clipboard_write') content = result.success ? `Copied ${result.length} chars` : `Error: ${result.error}`
        else if (toolName === 'run_code') content = result.stdout || result.stderr || 'No output.'
        else if (toolName === 'screenshot') content = result.success ? `Saved to ${result.path}` : `Error: ${result.error}`
        else if (toolName === 'list_processes') {
          const procs = result.processes || []
          content = procs.map(p => `  ${p.name || '?'}  pid=${p.pid || '?'}  mem=${p.memory_kb || p.memory_percent || 0}`).join('\n')
          content = `Top ${result.count || 0} processes:\n${content}`
        }
        else if (toolName === 'get_active_window') content = result.title || '(unknown)'
        else if (toolName === 'create_project' || toolName === 'switch_project') content = result.result || 'Done.'
        else if (toolName === 'list_projects') content = result.result || 'No projects.'
        else content = JSON.stringify(result, null, 2)

        if (fileTimerRef.current) clearTimeout(fileTimerRef.current)
        setFileOutput({
          visible: true,
          type: fileType,
          title: toolName.replace(/_/g, ' ').toUpperCase(),
          content,
          success: result.success !== false
        })
      } else {
        // Unknown tool → generic tool panel at bottom
        if (toolTimerRef.current) clearTimeout(toolTimerRef.current)
        setToolPanel({
          visible: true,
          toolName,
          status: 'done',
          output: typeof result === 'string' ? result : JSON.stringify(result, null, 2),
          args: null
        })
        toolTimerRef.current = setTimeout(() => {
          setToolPanel((prev) => ({ ...prev, visible: false }))
        }, 3000)
      }
    }

    const onPanelOpen = (data) => {
      if (!data || !data.panelType) return
      const { panelType, data: panelData, direction } = data
      const state = { visible: true, data: panelData, direction: direction || 'right' }
      switch (panelType) {
        case 'IELTSDashboard':
          setIeltsDashboard(state)
          break
        case 'IELTSWriting':
          setIeltsWriting(state)
          break
        case 'IELTSSpeaking':
          setIeltsSpeaking(state)
          break
        case 'IELTSReading':
          setIeltsReading(state)
          break
        case 'IELTSVocab':
          setIeltsVocab(state)
          break
        case 'IELTSProgress':
          setIeltsProgress(state)
          break
      }
    }

    const onError = (data) => {
      markDone()

      // Show errors in the info panel (top)
      if (infoTimerRef.current) clearTimeout(infoTimerRef.current)
      setInfoPanel({ visible: true, type: 'error', data: { error: data?.msg || 'Unknown error' } })
    }

    const onClosePanel = (data) => {
      if (!data || !data.panel) return
      switch (data.panel) {
        case 'terminal':
          if (terminalTimerRef.current) clearTimeout(terminalTimerRef.current)
          setTerminal(prev => ({ ...prev, visible: false }))
          break
        case 'search':
          if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
          setSearch(prev => ({ ...prev, visible: false }))
          break
        case 'spotify_search':
          if (spotifySearchTimerRef.current) clearTimeout(spotifySearchTimerRef.current)
          setSpotifySearch(prev => ({ ...prev, visible: false }))
          break
        case 'task_terminal':
          setTaskTerminalVisible(false)
          break
        case 'scraped':
          setScrapedData(prev => ({ ...prev, visible: false }))
          break
        case 'file':
          if (fileTimerRef.current) clearTimeout(fileTimerRef.current)
          setFileOutput(prev => ({ ...prev, visible: false }))
          break
        case 'memory':
          setMemoryPanel(prev => ({ ...prev, visible: false }))
          break
        case 'info':
          if (infoTimerRef.current) clearTimeout(infoTimerRef.current)
          setInfoPanel(prev => ({ ...prev, visible: false }))
          break
        case 'navigation':
          setNavigation(prev => ({ ...prev, visible: false }))
          break
        case 'all':
          if (terminalTimerRef.current) clearTimeout(terminalTimerRef.current)
          setTerminal(prev => ({ ...prev, visible: false }))
          if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
          setSearch(prev => ({ ...prev, visible: false }))
          if (spotifySearchTimerRef.current) clearTimeout(spotifySearchTimerRef.current)
          setSpotifySearch(prev => ({ ...prev, visible: false }))
          if (fileTimerRef.current) clearTimeout(fileTimerRef.current)
          setFileOutput(prev => ({ ...prev, visible: false }))
          if (infoTimerRef.current) clearTimeout(infoTimerRef.current)
          setInfoPanel(prev => ({ ...prev, visible: false }))
          setToolPanel(prev => ({ ...prev, visible: false }))
          setWebpageSummary(prev => ({ ...prev, visible: false }))
          setFileBrowser(prev => ({ ...prev, visible: false }))

          setWeatherPanel(prev => ({ ...prev, visible: false }))
          setSystemStatusPanel(prev => ({ ...prev, visible: false }))
          setMemoryPanel(prev => ({ ...prev, visible: false }))
          setCurrencyPanel(prev => ({ ...prev, visible: false }))
          setProcessPanel(prev => ({ ...prev, visible: false }))
          setNetworkPanel(prev => ({ ...prev, visible: false }))
          setTaskTerminalVisible(false)
          setGitHubPanel(prev => ({ ...prev, visible: false }))
          setDeployPanel(prev => ({ ...prev, visible: false }))
          setPageSpeedPanel(prev => ({ ...prev, visible: false }))
          setEmailPanel(prev => ({ ...prev, visible: false }))
          setNavigation(prev => ({ ...prev, visible: false }))
          setIeltsDashboard(prev => ({ ...prev, visible: false }))
          setIeltsWriting(prev => ({ ...prev, visible: false }))
          setIeltsSpeaking(prev => ({ ...prev, visible: false }))
          setIeltsReading(prev => ({ ...prev, visible: false }))
          setIeltsVocab(prev => ({ ...prev, visible: false }))
          setIeltsProgress(prev => ({ ...prev, visible: false }))
          setFloatingWindows([])
          break
      }
    }

    const clearTask = () => {
      if (clearTaskTimeoutRef.current) clearTimeout(clearTaskTimeoutRef.current)
      setTask(null)
      setTaskData(null)
    }

    const markDone = (immediate = false) => {
      setTask((prev) => {
        if (!prev || prev.status === 'done' || prev.status === 'error' || prev.status === 'cancelled') return prev
        return { ...prev, status: 'done' }
      })
      if (clearTaskTimeoutRef.current) clearTimeout(clearTaskTimeoutRef.current)
      clearTaskTimeoutRef.current = setTimeout(() => {
        setTask(null)
        setTaskData(null)
      }, immediate ? 0 : 500)
    }

    window.addEventListener('soda:tool-resolved', handleResolve)
    socket.on('connect', onConnect)
    socket.on('disconnect', onDisconnect)
    socket.on('connect_error', onConnectError)
    socket.on('agent_connection_status', (data) => setAgentState(data))
    socket.on('tool_confirmation_request', onConfirm)
    socket.on('command_output', onCommandOutput)
    const onBackgroundCmdStatus = (data) => {
      if (!data) return
      // Update task and taskData so the retry animation shows proper phase
      setTask(prev => {
        if (!prev || (prev.status !== 'running' && prev.status !== 'pending')) return prev
        return { ...prev, status: 'running' }
      })
      setTaskData({
        command: data.command || '',
        output: data.output || '',
        attempt: data.attempt || 0,
        total_attempts: data.total || 1,
        phase: data.phase || 'running',
        success: data.success,
        error: data.error || '',
      })
      // Show terminal output for completed phases
      if (data.phase === 'done' || data.phase === 'failed') {
        setTerminal((prev) => ({
          ...prev,
          visible: true,
          command: data.command || prev.command,
          output: data.output || (data.success ? 'Command completed.' : 'Command failed.'),
          success: data.success
        }))
        if (terminalTimerRef.current) clearTimeout(terminalTimerRef.current)
        terminalTimerRef.current = setTimeout(() => {
          setTerminal((prev) => ({ ...prev, visible: false }))
        }, data.phase === 'failed' ? 10000 : 5000)
      }
    }
    socket.on('background_cmd_status', onBackgroundCmdStatus)
    const onAudioData = (data) => {
      if (data && data.data) playPcmBytes(data.data)
    }
    socket.on('audio_data', onAudioData)
    const onMicLevel = (data) => { if (data && typeof data.level === 'number') setOrbMicLevel(data.level) }
    socket.on('mic_level', onMicLevel)
    socket.on('search_results', onSearchResults)
    socket.on('spotify_search_results', (data) => {
      if (!data || !data.results) return
      if (spotifySearchTimerRef.current) clearTimeout(spotifySearchTimerRef.current)
      setSpotifySearch({ visible: true, query: data.query || '', results: data.results || [] })
    })
    socket.on('webpage_content', onWebpageContent)
    socket.on('file_list', onFileList)
    socket.on('tool_result', onToolResult)
    socket.on('now_playing', (data) => {
      setTaskData(data)
      setTimeout(() => setTaskData(null), 4000)
    })
    socket.on('panel_open', onPanelOpen)
    socket.on('error', onError)
    socket.on('close_panel', onClosePanel)
    const onTaskPlanUpdate = (data) => {
      if (data && data.tasks) {
        setTaskTerminalVisible(true)
      } else {
        setTaskTerminalVisible(false)
      }
    }
    socket.on('task_plan_update', onTaskPlanUpdate)
    const onPentestOutput = (data) => {
      if (data?.report) {
        setPentestResult(data)
        setPentestActive(false)
        setPentestProgress(null)
        setPentestVisible(true)
      }
    }
    socket.on('pentest_output', onPentestOutput)
    const onEmailData = (data) => {
      if (data) setEmailPanel({ visible: true, data })
    }
    socket.on('email_data', onEmailData)
    const onOpenUrl = (data) => {
      if (data && data.url) openUrlInFloatingWindow(data.url, data.webview_id)
    }
    socket.on('open_url', onOpenUrl)
    const onOpenSchedule = (data) => {
      if (data) openFloatingWindow('schedule_panel', 'SCHEDULE', { type: 'schedule', data }, 460, 60, 480, 520)
    }
    socket.on('open_schedule', onOpenSchedule)

    const onOpenNotepad = (data) => {
      if (!data || !data.id) return
      const id = data.id
      const tabs = (data.tabs || []).map((t, i) => ({ id: `tab_${i+1}`, title: t.title || 'notes', content: t.content || '', dirty: false }))
      openFloatingWindow(id, 'NOTEPAD', { type: 'notepad', id, tabs }, 100, 80, 520, 400)
    }
    socket.on('open_notepad', onOpenNotepad)

    const onOpenPastebox = () => {
      openFloatingWindow('pastebox', 'PASTE BOX', { type: 'pastebox' }, 300, 150, 520, 380)
    }
    socket.on('open_pastebox', onOpenPastebox)

    const onCameraOpen = () => {
      try { localStorage.removeItem('float_pos_camera') } catch {}
      const vw = window.innerWidth
      const camW = Math.min(320, vw - 16)
      const camX = Math.max(0, Math.floor((vw - camW) / 2))
      const camY = Math.max(0, Math.floor((window.innerHeight - 280) / 2))
      openFloatingWindow('camera_window', 'CAMERA', { type: 'camera' }, camX, camY, camW, 280)
    }
    socket.on('camera_open', onCameraOpen)

    const onViewFile = (data) => {
      if (!data || !data.payload) return
      const { payload } = data
      const fileName = payload.path.split('\\').pop().split('/').pop()
      const fwId = `file_view_${Date.now()}`
      openFloatingWindow(fwId, fileName, { type: 'file_viewer', mediaType: payload.type, content: payload.content, mime: payload.mime, path: payload.path }, 120, 80, 600, 480)
    }
    socket.on('view_file_content', onViewFile)

    const onPentestProgress = (data) => {
      if (data) setPentestProgress(data)
    }
    socket.on('pentest_scan_progress', onPentestProgress)

    const onTelegramMessage = (data) => {
      if (!data || !data.text) return
      setTaskData({ command: `📨 Telegram: ${data.text.slice(0, 60)}`, output: data.text, success: true })
    }
    socket.on('telegram_message', onTelegramMessage)

    const resolveWebviewId = (id) => {
      if (WebviewActionService.get(id)) return id
      const allIds = WebviewActionService.getAllIds()
      return allIds.length > 0 ? allIds[0] : id
    }

    const onWebviewAction = async (data) => {
      if (!data || !data.id || !data.action) return
      const { id, action, params } = data
      const wvId = resolveWebviewId(id)
      let result
      switch (action) {
        case 'click': result = await WebviewActionService.click(wvId, params?.selector); break
        case 'type': result = await WebviewActionService.type(wvId, params?.selector, params?.text); break
        case 'scroll': result = await WebviewActionService.scroll(wvId, params?.selector, params?.x, params?.y); break
        case 'scrollTo': result = await WebviewActionService.scrollTo(wvId, params?.selector); break
        case 'getContent': result = await WebviewActionService.getContent(wvId); break
        case 'getUrl': result = await WebviewActionService.getUrl(wvId); break
        case 'goBack': result = await WebviewActionService.goBack(wvId); break
        case 'goForward': result = await WebviewActionService.goForward(wvId); break
        case 'navigate': result = await WebviewActionService.navigate(wvId, params?.url); break
        case 'waitForLoad': result = await WebviewActionService.waitForLoad(wvId, params?.timeout); break
        case 'executeJS': result = await WebviewActionService.executeJS(wvId, params?.code); break
        default: result = { error: `unknown action: ${action}` }
      }
      socket.emit('webview_action_result', { id, action, result })
    }
    socket.on('webview_action', onWebviewAction)

    const onRequestBrowserUrl = async () => {
      let foundUrl = ''
      for (const fw of floatingWindows) {
        if (fw.content?.type === 'web' && fw.content?.id && fw.content?.url) {
          const result = await WebviewActionService.getUrl(fw.content.id)
          if (result?.success && result?.result?.url) {
            foundUrl = result.result.url
            break
          }
        }
      }
      if (!foundUrl) {
        for (const fw of floatingWindows) {
          if (fw.content?.type === 'web' && fw.content?.url) {
            foundUrl = fw.content.url
            break
          }
        }
      }
      socket.emit('browser_url_response', { url: foundUrl })
    }
    socket.on('request_browser_url', onRequestBrowserUrl)

    socket.on('window_minimize', () => {
      if (window.electron?.minimize) window.electron.minimize()
    })

    socket.on('window_restore', () => {
      if (window.electron?.restore) window.electron.restore()
    })

    const onShutdown = () => {
      if (window.electron?.close) window.electron.close()
      else if (window.close) window.close()
    }
    const onPersonality = (data) => {
      if (data && data.text) {
        setPersonalityText(data.text)
        setPersonalityMood(data.mood || 'neutral')
        if (personalityTimerRef.current) clearTimeout(personalityTimerRef.current)
        personalityTimerRef.current = setTimeout(() => {
          setPersonalityText(null)
        }, 5000)
      }
    }
    const onIdleMode = (data) => {
      setIdleMode(data.active)
      if (data.active && window.electron?.enterBackground) {
        setBackgroundMode(true)
        window.electron.enterBackground()
      } else if (!data.active && window.electron?.exitBackground) {
        setBackgroundMode(false)
        window.electron.exitBackground()
      }
    }
    socket.on('idle_mode', onIdleMode)
    const onBackgroundMode = (data) => {
      setBackgroundMode(data.active)
      if (data.active && window.electron?.enterBackground) {
        window.electron.enterBackground()
      } else if (!data.active && window.electron?.exitBackground) {
        window.electron.exitBackground()
      }
    }
    socket.on('background_mode', onBackgroundMode)
    const requestLiveLocation = () => {
      if (!navigator.geolocation) return
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          console.log('[SODA] Location:', pos.coords.latitude, pos.coords.longitude, '±' + Math.round(pos.coords.accuracy) + 'm')
          socket.emit('live_location', { lat: pos.coords.latitude, lon: pos.coords.longitude })
        },
        (err) => console.warn('[SODA] Geolocation error:', err.code === 1 ? 'Permission denied' : err.message),
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 5000 }
      )
    }
    requestLiveLocationRef.current = requestLiveLocation

    const onSpeakingState = (data) => {
      if (data && data.state) {
        setSpeakingState(data.state)
        if (data.state === 'user') requestLiveLocation()
      }
    }
    socket.on('speaking_state', onSpeakingState)
    socket.on('personality', onPersonality)
    socket.on('shutdown', onShutdown)
    socket.on('stop_audio', stopAudio)
    const onRemoteCount = (data) => { if (data && typeof data.count === 'number') setRemoteCount(data.count) }
    socket.on('soda_remote_count', onRemoteCount)

    socket.on('reminder_fired', (data) => {
      if (data && data.message) {
        showNotification('SODA Reminder', data.message, data.id ? parseInt(data.id, 36) || undefined : undefined)
      }
    })

    setTimeout(requestNotifPermission, 2000)

    socket.connect()

    // Handle already-connected edge case (e.g., StrictMode double-mount in dev)
    if (socket.connected) {
      onConnect()
    }

    return () => {
      window.removeEventListener('soda:tool-resolved', handleResolve)
      socket.off('connect', onConnect)
      socket.off('disconnect', onDisconnect)
      socket.off('connect_error', onConnectError)
      socket.off('agent_connection_status')
      socket.off('tool_confirmation_request', onConfirm)
      socket.off('command_output', onCommandOutput)
      socket.off('background_cmd_status')
      socket.off('audio_data', onAudioData)
      socket.off('mic_level', onMicLevel)
      socket.off('search_results', onSearchResults)
      socket.off('spotify_search_results')
      socket.off('webpage_content', onWebpageContent)
      socket.off('file_list', onFileList)
      socket.off('scraped_data', onScrapedData)
      socket.off('tool_result', onToolResult)
      socket.off('now_playing')
      socket.off('panel_open', onPanelOpen)
      socket.off('error', onError)
      socket.off('close_panel', onClosePanel)
      socket.off('task_plan_update', onTaskPlanUpdate)
      socket.off('open_url', onOpenUrl)
      socket.off('open_schedule', onOpenSchedule)
      socket.off('open_notepad', onOpenNotepad)
      socket.off('camera_open', onCameraOpen)
      socket.off('view_file_content', onViewFile)
      socket.off('telegram_message', onTelegramMessage)
      socket.off('webview_action', onWebviewAction)
      socket.off('window_minimize')
      socket.off('window_restore')
      socket.off('idle_mode', onIdleMode)
      socket.off('background_mode', onBackgroundMode)
      socket.off('speaking_state', onSpeakingState)
      socket.off('personality', onPersonality)
      socket.off('shutdown', onShutdown)
      socket.off('stop_audio', stopAudio)
      socket.off('soda_remote_count', onRemoteCount)
      socket.off('reminder_fired')
      socket.off('pentest_scan_progress', onPentestProgress)
      socket.off('pentest_output', onPentestOutput)
      socket.off('email_data', onEmailData)
      if (clearTaskTimeoutRef.current) clearTimeout(clearTaskTimeoutRef.current)
    }
  }, [])

  // Keep center animation visible until next command — no auto-dismiss

  const closeTerminal = () => {
    if (terminalTimerRef.current) clearTimeout(terminalTimerRef.current)
    setTerminal((prev) => ({ ...prev, visible: false }))
  }

  const closeSearch = () => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    setSearch((prev) => ({ ...prev, visible: false }))
  }

  const closeSpotifySearch = () => {
    if (spotifySearchTimerRef.current) clearTimeout(spotifySearchTimerRef.current)
    setSpotifySearch((prev) => ({ ...prev, visible: false }))
  }

  const closeFileOutput = () => {
    if (fileTimerRef.current) clearTimeout(fileTimerRef.current)
    setFileOutput((prev) => ({ ...prev, visible: false }))
  }

  const closeInfoPanel = () => {
    if (infoTimerRef.current) clearTimeout(infoTimerRef.current)
    setInfoPanel((prev) => ({ ...prev, visible: false }))
  }

  const closeToolPanel = () => {
    if (toolTimerRef.current) clearTimeout(toolTimerRef.current)
    setToolPanel((prev) => ({ ...prev, visible: false }))
  }

  const closeWebpageSummary = () => {
    if (webpageTimerRef.current) clearTimeout(webpageTimerRef.current)
    setWebpageSummary((prev) => ({ ...prev, visible: false }))
  }

  const closeFileBrowser = () => {
    if (fileBrowserTimerRef.current) clearTimeout(fileBrowserTimerRef.current)
    setFileBrowser((prev) => ({ ...prev, visible: false }))
  }

  const closeScrapedData = () => {
    setScrapedData({ visible: false, data: null, url: '' })
  }

  const handleScrapedExport = (fmt) => {
    closeScrapedData()
    if (typeof socket !== 'undefined' && socket.emit) {
      socket.emit('force_tool', {
        tool: 'export_data',
        args: { format: fmt, title: 'scraped_data' }
      })
    }
  }

  // ── Floating Windows (draggable, anywhere on screen) ──
  const [floatingWindows, setFloatingWindows] = useState([])
  const nextZRef = useRef(100)
  const floatOffsetRef = useRef(0)

  const findFreeFloatPosition = useCallback((w, h) => {
    const leftZone = { x: 0, y: 0, w: 440, h: 10000 }
    const rightZone = { x: window.innerWidth - 420, y: 0, w: 420, h: 10000 }

    const tries = [
      { x: Math.max(460, window.innerWidth - w - 440), y: 60 },
      { x: 460, y: 60 },
      { x: Math.max(460, window.innerWidth - w - 440), y: window.innerHeight - h - 40 },
      { x: 460, y: window.innerHeight - h - 160 },
      { x: 300, y: 120 },
      { x: 500, y: 200 },
    ]

    const existing = floatingWindows.map(fw => ({ x: fw.x, y: fw.y, w: fw.w, h: fw.h }))

    for (const pos of tries) {
      const overlapsAny = existing.some(e =>
        pos.x < e.x + e.w && pos.x + w > e.x &&
        pos.y < e.y + e.h && pos.y + h > e.y
      )
      const inLeftZone = pos.x < leftZone.x + leftZone.w
      const inRightZone = pos.x + w > rightZone.x
      if (!overlapsAny && !inLeftZone && !inRightZone) {
        return { x: pos.x, y: pos.y }
      }
    }

    const offset = floatOffsetRef.current
    floatOffsetRef.current += 40
    return { x: 460 + offset, y: 100 + offset }
  }, [floatingWindows])

  const getFloatPosition = useCallback((key) => {
    try {
      const saved = localStorage.getItem('float_pos_' + key)
      if (saved) return JSON.parse(saved)
    } catch {}
    return null
  }, [])

  const saveFloatPosition = useCallback((key, x, y) => {
    try {
      localStorage.setItem('float_pos_' + key, JSON.stringify({ x, y }))
    } catch {}
  }, [])

  const positionKeyFromContent = (content) => {
    return content?.positionKey || content?.type || 'window'
  }

  const openFloatingWindow = useCallback((id, title, content, preferredX, preferredY, w, h) => {
    const z = nextZRef.current++
    const pKey = positionKeyFromContent(content)
    const saved = getFloatPosition(pKey)
    let x, y
    if (saved) {
      x = saved.x
      y = saved.y
    } else if (preferredX !== undefined && preferredY !== undefined) {
      const vw = window.innerWidth
      x = Math.max(0, Math.min(preferredX, vw - (w || 320) - 8))
      y = Math.max(0, preferredY)
    } else {
      const pos = findFreeFloatPosition(w || 480, h || 360)
      x = pos.x
      y = pos.y
    }
    setFloatingWindows(prev => {
      const existing = prev.find(fw => fw.id === id)
      if (existing) {
        return prev.map(fw => fw.id === id ? { ...fw, zIndex: z, title, content } : fw)
      }
      return [...prev, { id, title, content, x, y, w, h, zIndex: z, positionKey: pKey }]
    })
  }, [findFreeFloatPosition, getFloatPosition])

  const closeFloatingWindow = useCallback((id) => {
    setFloatingWindows(prev => prev.filter(fw => fw.id !== id))
  }, [])

  const focusFloatingWindow = useCallback((id) => {
    const z = nextZRef.current++
    setFloatingWindows(prev => prev.map(fw => fw.id === id ? { ...fw, zIndex: z } : fw))
  }, [])

  const openUrlInFloatingWindow = useCallback((url, webviewId) => {
    if (!url) return
    const id = webviewId || `web_${Date.now()}`
    const shortUrl = url.replace(/^https?:\/\//, '').slice(0, 50)
    openFloatingWindow(id, shortUrl, { type: 'web', url, id }, 80, 60, 680, 520)
  }, [openFloatingWindow])

  const confirmTool = () => {
    if (pendingIdRef.current) {
      socket.emit('confirm_tool', { id: pendingIdRef.current, confirmed: true })
      setToolPanel(prev => ({ ...prev, status: 'running' }))
    }
  }

  const denyTool = () => {
    if (pendingIdRef.current) {
      socket.emit('confirm_tool', { id: pendingIdRef.current, confirmed: false })
      pendingIdRef.current = null
      setToolPanel(prev => ({ ...prev, visible: false }))
    }
  }

  const isIdle = !task
  const orbPulse = task && (task.status === 'pending' || task.status === 'running')

  return (
    <RootErrorBoundary>
    <>
    <AnimationErrorBoundary fallback={
      <div style={{ backgroundColor: '#04080B', height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ color: '#00fbfb', fontFamily: 'monospace', fontSize: 14 }}>SODA</span>
      </div>
    }>
    <PanelSpaceProvider>
    <div
      className="relative h-screen w-screen font-sans overflow-hidden flex items-center justify-center"
      style={{
        backgroundColor: '#04080B',
        minHeight: '100vh',
        opacity: backgroundMode ? 0 : 1,
        pointerEvents: backgroundMode ? 'none' : 'auto',
        transition: 'opacity 0.25s ease',
      }}
      onClick={() => { initAudioCtx(); resumeMicAudio(); requestLiveLocationRef.current?.() }}
    >
      {/* ── Remote Connection Indicator (top-right) ── */}
      {remoteCount > 0 && (
        <div className="absolute top-3 right-3 flex items-center gap-1.5 z-50" style={{ pointerEvents: 'none' }}>
          <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: '#00ff88', boxShadow: '0 0 6px #00ff88' }} />
          <span className="text-[9px] font-mono tracking-widest" style={{ color: 'rgba(0,255,136,0.7)' }}>
            REMOTE {remoteCount}
          </span>
        </div>
      )}
      {/* Terminal Panel — slides from LEFT */}
      <TerminalPanel
        visible={terminal.visible}
        command={terminal.command}
        output={terminal.output}
        success={terminal.success}
        attempts={terminal.attempts}
        total_attempts={terminal.total_attempts}
        onClose={closeTerminal}
      />

      {/* Search Results Panel — slides from RIGHT */}
      <SearchResultsPanel
        visible={search.visible}
        query={search.query}
        results={search.results}
        onClose={closeSearch}
        onOpenUrl={openUrlInFloatingWindow}
      />

      {/* Spotify Search Results Panel — slides from RIGHT */}
      <SpotifySearchPanel
        visible={spotifySearch.visible}
        query={spotifySearch.query}
        results={spotifySearch.results}
        onClose={closeSpotifySearch}
      />

      {/* File/Clipboard/Code Output Panel — slides from BOTTOM */}
      <FileOutputPanel
        visible={fileOutput.visible}
        type={fileOutput.type}
        title={fileOutput.title}
        content={fileOutput.content}
        success={fileOutput.success}
        onClose={closeFileOutput}
      />

      {/* Info Panel (weather/news/errors) — slides from TOP */}
      <InfoPanel
        visible={infoPanel.visible}
        type={infoPanel.type}
        data={infoPanel.data}
        onClose={closeInfoPanel}
      />

      {/* Tool Output / Confirmation Panel — slides from BOTTOM */}
      <ToolOutputPanel
        visible={toolPanel.visible}
        toolName={toolPanel.toolName}
        status={toolPanel.status}
        output={toolPanel.output}
        args={toolPanel.args}
        onConfirm={toolPanel.status === 'pending' ? confirmTool : undefined}
        onDeny={toolPanel.status === 'pending' ? denyTool : undefined}
        onClose={closeToolPanel}
      />

      {/* Webpage Summary Panel — slides from BOTTOM */}
      <WebpageSummaryPanel
        visible={webpageSummary.visible}
        url={webpageSummary.url}
        content={webpageSummary.content}
        success={webpageSummary.success}
        images={webpageSummary.images}
        onClose={closeWebpageSummary}
      />

      {/* Scraped Data Panel — slides from BOTTOM */}
      <ScrapedDataPanel
        visible={scrapedData.visible}
        data={scrapedData.data}
        url={scrapedData.url}
        onClose={closeScrapedData}
        onExport={handleScrapedExport}
      />

      {/* File Browser Panel — slides from BOTTOM */}
      <FileBrowserPanel
        visible={fileBrowser.visible}
        path={fileBrowser.path}
        items={fileBrowser.items}
        success={fileBrowser.success}
        searchQuery={fileBrowser.searchQuery}
        onClose={closeFileBrowser}
      />

      {/* Specialized Data Panels */}
      <WeatherPanel visible={weatherPanel.visible} data={weatherPanel.data}
        onClose={() => setWeatherPanel(prev => ({ ...prev, visible: false }))} />
      <SystemStatusPanel visible={systemStatusPanel.visible} data={systemStatusPanel.data}
        onClose={() => setSystemStatusPanel(prev => ({ ...prev, visible: false }))} />
      <MemoryPanel visible={memoryPanel.visible} data={memoryPanel.data}
        onClose={() => setMemoryPanel(prev => ({ ...prev, visible: false }))} />
      <CurrencyPanel visible={currencyPanel.visible} data={currencyPanel.data}
        onClose={() => setCurrencyPanel(prev => ({ ...prev, visible: false }))} />
      <ProcessListPanel visible={processPanel.visible} data={processPanel.data}
        onClose={() => setProcessPanel(prev => ({ ...prev, visible: false }))} />
      <NetworkInfoPanel visible={networkPanel.visible} data={networkPanel.data}
        onClose={() => setNetworkPanel(prev => ({ ...prev, visible: false }))} />
      <GitHubPanel visible={gitHubPanel.visible} data={gitHubPanel.data}
        onClose={() => setGitHubPanel(prev => ({ ...prev, visible: false }))} />
      <DeployPanel visible={deployPanel.visible} data={deployPanel.data}
        onClose={() => setDeployPanel(prev => ({ ...prev, visible: false }))} />
      <PageSpeedPanel visible={pageSpeedPanel.visible} data={pageSpeedPanel.data}
        onClose={() => setPageSpeedPanel(prev => ({ ...prev, visible: false }))} />
      <EmailPanel visible={emailPanel.visible} data={emailPanel.data}
        onClose={() => setEmailPanel(prev => ({ ...prev, visible: false }))} />

      {/* ── Navigation Panel (full-screen 3D map) ── */}
      {navigation.visible && navigation.data && (
        <NavigationPanel
          data={navigation.data}
          socket={socket}
          onClose={() => setNavigation(prev => ({ ...prev, visible: false }))}
        />
      )}



      {/* ── IELTS Panels ── */}
      <SlidePanel visible={ieltsDashboard.visible} direction={ieltsDashboard.direction}
        title="IELTS DASHBOARD" accentColor="#00fbfb"
        onClose={() => setIeltsDashboard(prev => ({ ...prev, visible: false }))}>
        <IELTSDashboardPanel data={ieltsDashboard.data} />
      </SlidePanel>
      <SlidePanel visible={ieltsWriting.visible} direction={ieltsWriting.direction}
        title="IELTS WRITING" accentColor="#00fbfb"
        onClose={() => setIeltsWriting(prev => ({ ...prev, visible: false }))}>
        <IELTSWritingPanel data={ieltsWriting.data} />
      </SlidePanel>
      <SlidePanel visible={ieltsSpeaking.visible} direction={ieltsSpeaking.direction}
        title="IELTS SPEAKING" accentColor="#00fbfb"
        onClose={() => setIeltsSpeaking(prev => ({ ...prev, visible: false }))}>
        <IELTSSpeakingPanel data={ieltsSpeaking.data} />
      </SlidePanel>
      <SlidePanel visible={ieltsReading.visible} direction={ieltsReading.direction}
        title="IELTS READING" accentColor="#00fbfb"
        onClose={() => setIeltsReading(prev => ({ ...prev, visible: false }))}>
        <IELTSReadingPanel data={ieltsReading.data} />
      </SlidePanel>
      <SlidePanel visible={ieltsVocab.visible} direction={ieltsVocab.direction}
        title="IELTS VOCABULARY" accentColor="#00fbfb"
        onClose={() => setIeltsVocab(prev => ({ ...prev, visible: false }))}>
        <IELTSVocabPanel data={ieltsVocab.data} />
      </SlidePanel>
      <SlidePanel visible={ieltsProgress.visible} direction={ieltsProgress.direction}
        title="IELTS STUDY PLAN" accentColor="#00fbfb"
        onClose={() => setIeltsProgress(prev => ({ ...prev, visible: false }))}>
        <IELTSProgressPanel data={ieltsProgress.data} />
      </SlidePanel>

      {/* ── Task Terminal Panel (centered bottom) ── */}
      <TaskTerminalPanel visible={taskTerminalVisible} onClose={() => setTaskTerminalVisible(false)} />

      {/* ── Pentest Progress Indicator (top-left) ── */}
      {pentestActive && <PentestProgressIndicator progress={pentestProgress} onDismiss={() => { setPentestActive(false); setPentestProgress(null) }} />}

      {/* ── Pentest Results Panel ── */}
      <PentestResultsPanel visible={pentestVisible} result={pentestResult} onClose={() => { setPentestVisible(false); setPentestResult(null) }} />

      {/* ── Floating Windows (draggable, anywhere on screen) ── */}
      {floatingWindows.map(fw => (
        <FloatingWindow
          key={fw.id}
          id={fw.id}
          title={fw.title}
          initialX={fw.x}
          initialY={fw.y}
          width={fw.w}
          height={fw.h}
          zIndex={fw.zIndex}
          onClose={closeFloatingWindow}
          onFocus={focusFloatingWindow}
          onPositionChange={(id, x, y) => saveFloatPosition(fw.positionKey || fw.content?.type || 'window', x, y)}
        >
          <FloatingContent content={fw.content} />
        </FloatingWindow>
      ))}

      <div className="flex flex-col items-center gap-6">
        {task && AI_CARD_TOOLS.has(task.tool) ? (
          /* ── AI Studio Full Card replaces orb + panel ── */
          <div className="flex flex-col items-center gap-4" style={{ width: 380 }}>
            <AnimationStage category={task.category} status={task.status} toolName={task.tool} data={taskData} />
            <span
              className="text-xs font-semibold tracking-wider uppercase"
              style={{ color: STATUS_COLORS[task.status] || 'var(--text-primary)' }}
            >
              {task.tool}
            </span>
            <span
              className="text-[10px] font-medium tracking-wider uppercase"
              style={{ color: STATUS_COLORS[task.status] || 'var(--text-dim)' }}
            >
              {STATUS_LABELS[task.status] || task.status}
            </span>
          </div>
        ) : (
          /* ── Holographic Orb + SVG Animation overlay ── */
          <>
            {(() => {
              const orbSize = 192
              return (
            <div className={'relative flex items-center justify-center w-48 h-48'}>
              <div
                className="absolute inset-0 flex items-center justify-center"
                style={{
                  opacity: task ? 0.25 : 1,
                  transition: 'opacity 0.6s ease',
                }}
              >
                <HolographicOrb size={orbSize} micLevel={orbMicLevel} mood={personalityMood} idle={idleMode} />
              </div>
              {idleMode && (
                <div className="idle-label">SODA is in Idle Mode</div>
              )}
              {personalityText && (
                <div className="thought-bubble thought-bubble-enter" key={personalityText}>
                  {personalityText}
                </div>
              )}
              {task && (
                <div className="absolute inset-0 flex items-center justify-center" style={{ opacity: 1 }}>
                  <div style={{ width: orbSize, height: orbSize }}>
                    <AnimationStage
                      category={task.category}
                      status={task.status}
                      toolName={task.tool}
                      data={taskData}
                    />
                  </div>
                </div>
              )}
            </div>
            )})()}
            {task && (
              <div className="flex flex-col items-center gap-1">
                <span
                  className="text-xs font-semibold tracking-wider uppercase"
                  style={{ color: STATUS_COLORS[task.status] || 'var(--text-primary)' }}
                >
                  {task.tool.replace(/_/g, ' ')}
                </span>
                <span
                  className="text-[10px] font-medium tracking-wider uppercase"
                  style={{ color: STATUS_COLORS[task.status] || 'var(--text-dim)' }}
                >
                  {STATUS_LABELS[task.status] || task.status}
                </span>
              </div>
            )}
          </>
        )}

        {isIdle && !(task && AI_CARD_TOOLS.has(task.tool)) && (
          <div className="flex flex-col items-center gap-1">
            <span
              className="text-[10px] font-medium tracking-wider uppercase"
              style={{ color: 'var(--text-dim)' }}
            >
              {idleMode ? 'idle' : (connectionStatus === 'connected' ? 'ready' : 'connecting...')}
            </span>
            {agentState !== null && (
              <span
                className="text-[9px] font-medium tracking-wider"
                style={{ color: agentState.connected ? 'rgba(0,255,136,0.6)' : 'rgba(255,51,85,0.6)' }}
              >
                AGENT {agentState.connected ? 'ONLINE' : 'OFFLINE'}
              </span>
            )}
            {agentState?.error && !agentState.connected && (
              <div className="mt-2 px-2 py-1 border text-[9px] leading-relaxed cursor-pointer"
                style={{ borderColor: 'rgba(255,51,85,0.3)', backgroundColor: 'rgba(255,51,85,0.08)', color: '#ff4466' }}
                onClick={() => setAgentState(prev => ({ ...prev, error: false }))}>
                Local agent offline. Desktop commands require{' '}
                <code className="font-bold" style={{ color: '#ff6688' }}>py -3.11 backend\local_agent.py</code>
                <span className="block mt-0.5 opacity-60">Click to dismiss</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
    </PanelSpaceProvider>
    </AnimationErrorBoundary>
    {task && VISION_TOOLS.has(task.tool) && <CameraCapture />}
    </>
    </RootErrorBoundary>
  )
}
