import { useState, useEffect, useRef, useCallback, Suspense, Component } from 'react'
import socket from './services/SocketService'
import { getCategory, CATEGORIES, getAnimationForTool, getVariantForTool, getSpecializedPanel } from './components/animations'
import useAudioPlayback from './hooks/useAudioPlayback'
import usePanelState from './hooks/usePanelState'
import useFloatingWindows from './hooks/useFloatingWindows'
import useSocketHandlers from './hooks/useSocketHandlers'
import useBrowserMic, { resumeMicAudio } from './services/useBrowserMic'
import WebviewActionService from './services/WebviewActionService'

import SearchResultsPanel from './components/panels/SearchResultsPanel'
import FileOutputPanel from './components/panels/FileOutputPanel'
import InfoPanel from './components/panels/InfoPanel'
import ToolOutputPanel from './components/panels/ToolOutputPanel'
import ParallelToolPanel from './components/panels/ParallelToolPanel'
import WebpageSummaryPanel from './components/panels/WebpageSummaryPanel'
import FileBrowserPanel from './components/panels/FileBrowserPanel'
import ToolShowcasePanel from './components/panels/ToolShowcasePanel'
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
import ResearchResultsPanel from './components/panels/ResearchResultsPanel'
import BackgroundTaskPanel from './components/panels/BackgroundTaskPanel'
import EmailPanel from './components/panels/EmailPanel'
import ProjectStatsPanel from './components/panels/ProjectStatsPanel'
import MemoryPanel from './components/panels/MemoryPanel'
import IELTSDashboardPanel from './components/panels/IELTSDashboardPanel'
import IELTSWritingPanel from './components/panels/IELTSWritingPanel'
import IELTSSpeakingPanel from './components/panels/IELTSSpeakingPanel'
import IELTSReadingPanel from './components/panels/IELTSReadingPanel'
import IELTSVocabPanel from './components/panels/IELTSVocabPanel'
import IELTSProgressPanel from './components/panels/IELTSProgressPanel'
import WikipediaPanel from './components/panels/WikipediaPanel'
import NewsPanel from './components/panels/NewsPanel'
import CodePanel from './components/panels/CodePanel'
import DataPanel from './components/panels/DataPanel'
import TranslatePanel from './components/panels/TranslatePanel'
import SummarizePanel from './components/panels/SummarizePanel'
import MonitorPanel from './components/panels/MonitorPanel'
import SocialPanel from './components/panels/SocialPanel'
import ResearchPanel from './components/panels/ResearchPanel'
import AgentsPanel from './components/panels/AgentsPanel'
import { PanelSpaceProvider } from './contexts/PanelSpaceContext'
import SlidePanel from './components/SlidePanel'
import CameraCapture from './components/CameraCapture'
import HolographicOrb from './components/HolographicOrb'
import WakeSequence from './components/WakeSequence'
import NightWinddown from './components/NightWinddown'
import DailyBriefingPanel from './components/panels/DailyBriefingPanel'
import Notepad from './components/Notepad'
import BackgroundWidget from './components/BackgroundWidget'
import FullscreenCamera from './components/FullscreenCamera'
import WorldMonitorPanel from './components/panels/WorldMonitorPanel'
import ScheduleWindow from './components/ScheduleWindow'

// ── Frontend Error Logging ──
if (typeof socket !== 'undefined') {
  window.onerror = (msg, url, line, col, err) => {
    socket.emit('client_log', {
      level: 'error', message: msg,
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

const STATUS_LABELS = {
  pending: 'awaiting', running: 'running', done: 'complete',
  error: 'failed', cancelled: 'cancelled'
}

const STATUS_COLORS = {
  pending: 'var(--accent)', running: 'var(--accent)',
  done: 'var(--success)', error: 'var(--error)', cancelled: 'var(--text-dim)'
}

const AI_CARD_TOOLS = new Set([
  'get_system_status', 'get_weather', 'terminal_execute', 'reminder',
])

const VISION_TOOLS = new Set([
  'screenshot', 'analyze_screen', 'read_screen_text', 'take_photo', 'recognize_face', 'remember_face',
])

// ── Error Boundaries ──
class AnimationErrorBoundary extends Component {
  constructor(props) { super(props); this.state = { hasError: false } }
  static getDerivedStateFromError() { return { hasError: true } }
  componentDidCatch(error) { console.warn('[SODA] Animation error caught:', error?.message) }
  render() { return this.state.hasError ? (this.props.fallback || null) : this.props.children }
}

class RootErrorBoundary extends Component {
  constructor(props) { super(props); this.state = { hasError: false, error: null } }
  static getDerivedStateFromError(error) { return { hasError: true, error } }
  componentDidCatch(error) { console.error('[SODA] Root error:', error) }
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

// ── AnimationStage ──
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

// ── TerminalPanel ──
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
    if (scrollRef.current) scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [output])

  return (
    <div className="terminal-panel" style={{
      left: pos.x, top: pos.y,
      transform: visible ? 'translateX(0)' : 'translateX(-110%)',
      opacity: visible ? 1 : 0,
    }}>
      <div className="terminal-header" onMouseDown={handleMouseDown}>
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
        {output ? (
          <pre className="terminal-output" style={{ color: success === false ? '#ffb4ab' : '#c8c8c8' }}>{output}</pre>
        ) : (
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

// ── FloatingContent ──
function FloatingContent({ content }) {
  const webviewRef = useRef(null)

  useEffect(() => {
    if (content?.type !== 'web' || !content?.id) return
    const wv = webviewRef.current
    if (wv) WebviewActionService.register(content.id, wv)
    const onReady = () => {
      const el = webviewRef.current
      if (el) WebviewActionService.register(content.id, el)
    }
    wv?.addEventListener('dom-ready', onReady)
    wv?.addEventListener('did-finish-load', onReady)
    return () => {
      wv?.removeEventListener('dom-ready', onReady)
      wv?.removeEventListener('did-finish-load', onReady)
      WebviewActionService.unregister(content.id)
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
            {(!content.results || content.results.length === 0) && <div className="sp-empty">no results</div>}
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
            {(!content.items || content.items.length === 0) && <div className="sp-empty">empty directory</div>}
          </div>
        </>
      )
    case 'output':
      return <pre className="sp-output-pre" style={{ color: content.success === false ? '#ffb4ab' : '#c8c8c8' }}>{content.content || 'No output.'}</pre>
    case 'text':
      return <pre className="sp-output-pre" style={{ color: '#c8c8c8' }}>{content.text || 'No data.'}</pre>
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
          <div style={{ color: '#ffb4ab', fontSize: 14, marginBottom: 8 }}>WARNING: ERROR</div>
          <div style={{ color: 'rgba(255,180,171,0.7)', fontSize: 12 }}>{content.msg}</div>
        </div>
      )
    case 'schedule':
      return <ScheduleWindow data={content.data} />
    default:
      return <pre className="sp-output-pre" style={{ color: '#c8c8c8' }}>{JSON.stringify(content, null, 2)}</pre>
  }
}

// ── Widget Mode ──
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
    const onSpeakingState = (data) => { if (data && data.state) setSpeakingState(data.state) }
    const onBackgroundMode = (data) => {
      if (data && data.active === false && window.electron?.exitBackground) window.electron.exitBackground()
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

  if (!ready) return null
  return <BackgroundWidget speakingState={speakingState} onRestore={() => {}} widgetMode={true} />
}

// ── Main App ──
const isWidgetMode = typeof window !== 'undefined' && new URLSearchParams(window.location.search).has('widget')

export default function App() {
  if (isWidgetMode) return <WidgetApp />

  const [connectionStatus, setConnectionStatus] = useState('disconnected')
  const [agentState, setAgentState] = useState(null)
  const [task, setTask] = useState(null)
  const [taskData, setTaskData] = useState(null)
  const pendingIdRef = useRef(null)
  const clearTaskTimeoutRef = useRef(null)

  // Tool showcase panel state (right)
  const [toolShowcase, setToolShowcase] = useState({ visible: false, tools: [] })
  const showcaseTimerRef = useRef(null)

  const panels = usePanelState()
  const audio = useAudioPlayback()
  const floating = useFloatingWindows()
  const { micActive: browserMicActive, micError: browserMicError, start: startBrowserMic, stop: stopBrowserMic } = useBrowserMic(socket)

  const handleScrapedExport = useCallback((fmt) => {
    panels.closeScrapedData()
    if (typeof socket !== 'undefined' && socket.emit) {
      socket.emit('force_tool', { tool: 'export_data', args: { format: fmt, title: 'scraped_data' } })
    }
  }, [panels.closeScrapedData])

  const confirmTool = useCallback(() => {
    if (pendingIdRef.current) {
      socket.emit('confirm_tool', { id: pendingIdRef.current, confirmed: true })
      panels.setToolPanel(prev => ({ ...prev, status: 'running' }))
    }
  }, [panels.setToolPanel])

  const denyTool = useCallback(() => {
    if (pendingIdRef.current) {
      socket.emit('confirm_tool', { id: pendingIdRef.current, confirmed: false })
      pendingIdRef.current = null
      panels.setToolPanel(prev => ({ ...prev, visible: false }))
    }
  }, [panels.setToolPanel])

  useSocketHandlers({
    setConnectionStatus, setAgentState, setTask, setTaskData,
    setToolShowcase, showcaseTimerRef,
    pendingIdRef, clearTaskTimeoutRef,
    terminalTimerRef: panels.terminalTimerRef, setTerminal: panels.setTerminal,
    searchTimerRef: panels.searchTimerRef, setSearch: panels.setSearch,
    fileTimerRef: panels.fileTimerRef, setFileOutput: panels.setFileOutput,
    infoTimerRef: panels.infoTimerRef, setInfoPanel: panels.setInfoPanel,
    toolTimerRef: panels.toolTimerRef, setToolPanel: panels.setToolPanel,
    setToolQueue: panels.setToolQueue,
    setParallelPanelOpen: panels.setParallelPanelOpen,
    setWikipediaPanel: panels.setWikipediaPanel, setNewsPanel: panels.setNewsPanel,
    setCodePanel: panels.setCodePanel, setDataPanel: panels.setDataPanel,
    setTranslatePanel: panels.setTranslatePanel, setSummarizePanel: panels.setSummarizePanel,
    setMonitorPanel: panels.setMonitorPanel, setSocialPanel: panels.setSocialPanel,
    setResearchPanel: panels.setResearchPanel, setAgentsPanel: panels.setAgentsPanel,
    webpageTimerRef: panels.webpageTimerRef, setWebpageSummary: panels.setWebpageSummary,
    fileBrowserTimerRef: panels.fileBrowserTimerRef, setFileBrowser: panels.setFileBrowser,
    setScrapedData: panels.setScrapedData,
    setWeatherPanel: panels.setWeatherPanel, setSystemStatusPanel: panels.setSystemStatusPanel,
    setMemoryPanel: panels.setMemoryPanel, setCurrencyPanel: panels.setCurrencyPanel,
    setProcessPanel: panels.setProcessPanel, setNetworkPanel: panels.setNetworkPanel,
    setTaskTerminalVisible: panels.setTaskTerminalVisible,
    setPentestVisible: panels.setPentestVisible, setPentestActive: panels.setPentestActive,
    setPentestProgress: panels.setPentestProgress, setPentestResult: panels.setPentestResult,
    setGitHubPanel: panels.setGitHubPanel, setDeployPanel: panels.setDeployPanel,
    setPageSpeedPanel: panels.setPageSpeedPanel,
    setResearchResultsPanel: panels.setResearchResultsPanel,
    setBackgroundTaskPanel: panels.setBackgroundTaskPanel,
    setEmailPanel: panels.setEmailPanel, setProjectStatsPanel: panels.setProjectStatsPanel,
    setIeltsDashboard: panels.setIeltsDashboard, setIeltsWriting: panels.setIeltsWriting,
    setIeltsSpeaking: panels.setIeltsSpeaking, setIeltsReading: panels.setIeltsReading,
    setIeltsVocab: panels.setIeltsVocab, setIeltsProgress: panels.setIeltsProgress,
    setOrbMicLevel: panels.setOrbMicLevel, setRemoteCount: panels.setRemoteCount,
    setPersonalityText: panels.setPersonalityText, setPersonalityMood: panels.setPersonalityMood,
    personalityTimerRef: panels.personalityTimerRef,
    setIdleMode: panels.setIdleMode, setBackgroundMode: panels.setBackgroundMode,
    setSpeakingState: panels.setSpeakingState, setWaking: panels.setWaking,
    setDailyBrief: panels.setDailyBrief, setNightWinddown: panels.setNightWinddown,
    openFloatingWindow: floating.openFloatingWindow,
    openUrlInFloatingWindow: floating.openUrlInFloatingWindow,
    floatingWindows: floating.floatingWindows,
    setFloatingWindows: floating.setFloatingWindows,
    setWorldMonitorOpen: panels.setWorldMonitorOpen,
    setCameraFullscreen: panels.setCameraFullscreen,
    playPcmBytes: audio.playPcmBytes, stopAudio: audio.stopAudio,
    initAudioCtx: audio.initAudioCtx, playConnectionBeep: audio.playConnectionBeep,
    startBrowserMic,
  })

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
        backgroundColor: '#04080B', minHeight: '100vh',
        opacity: panels.backgroundMode ? 0 : 1,
        pointerEvents: panels.backgroundMode ? 'none' : 'auto',
        transition: 'opacity 0.25s ease',
      }}
      onClick={() => { audio.initAudioCtx(); resumeMicAudio() }}
    >
      {panels.remoteCount > 0 && (
        <div className="absolute top-3 right-3 flex items-center gap-1.5 z-50" style={{ pointerEvents: 'none' }}>
          <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: '#00ff88', boxShadow: '0 0 6px #00ff88' }} />
          <span className="text-[9px] font-mono tracking-widest" style={{ color: 'rgba(0,255,136,0.7)' }}>
            REMOTE {panels.remoteCount}
          </span>
        </div>
      )}

      <TerminalPanel visible={panels.terminal.visible} command={panels.terminal.command}
        output={panels.terminal.output} success={panels.terminal.success}
        attempts={panels.terminal.attempts} total_attempts={panels.terminal.total_attempts}
        onClose={panels.closeTerminal} />

      <SearchResultsPanel visible={panels.search.visible} query={panels.search.query}
        results={panels.search.results} onClose={panels.closeSearch}
        onOpenUrl={floating.openUrlInFloatingWindow} />

      <DailyBriefingPanel visible={panels.dailyBrief.visible} data={panels.dailyBrief.data}
        onClose={() => panels.setDailyBrief(prev => ({ ...prev, visible: false }))} />

      <NightWinddown active={panels.nightWinddown} onComplete={() => panels.setNightWinddown(false)} />

      <FileOutputPanel visible={panels.fileOutput.visible} type={panels.fileOutput.type}
        title={panels.fileOutput.title} content={panels.fileOutput.content}
        success={panels.fileOutput.success} onClose={panels.closeFileOutput} />

      <InfoPanel visible={panels.infoPanel.visible} type={panels.infoPanel.type}
        data={panels.infoPanel.data} onClose={panels.closeInfoPanel} />

      <WikipediaPanel visible={panels.wikipediaPanel.visible} data={panels.wikipediaPanel.data}
        onClose={() => panels.setWikipediaPanel(prev => ({ ...prev, visible: false }))} />
      <NewsPanel visible={panels.newsPanel.visible} data={panels.newsPanel.data}
        onClose={() => panels.setNewsPanel(prev => ({ ...prev, visible: false }))} />
      <CodePanel visible={panels.codePanel.visible} data={panels.codePanel.data}
        onClose={() => panels.setCodePanel(prev => ({ ...prev, visible: false }))} />
      <DataPanel visible={panels.dataPanel.visible} data={panels.dataPanel.data}
        onClose={() => panels.setDataPanel(prev => ({ ...prev, visible: false }))} />
      <TranslatePanel visible={panels.translatePanel.visible} data={panels.translatePanel.data}
        onClose={() => panels.setTranslatePanel(prev => ({ ...prev, visible: false }))} />
      <SummarizePanel visible={panels.summarizePanel.visible} data={panels.summarizePanel.data}
        onClose={() => panels.setSummarizePanel(prev => ({ ...prev, visible: false }))} />
      <MonitorPanel visible={panels.monitorPanel.visible} data={panels.monitorPanel.data}
        onClose={() => panels.setMonitorPanel(prev => ({ ...prev, visible: false }))} />
      <SocialPanel visible={panels.socialPanel.visible} data={panels.socialPanel.data}
        onClose={() => panels.setSocialPanel(prev => ({ ...prev, visible: false }))} />
      <ResearchPanel visible={panels.researchPanel.visible} data={panels.researchPanel.data}
        onClose={() => panels.setResearchPanel(prev => ({ ...prev, visible: false }))} />
      <AgentsPanel visible={panels.agentsPanel.visible} data={panels.agentsPanel.data}
        onClose={() => panels.setAgentsPanel(prev => ({ ...prev, visible: false }))} />

      <ToolOutputPanel visible={panels.toolPanel.visible} toolName={panels.toolPanel.toolName}
        status={panels.toolPanel.status} output={panels.toolPanel.output} args={panels.toolPanel.args}
        onConfirm={panels.toolPanel.status === 'pending' ? confirmTool : undefined}
        onDeny={panels.toolPanel.status === 'pending' ? denyTool : undefined}
        onClose={panels.closeToolPanel} />

      <ParallelToolPanel visible={panels.parallelPanelOpen && panels.toolQueue.length > 0}
        tools={panels.toolQueue}
        onClose={() => { panels.setParallelPanelOpen(false); setTimeout(() => panels.setToolQueue([]), 400) }} />

      <WebpageSummaryPanel visible={panels.webpageSummary.visible} url={panels.webpageSummary.url}
        content={panels.webpageSummary.content} success={panels.webpageSummary.success}
        images={panels.webpageSummary.images} onClose={panels.closeWebpageSummary} />

      <ScrapedDataPanel visible={panels.scrapedData.visible} data={panels.scrapedData.data}
        url={panels.scrapedData.url} onClose={panels.closeScrapedData} onExport={handleScrapedExport} />

      <FileBrowserPanel visible={panels.fileBrowser.visible} path={panels.fileBrowser.path}
        items={panels.fileBrowser.items} success={panels.fileBrowser.success}
        searchQuery={panels.fileBrowser.searchQuery} onClose={panels.closeFileBrowser} />

      {/* Tool Showcase Panel — slides from RIGHT */}
      <ToolShowcasePanel
        visible={toolShowcase.visible}
        tools={toolShowcase.tools}
        onClose={() => setToolShowcase(prev => ({ ...prev, visible: false }))}
      />

      <WeatherPanel visible={panels.weatherPanel.visible} data={panels.weatherPanel.data}
        onClose={() => panels.setWeatherPanel(prev => ({ ...prev, visible: false }))} />
      <SystemStatusPanel visible={panels.systemStatusPanel.visible} data={panels.systemStatusPanel.data}
        onClose={() => panels.setSystemStatusPanel(prev => ({ ...prev, visible: false }))} />
      <MemoryPanel visible={panels.memoryPanel.visible} data={panels.memoryPanel.data}
        onClose={() => panels.setMemoryPanel(prev => ({ ...prev, visible: false }))} />
      <CurrencyPanel visible={panels.currencyPanel.visible} data={panels.currencyPanel.data}
        onClose={() => panels.setCurrencyPanel(prev => ({ ...prev, visible: false }))} />
      <ProcessListPanel visible={panels.processPanel.visible} data={panels.processPanel.data}
        onClose={() => panels.setProcessPanel(prev => ({ ...prev, visible: false }))} />
      <NetworkInfoPanel visible={panels.networkPanel.visible} data={panels.networkPanel.data}
        onClose={() => panels.setNetworkPanel(prev => ({ ...prev, visible: false }))} />
      <GitHubPanel visible={panels.gitHubPanel.visible} data={panels.gitHubPanel.data}
        onClose={() => panels.setGitHubPanel(prev => ({ ...prev, visible: false }))} />
      <DeployPanel visible={panels.deployPanel.visible} data={panels.deployPanel.data}
        onClose={() => panels.setDeployPanel(prev => ({ ...prev, visible: false }))} />
      <PageSpeedPanel visible={panels.pageSpeedPanel.visible} data={panels.pageSpeedPanel.data}
        onClose={() => panels.setPageSpeedPanel(prev => ({ ...prev, visible: false }))} />
      <ResearchResultsPanel visible={panels.researchResultsPanel.visible} data={panels.researchResultsPanel.data}
        onClose={() => panels.setResearchResultsPanel(prev => ({ ...prev, visible: false }))} />
      <BackgroundTaskPanel visible={panels.backgroundTaskPanel.visible} data={panels.backgroundTaskPanel.data}
        onClose={() => panels.setBackgroundTaskPanel(prev => ({ ...prev, visible: false }))} />
      <EmailPanel visible={panels.emailPanel.visible} data={panels.emailPanel.data}
        onClose={() => panels.setEmailPanel(prev => ({ ...prev, visible: false }))} />
      <ProjectStatsPanel visible={panels.projectStatsPanel.visible} data={panels.projectStatsPanel.data}
        onClose={() => panels.setProjectStatsPanel(prev => ({ ...prev, visible: false }))} />

      {/* IELTS Panels */}
      <SlidePanel visible={panels.ieltsDashboard.visible} direction={panels.ieltsDashboard.direction}
        title="IELTS DASHBOARD" accentColor="#00fbfb"
        onClose={() => panels.setIeltsDashboard(prev => ({ ...prev, visible: false }))}>
        <IELTSDashboardPanel data={panels.ieltsDashboard.data} />
      </SlidePanel>
      <SlidePanel visible={panels.ieltsWriting.visible} direction={panels.ieltsWriting.direction}
        title="IELTS WRITING" accentColor="#00fbfb"
        onClose={() => panels.setIeltsWriting(prev => ({ ...prev, visible: false }))}>
        <IELTSWritingPanel data={panels.ieltsWriting.data} />
      </SlidePanel>
      <SlidePanel visible={panels.ieltsSpeaking.visible} direction={panels.ieltsSpeaking.direction}
        title="IELTS SPEAKING" accentColor="#00fbfb"
        onClose={() => panels.setIeltsSpeaking(prev => ({ ...prev, visible: false }))}>
        <IELTSSpeakingPanel data={panels.ieltsSpeaking.data} />
      </SlidePanel>
      <SlidePanel visible={panels.ieltsReading.visible} direction={panels.ieltsReading.direction}
        title="IELTS READING" accentColor="#00fbfb"
        onClose={() => panels.setIeltsReading(prev => ({ ...prev, visible: false }))}>
        <IELTSReadingPanel data={panels.ieltsReading.data} />
      </SlidePanel>
      <SlidePanel visible={panels.ieltsVocab.visible} direction={panels.ieltsVocab.direction}
        title="IELTS VOCABULARY" accentColor="#00fbfb"
        onClose={() => panels.setIeltsVocab(prev => ({ ...prev, visible: false }))}>
        <IELTSVocabPanel data={panels.ieltsVocab.data} />
      </SlidePanel>
      <SlidePanel visible={panels.ieltsProgress.visible} direction={panels.ieltsProgress.direction}
        title="IELTS STUDY PLAN" accentColor="#00fbfb"
        onClose={() => panels.setIeltsProgress(prev => ({ ...prev, visible: false }))}>
        <IELTSProgressPanel data={panels.ieltsProgress.data} />
      </SlidePanel>

      <TaskTerminalPanel visible={panels.taskTerminalVisible} onClose={() => panels.setTaskTerminalVisible(false)} />

      {panels.pentestActive && <PentestProgressIndicator progress={panels.pentestProgress} onDismiss={() => { panels.setPentestActive(false); panels.setPentestProgress(null) }} />}
      <PentestResultsPanel visible={panels.pentestVisible} result={panels.pentestResult} onClose={() => { panels.setPentestVisible(false); panels.setPentestResult(null) }} />

      {floating.floatingWindows.map(fw => (
        <FloatingWindow key={fw.id} id={fw.id} title={fw.title}
          initialX={fw.x} initialY={fw.y} width={fw.w} height={fw.h} zIndex={fw.zIndex}
          onClose={floating.closeFloatingWindow} onFocus={floating.focusFloatingWindow}
          onPositionChange={(id, x, y) => floating.saveFloatPosition(fw.positionKey || fw.content?.type || 'window', x, y)}>
          <FloatingContent content={fw.content} />
        </FloatingWindow>
      ))}

      <div className="flex flex-col items-center gap-6">
        {task && AI_CARD_TOOLS.has(task.tool) ? (
          <div className="flex flex-col items-center gap-4" style={{ width: 380 }}>
            <AnimationStage category={task.category} status={task.status} toolName={task.tool} data={taskData} />
            <span className="text-xs font-semibold tracking-wider uppercase"
              style={{ color: STATUS_COLORS[task.status] || 'var(--text-primary)' }}>
              {task.tool}
            </span>
            <span className="text-[10px] font-medium tracking-wider uppercase"
              style={{ color: STATUS_COLORS[task.status] || 'var(--text-dim)' }}>
              {STATUS_LABELS[task.status] || task.status}
            </span>
          </div>
        ) : (
          <>
            {(() => {
              const isShowcase = task && task.tool === 'show_tools'
              const orbSize = isShowcase ? 320 : 192
              return (
                <div className={`relative flex items-center justify-center ${isShowcase ? 'w-80 h-80' : 'w-48 h-48'}`}>
                  <div className="absolute inset-0 flex items-center justify-center"
                    style={{ opacity: task ? 0.25 : 1, transition: 'opacity 0.6s ease' }}>
                    <HolographicOrb size={orbSize} micLevel={panels.orbMicLevel} mood={panels.personalityMood} idle={panels.idleMode} waking={panels.waking} />
                  </div>
                  {panels.toolQueue.length > 0 && !task && (
                    <div className="orb-tool-badge" onClick={() => panels.setParallelPanelOpen(true)} title={`${panels.toolQueue.length} tools running`}>
                      {panels.toolQueue.filter(t => t.status === 'running').length || panels.toolQueue.length}
                    </div>
                  )}
                  {panels.idleMode && <div className="idle-label">SODA is in Idle Mode</div>}
                  {panels.personalityText && (
                    <div className="thought-bubble thought-bubble-enter" key={panels.personalityText}>
                      {panels.personalityText}
                    </div>
                  )}
                  {task && (
                    <div className="absolute inset-0 flex items-center justify-center" style={{ opacity: 1 }}>
                      <div style={{ width: orbSize, height: orbSize }}>
                        <AnimationStage category={task.category} status={task.status} toolName={task.tool} data={taskData} />
                      </div>
                    </div>
                  )}
                </div>
              )
            })()}
            {task && (
              <div className="flex flex-col items-center gap-1">
                <span className="text-xs font-semibold tracking-wider uppercase"
                  style={{ color: STATUS_COLORS[task.status] || 'var(--text-primary)' }}>
                  {task.tool.replace(/_/g, ' ')}
                </span>
                <span className="text-[10px] font-medium tracking-wider uppercase"
                  style={{ color: STATUS_COLORS[task.status] || 'var(--text-dim)' }}>
                  {STATUS_LABELS[task.status] || task.status}
                </span>
              </div>
            )}
          </>
        )}

        {isIdle && !(task && AI_CARD_TOOLS.has(task.tool)) && (
          <div className="flex flex-col items-center gap-1">
            <span className="text-[10px] font-medium tracking-wider uppercase" style={{ color: 'var(--text-dim)' }}>
              {panels.idleMode ? 'idle' : (connectionStatus === 'connected' ? 'ready' : 'connecting...')}
            </span>
            {agentState !== null && (
              <span className="text-[9px] font-medium tracking-wider"
                style={{ color: agentState.connected ? 'rgba(0,255,136,0.6)' : 'rgba(255,51,85,0.6)' }}>
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
    {(task && VISION_TOOLS.has(task.tool)) || panels.cameraFullscreen ? <CameraCapture /> : null}
    {panels.cameraFullscreen && (
      <FullscreenCamera socket={socket} onClose={() => panels.setCameraFullscreen(false)} />
    )}
    <WorldMonitorPanel open={panels.worldMonitorOpen} onClose={() => panels.setWorldMonitorOpen(false)} />
    <WakeSequence active={panels.waking} onComplete={() => panels.setWaking(false)} />
    </>
    </RootErrorBoundary>
  )
}
