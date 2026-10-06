import { useEffect, useRef, useCallback } from 'react'
import socket from '../services/SocketService'
import { getCategory, getSpecializedPanel, ALL_TOOL_NAMES } from '../components/animations'
import WebviewActionService from '../services/WebviewActionService'

const TOOLS_WITH_OUTPUT = new Set([
  'write_file', 'read_file', 'read_directory',
  'screenshot',
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
  'reminder',
  'create_memory_schema', 'list_custom_schemas',
  'store_custom_memory', 'query_custom_memory',
])

const TOOLS_WITH_AGENT = new Set([
  'show_agents',
  'agent_wikipedia', 'agent_news', 'agent_code', 'agent_data',
  'agent_translate', 'agent_summarize', 'agent_monitor',
  'agent_social', 'agent_research', 'agent_browse',
  'agent_security', 'agent_database', 'agent_devops',
])

export default function useSocketHandlers(cfg) {
  const {
    setConnectionStatus, setAgentState, setTask, setTaskData,
    pendingIdRef, clearTaskTimeoutRef,
    terminalTimerRef, setTerminal, searchTimerRef, setSearch,
    fileTimerRef, setFileOutput, infoTimerRef, setInfoPanel,
    toolTimerRef, setToolPanel, setToolQueue, setParallelPanelOpen,
    setWikipediaPanel, setNewsPanel, setCodePanel, setDataPanel,
    setTranslatePanel, setSummarizePanel, setMonitorPanel,
    setSocialPanel, setResearchPanel, setAgentsPanel,
    webpageTimerRef, setWebpageSummary, fileBrowserTimerRef, setFileBrowser,
    setScrapedData,
    setWeatherPanel, setSystemStatusPanel, setMemoryPanel,
    setCurrencyPanel, setProcessPanel, setNetworkPanel,
    setTaskTerminalVisible, setPentestVisible, setPentestActive,
    setPentestProgress, setPentestResult,
    setGitHubPanel, setDeployPanel, setPageSpeedPanel,
    setResearchResultsPanel, setBackgroundTaskPanel, setEmailPanel,
    setProjectStatsPanel,
    setIeltsDashboard, setIeltsWriting, setIeltsSpeaking,
    setIeltsReading, setIeltsVocab, setIeltsProgress,
    setOrbMicLevel, setRemoteCount,
    setPersonalityText, setPersonalityMood, personalityTimerRef,
    setIdleMode, setBackgroundMode, setSpeakingState, setWaking,
    setDailyBrief, setNightWinddown,
    openFloatingWindow, openUrlInFloatingWindow, floatingWindows,
    setFloatingWindows,
    setToolShowcase, showcaseTimerRef,
    setWorldMonitorOpen, setCameraFullscreen,
    playPcmBytes, stopAudio, initAudioCtx, playConnectionBeep,
    startBrowserMic,
  } = cfg

  const clearTimerRef = useRef(false)

  const clearTask = useCallback(() => {
    if (clearTaskTimeoutRef.current) clearTimeout(clearTaskTimeoutRef.current)
    setTask(null)
    setTaskData(null)
  }, [setTask, setTaskData, clearTaskTimeoutRef])

  const markDone = useCallback((immediate = false) => {
    setTask((prev) => {
      if (!prev || prev.status === 'done' || prev.status === 'error' || prev.status === 'cancelled') return prev
      return { ...prev, status: 'done' }
    })
    if (clearTaskTimeoutRef.current) clearTimeout(clearTaskTimeoutRef.current)
    clearTaskTimeoutRef.current = setTimeout(() => {
      setTask(null)
      setTaskData(null)
    }, immediate ? 0 : 500)
  }, [setTask, setTaskData, clearTaskTimeoutRef])

  const connectGuardRef = useRef(false)
  const floatingWindowsRef = useRef(floatingWindows)
  floatingWindowsRef.current = floatingWindows

  useEffect(() => {
    const onConnect = () => {
      setConnectionStatus('connected')
      if (connectGuardRef.current) return
      connectGuardRef.current = true
      socket.emit('start_audio')
      startBrowserMic()
      playConnectionBeep()
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

      // Start showcase immediately — panel + animation, no need to wait for backend tool_showcase event
      if (toolName === 'show_tools' && data.auto_allowed) {
        if (showcaseTimerRef.current) clearTimeout(showcaseTimerRef.current)
        const tools = ALL_TOOL_NAMES.map(name => ({ name, description: '' }))
        setToolShowcase({ visible: true, tools })
        setTaskData({ tools })
        const ms = Math.min(tools.length * 120 + 600, 12000)
        showcaseTimerRef.current = setTimeout(() => {
          setTask(prev => {
            if (!prev || prev.name !== 'show_tools') return prev
            return { ...prev, status: 'done' }
          })
        }, ms)
      }

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
          setToolPanel(prev => ({ ...prev, visible: false }))
          return { ...prev, status: 'cancelled' }
        }
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
      setSearch({ visible: true, query: data.query || '', results: data.results || [] })
    }

    const onToolShowcase = (data) => {
      const tools = data.tools || []
      if (data.status === 'done') {
        setToolShowcase({ visible: true, tools, status: 'done' })
        if (showcaseTimerRef.current) clearTimeout(showcaseTimerRef.current)
        return
      }
      setToolShowcase({ visible: true, tools })
      if (tools.length) {
        setTask({
          status: 'running',
          tool: 'show_tools',
          name: 'show_tools',
          category: 'data',
          timestamp: Date.now(),
        })
        setTaskData(data)
        if (showcaseTimerRef.current) clearTimeout(showcaseTimerRef.current)
        const ms = Math.min(tools.length * 120 + 600, 12000)
        showcaseTimerRef.current = setTimeout(() => {
          setTask(prev => {
            if (!prev || prev.name !== 'show_tools') return prev
            return { ...prev, status: 'done' }
          })
        }, ms)
      }
    }

    const onScrapedData = (data) => {
      if (!data || !data.data) return
      setScrapedData({ visible: true, data: data.data, url: data.url || '' })
    }

    const onWebpageContent = (data) => {
      markDone()
      setTaskData(data)
      if (webpageTimerRef.current) clearTimeout(webpageTimerRef.current)
      setWebpageSummary({
        visible: true, url: data.url || '', content: data.content || '',
        success: data.success !== false, images: data.images || []
      })
    }

    const onFileList = (data) => {
      markDone()
      setTaskData(data)
      if (fileBrowserTimerRef.current) clearTimeout(fileBrowserTimerRef.current)
      setFileBrowser({
        visible: true, path: data.path || '', items: data.items || [],
        success: data.success !== false, searchQuery: data.searchQuery || ''
      })
    }

    const onToolResult = (data) => {
      if (!data || !data.tool) return
      if (data.tool === 'camera_control' || data.tool === 'open_camera') return

      const persistentAnims = new Set([
        'get_system_status', 'get_weather', 'get_news', 'get_bangladeshi_news', 'get_exchange_rate',
        'list_files', 'show_tools', 'browse_webpage',
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

      const result = data.result || {}
      const resultStr = JSON.stringify(result).toLowerCase()
      if (resultStr.includes('local agent') || resultStr.includes('agent did not respond') || resultStr.includes('agent is not connected')) {
        setAgentState({ connected: false, error: true, machine_id: null, tools_count: 0, reason: 'timeout_or_not_connected' })
      }

      const toolName = data.tool

      if (toolName === 'reminder' && result) {
        let parsed = result
        if (typeof result.result === 'string') {
          try { parsed = JSON.parse(result.result) } catch (e) { parsed = result }
        }
        const reminder = parsed.reminder || parsed
        const nextFire = reminder.next_fire
        if (nextFire) {
          const ln = (() => { try { return window.Capacitor?.Plugins?.LocalNotifications } catch { return null } })()
          if (ln) {
            ln.schedule({
              notifications: [{
                id: parseInt(reminder.id || '0', 36) % 1000000 || Math.floor(Math.random() * 1000000),
                title: 'SODA Reminder',
                body: reminder.message || 'Reminder triggered',
                schedule: { at: new Date(nextFire * 1000) },
                smallIcon: 'ic_stat_soda', iconColor: '#0a0a0f', channelId: 'soda-reminders',
              }]
            }).catch(() => {})
          }
        }
      }

      const specializedPanel = getSpecializedPanel(toolName)
      if (specializedPanel) {
        switch (specializedPanel) {
          case 'WeatherPanel': setWeatherPanel({ visible: true, data: result }); return
          case 'SystemStatusPanel': setSystemStatusPanel({ visible: true, data: result }); return
          case 'MemoryPanel': setMemoryPanel({ visible: true, data: result.result || result }); return
          case 'CurrencyPanel': setCurrencyPanel({ visible: true, data: result }); return
          case 'ProcessListPanel': setProcessPanel({ visible: true, data: result }); return
          case 'NetworkInfoPanel': setNetworkPanel({ visible: true, data: result }); return
          case 'GitHubPanel': setGitHubPanel({ visible: true, data: result }); return
          case 'DeployPanel': setDeployPanel({ visible: true, data: result }); return
          case 'PageSpeedPanel': setPageSpeedPanel({ visible: true, data: result }); return
          case 'ResearchResultsPanel': setResearchResultsPanel({ visible: true, data: result }); return
          case 'BackgroundTaskPanel': setBackgroundTaskPanel({ visible: true, data: result }); return
          case 'EmailPanel': setEmailPanel({ visible: true, data: result.result || result }); return
          case 'ProjectStatsPanel': setProjectStatsPanel({ visible: true, data: result }); return
        }
      }

      if (TOOLS_WITH_AGENT.has(toolName)) {
        if (toolTimerRef.current) clearTimeout(toolTimerRef.current)
        const agentData = data.result || result
        const setters = {
          show_agents: setAgentsPanel, agent_wikipedia: setWikipediaPanel,
          agent_news: setNewsPanel, agent_code: setCodePanel,
          agent_data: setDataPanel, agent_translate: setTranslatePanel,
          agent_summarize: setSummarizePanel, agent_monitor: setMonitorPanel,
          agent_social: setSocialPanel, agent_research: setResearchPanel,
          agent_browse: setWikipediaPanel, agent_security: setCodePanel,
          agent_database: setDataPanel, agent_devops: setMonitorPanel,
        }
        const setter = setters[toolName]
        if (setter) setter({ visible: true, data: agentData })
        return
      }

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
        let fileType = 'file'
        if (toolName === 'run_code') fileType = 'code'
        let content = ''
        if (toolName === 'write_file') content = result.result || 'File written.'
        else if (toolName === 'read_file') content = result.result?.length > 500 ? `${result.result.slice(0, 500)}...\n\n[truncated, ${result.result.length} chars total]` : (result.result || 'File read.')
        else if (toolName === 'read_directory') content = result.result || 'Directory listed.'
        else if (toolName === 'run_code') content = result.stdout || result.stderr || 'No output.'
        else if (toolName === 'screenshot') content = result.success ? `Saved to ${result.path}` : `Error: ${result.error}`
        else if (toolName === 'list_processes') {
          const procs = result.processes || []
          content = procs.map(p => `  ${p.name || '?'}  pid=${p.pid || '?'}  mem=${p.memory_kb || p.memory_percent || 0}`).join('\n')
          content = `Top ${result.count || 0} processes:\n${content}`
        }
        else if (toolName === 'get_active_window') content = result.title || '(unknown)'
        else if (toolName === 'create_project' || toolName === 'switch_project') content = result.result || 'Done.'
        else if (toolName === 'project_registry') content = result.result || 'No projects.'
        else content = JSON.stringify(result, null, 2)

        if (fileTimerRef.current) clearTimeout(fileTimerRef.current)
        setFileOutput({
          visible: true, type: fileType,
          title: toolName.replace(/_/g, ' ').toUpperCase(),
          content, success: result.success !== false
        })
      } else {
        if (toolTimerRef.current) clearTimeout(toolTimerRef.current)
        setToolPanel({
          visible: true, toolName, status: 'done',
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
        case 'IELTSDashboard': setIeltsDashboard(state); break
        case 'IELTSWriting': setIeltsWriting(state); break
        case 'IELTSSpeaking': setIeltsSpeaking(state); break
        case 'IELTSReading': setIeltsReading(state); break
        case 'IELTSVocab': setIeltsVocab(state); break
        case 'IELTSProgress': setIeltsProgress(state); break
      }
    }

    const onError = (data) => {
      markDone()
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
        case 'task_terminal': setTaskTerminalVisible(false); break
        case 'scraped': setScrapedData(prev => ({ ...prev, visible: false })); break
        case 'file':
          if (fileTimerRef.current) clearTimeout(fileTimerRef.current)
          setFileOutput(prev => ({ ...prev, visible: false }))
          break
        case 'memory': setMemoryPanel(prev => ({ ...prev, visible: false })); break
        case 'info':
          if (infoTimerRef.current) clearTimeout(infoTimerRef.current)
          setInfoPanel(prev => ({ ...prev, visible: false }))
          break
        case 'world_monitor': setWorldMonitorOpen(false); break
        case 'all':
          if (terminalTimerRef.current) clearTimeout(terminalTimerRef.current)
          setTerminal(prev => ({ ...prev, visible: false }))
          if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
          setSearch(prev => ({ ...prev, visible: false }))
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
          setProjectStatsPanel(prev => ({ ...prev, visible: false }))
          setIeltsDashboard(prev => ({ ...prev, visible: false }))
          setIeltsWriting(prev => ({ ...prev, visible: false }))
          setIeltsSpeaking(prev => ({ ...prev, visible: false }))
          setIeltsReading(prev => ({ ...prev, visible: false }))
          setIeltsVocab(prev => ({ ...prev, visible: false }))
          setIeltsProgress(prev => ({ ...prev, visible: false }))
          setWikipediaPanel(prev => ({ ...prev, visible: false }))
          setNewsPanel(prev => ({ ...prev, visible: false }))
          setCodePanel(prev => ({ ...prev, visible: false }))
          setDataPanel(prev => ({ ...prev, visible: false }))
          setTranslatePanel(prev => ({ ...prev, visible: false }))
          setSummarizePanel(prev => ({ ...prev, visible: false }))
          setMonitorPanel(prev => ({ ...prev, visible: false }))
          setSocialPanel(prev => ({ ...prev, visible: false }))
          setResearchPanel(prev => ({ ...prev, visible: false }))
          setAgentsPanel(prev => ({ ...prev, visible: false }))
          setParallelPanelOpen(false)
          setCameraFullscreen(false)
          setWorldMonitorOpen(false)
          setFloatingWindows?.([])
          setToolShowcase?.(prev => ({ ...prev, visible: false }))
          break
      }
    }

    const onBackgroundCmdStatus = (data) => {
      if (!data) return
      setTask(prev => {
        if (!prev || (prev.status !== 'running' && prev.status !== 'pending')) return prev
        return { ...prev, status: 'running' }
      })
      setTaskData({
        command: data.command || '', output: data.output || '',
        attempt: data.attempt || 0, total_attempts: data.total || 1,
        phase: data.phase || 'running', success: data.success, error: data.error || '',
      })
      if (data.phase === 'done' || data.phase === 'failed') {
        setTerminal((prev) => ({
          ...prev, visible: true,
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

    const onAudioData = (data) => {
      if (data && data.data) {
        if (typeof data.data === 'string') playPcmBytes(data.data)
        else if (Array.isArray(data.data)) playPcmBytes(data.data)
      }
    }

    const onMicLevel = (data) => { if (data && typeof data.level === 'number') setOrbMicLevel(data.level) }

    const onToolBatchStart = (data) => {
      if (!data || !data.tools || !data.tools.length) return
      const newTools = data.tools.map(t => ({
        id: t.id, name: t.name, args: t.args, status: 'running', result: null,
      }))
      setToolQueue(prev => [...prev, ...newTools])
      setParallelPanelOpen(true)
    }

    const onToolBatchResult = (data) => {
      if (!data || !data.results) return
      setToolQueue(prev => prev.map(tool => {
        const r = data.results.find(res => res.id === tool.id)
        if (!r) return tool
        const hasError = (() => {
          const text = JSON.stringify(r.result || '').toLowerCase()
          return text.includes('error') || text.includes('fail')
        })()
        return { ...tool, status: hasError ? 'error' : 'done', result: r.result }
      }))
    }

    const onTaskPlanUpdate = (data) => {
      if (data && data.tasks) setTaskTerminalVisible(true)
      else setTaskTerminalVisible(false)
    }

    const onPentestOutput = (data) => {
      if (data?.report) {
        setPentestResult(data); setPentestActive(false)
        setPentestProgress(null); setPentestVisible(true)
      }
    }

    const onEmailData = (data) => { if (data) setEmailPanel({ visible: true, data }) }
    const onResearchData = (data) => { if (data) setResearchResultsPanel({ visible: true, data }) }

    const onBgTaskStatus = (data) => {
      if (data) setBackgroundTaskPanel(prev => ({
        visible: true,
        data: prev.data ? { ...prev.data, tasks: [...(prev.data.tasks || []).filter(t => t.task_id !== data.task_id), data] } : data
      }))
    }

    const onOpenUrl = (data) => { if (data && data.url) openUrlInFloatingWindow(data.url, data.webview_id) }
    const onOpenSchedule = (data) => {
      if (data) openFloatingWindow('schedule_panel', 'SCHEDULE', { type: 'schedule', data }, 460, 60, 480, 520)
    }
    const onOpenNotepad = (data) => {
      if (!data || !data.id) return
      const id = data.id
      const tabs = (data.tabs || []).map((t, i) => ({ id: `tab_${i+1}`, title: t.title || 'notes', content: t.content || '', dirty: false }))
      openFloatingWindow(id, 'NOTEPAD', { type: 'notepad', id, tabs }, 100, 80, 520, 400)
    }
    const onCameraFullscreenOpen = () => setCameraFullscreen(true)
    const onWorldMonitorOpen = () => setWorldMonitorOpen(true)
    const onWorldMonitorNavigate = (data) => {
      if (!data || !data.section) return
      const iframe = document.getElementById('world-monitor-iframe')
      if (iframe && iframe.contentWindow) {
        iframe.contentWindow.postMessage({ type: 'wm-navigate', section: data.section }, '*')
      }
    }

    const pendingDataRequests = new Map()
    const onWorldMonitorDataRequest = (data) => {
      if (!data || !data.requestId) return
      const iframe = document.getElementById('world-monitor-iframe')
      if (!iframe || !iframe.contentWindow) {
        socket.emit('world_monitor_data_response', { requestId: data.requestId, data: { error: 'World Monitor not open' } })
        return
      }
      const handler = (event) => {
        if (event.data?.type === 'wm-panel-data' && event.data.requestId === data.requestId) {
          window.removeEventListener('message', handler)
          pendingDataRequests.delete(data.requestId)
          socket.emit('world_monitor_data_response', { requestId: data.requestId, data: event.data.data })
        }
      }
      window.addEventListener('message', handler)
      pendingDataRequests.set(data.requestId, handler)
      iframe.contentWindow.postMessage({ type: 'wm-export-data', sections: data.sections || ['all'], requestId: data.requestId }, '*')
      setTimeout(() => {
        if (pendingDataRequests.has(data.requestId)) {
          window.removeEventListener('message', handler)
          pendingDataRequests.delete(data.requestId)
          socket.emit('world_monitor_data_response', { requestId: data.requestId, data: { error: 'Timeout waiting for World Monitor data' } })
        }
      }, 10000)
    }

    const onViewFile = (data) => {
      if (!data || !data.payload) return
      const { payload } = data
      const fileName = payload.path.split('\\').pop().split('/').pop()
      const fwId = `file_view_${Date.now()}`
      openFloatingWindow(fwId, fileName, { type: 'file_viewer', mediaType: payload.type, content: payload.content, mime: payload.mime, path: payload.path }, 120, 80, 600, 480)
    }

    const onPentestProgress = (data) => { if (data) setPentestProgress(data) }
    const onTelegramMessage = (data) => {
      if (!data || !data.text) return
      setTaskData({ command: `Telegram: ${data.text.slice(0, 60)}`, output: data.text, success: true })
    }

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

    const onRequestBrowserUrl = async () => {
      let foundUrl = ''
      const fws = floatingWindowsRef.current
      for (const fw of fws) {
        if (fw.content?.type === 'web' && fw.content?.id && fw.content?.url) {
          const result = await WebviewActionService.getUrl(fw.content.id)
          if (result?.success && result?.result?.url) { foundUrl = result.result.url; break }
        }
      }
      if (!foundUrl) {
        for (const fw of fws) {
          if (fw.content?.type === 'web' && fw.content?.url) { foundUrl = fw.content.url; break }
        }
      }
      socket.emit('browser_url_response', { url: foundUrl })
    }

    const onPersonality = (data) => {
      if (data && data.text) {
        setPersonalityText(data.text)
        setPersonalityMood(data.mood || 'neutral')
        if (personalityTimerRef.current) clearTimeout(personalityTimerRef.current)
        personalityTimerRef.current = setTimeout(() => { setPersonalityText(null) }, 5000)
      }
    }

    const onIdleMode = (data) => {
      setIdleMode(data.active)
      if (data.active && window.electron?.enterBackground) {
        setBackgroundMode(true); window.electron.enterBackground()
      } else if (!data.active && window.electron?.exitBackground) {
        setBackgroundMode(false); window.electron.exitBackground()
      }
    }

    const onBackgroundMode = (data) => {
      setBackgroundMode(data.active)
      if (data.active && window.electron?.enterBackground) window.electron.enterBackground()
      else if (!data.active && window.electron?.exitBackground) window.electron.exitBackground()
    }

    const onSpeakingState = (data) => { if (data && data.state) setSpeakingState(data.state) }
    const onWakeSequence = (data) => { if (data && data.active) setWaking(true) }
    const onDailyBrief = (data) => { if (data) setDailyBrief({ visible: true, data }) }
    const onNightWinddown = () => { setNightWinddown(true) }

    const onShutdown = () => {
      if (window.electron?.close) window.electron.close()
      else if (window.close) window.close()
    }

    const onRemoteCount = (data) => { if (data && typeof data.count === 'number') setRemoteCount(data.count) }

    const onReminderFired = (data) => {
      if (data && data.message) {
        const ln = (() => { try { return window.Capacitor?.Plugins?.LocalNotifications } catch { return null } })()
        if (ln) {
          ln.schedule({
            notifications: [{
              id: data.id ? parseInt(data.id, 36) || undefined : undefined,
              title: 'SODA Reminder', body: data.message,
              schedule: { at: new Date() },
              smallIcon: 'ic_stat_soda', iconColor: '#0a0a0f', channelId: 'soda-reminders',
            }]
          }).catch(() => {})
        }
      }
    }

    // Register all events
    window.addEventListener('soda:tool-resolved', handleResolve)
    socket.on('connect', onConnect)
    socket.on('disconnect', onDisconnect)
    socket.on('connect_error', onConnectError)
    socket.on('agent_connection_status', (data) => setAgentState(data))
    socket.on('tool_confirmation_request', onConfirm)
    socket.on('command_output', onCommandOutput)
    socket.on('background_cmd_status', onBackgroundCmdStatus)
    socket.on('audio_data', onAudioData)
    socket.on('mic_level', onMicLevel)
    socket.on('search_results', onSearchResults)
    socket.on('tool_showcase', onToolShowcase)
    socket.on('webpage_content', onWebpageContent)
    socket.on('file_list', onFileList)
    socket.on('scraped_data', onScrapedData)
    socket.on('tool_result', onToolResult)
    socket.on('tool_batch_start', onToolBatchStart)
    socket.on('tool_batch_result', onToolBatchResult)
    socket.on('now_playing', (data) => { setTaskData(data); setTimeout(() => setTaskData(null), 4000) })
    socket.on('panel_open', onPanelOpen)
    socket.on('error', onError)
    socket.on('close_panel', onClosePanel)
    socket.on('task_plan_update', onTaskPlanUpdate)
    socket.on('pentest_output', onPentestOutput)
    socket.on('email_data', onEmailData)
    socket.on('research_data', onResearchData)
    socket.on('bg_task_status', onBgTaskStatus)
    socket.on('open_url', onOpenUrl)
    socket.on('open_schedule', onOpenSchedule)
    socket.on('open_notepad', onOpenNotepad)
    socket.on('camera_fullscreen_open', onCameraFullscreenOpen)
    socket.on('view_file_content', onViewFile)
    socket.on('pentest_scan_progress', onPentestProgress)
    socket.on('telegram_message', onTelegramMessage)
    socket.on('webview_action', onWebviewAction)
    socket.on('request_browser_url', onRequestBrowserUrl)
    socket.on('window_minimize', () => { if (window.electron?.minimize) window.electron.minimize() })
    socket.on('window_restore', () => { if (window.electron?.restore) window.electron.restore() })
    socket.on('idle_mode', onIdleMode)
    socket.on('background_mode', onBackgroundMode)
    socket.on('speaking_state', onSpeakingState)
    socket.on('wake_sequence', onWakeSequence)
    socket.on('daily_brief', onDailyBrief)
    socket.on('night_winddown', onNightWinddown)
    socket.on('personality', onPersonality)
    socket.on('shutdown', onShutdown)
    socket.on('stop_audio', stopAudio)
    socket.on('soda_remote_count', onRemoteCount)
    socket.on('reminder_fired', onReminderFired)
    socket.on('world_monitor_open', onWorldMonitorOpen)
    socket.on('world_monitor_navigate', onWorldMonitorNavigate)
    socket.on('get_world_monitor_data', onWorldMonitorDataRequest)

    // Request notification permission
    const ln = (() => { try { return window.Capacitor?.Plugins?.LocalNotifications } catch { return null } })()
    if (ln) {
      ln.requestPermissions().catch(() => {})
      ln.createChannel({
        id: 'soda-reminders', name: 'SODA Reminders',
        importance: 4, visibility: 1, sound: 'default',
        vibration: true, lights: true
      }).catch(() => {})
    }

    socket.connect()
    if (socket.connected) onConnect()

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
    socket.off('tool_showcase', onToolShowcase)
      socket.off('webpage_content', onWebpageContent)
      socket.off('file_list', onFileList)
      socket.off('scraped_data', onScrapedData)
      socket.off('tool_result', onToolResult)
      socket.off('tool_batch_start', onToolBatchStart)
      socket.off('tool_batch_result', onToolBatchResult)
      socket.off('now_playing')
      socket.off('panel_open', onPanelOpen)
      socket.off('error', onError)
      socket.off('close_panel', onClosePanel)
      socket.off('task_plan_update', onTaskPlanUpdate)
      socket.off('open_url', onOpenUrl)
      socket.off('open_schedule', onOpenSchedule)
      socket.off('open_notepad', onOpenNotepad)
      socket.off('camera_fullscreen_open', onCameraFullscreenOpen)
      socket.off('view_file_content', onViewFile)
      socket.off('telegram_message', onTelegramMessage)
      socket.off('webview_action', onWebviewAction)
      socket.off('window_minimize')
      socket.off('window_restore')
      socket.off('idle_mode', onIdleMode)
      socket.off('background_mode', onBackgroundMode)
      socket.off('speaking_state', onSpeakingState)
      socket.off('wake_sequence', onWakeSequence)
      socket.off('daily_brief', onDailyBrief)
      socket.off('night_winddown', onNightWinddown)
      socket.off('personality', onPersonality)
      socket.off('shutdown', onShutdown)
      socket.off('stop_audio', stopAudio)
      socket.off('soda_remote_count', onRemoteCount)
      socket.off('reminder_fired')
      socket.off('pentest_scan_progress', onPentestProgress)
      socket.off('pentest_output', onPentestOutput)
      socket.off('email_data', onEmailData)
      socket.off('research_data', onResearchData)
      socket.off('bg_task_status', onBgTaskStatus)
      socket.off('world_monitor_open', onWorldMonitorOpen)
      socket.off('world_monitor_navigate', onWorldMonitorNavigate)
      socket.off('get_world_monitor_data', onWorldMonitorDataRequest)
      socket.off('request_browser_url', onRequestBrowserUrl)
      // Clean up any pending world monitor data request listeners
      for (const [, handler] of pendingDataRequests) {
        window.removeEventListener('message', handler)
      }
      pendingDataRequests.clear()
      if (clearTaskTimeoutRef.current) clearTimeout(clearTaskTimeoutRef.current)
      if (showcaseTimerRef.current) clearTimeout(showcaseTimerRef.current)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps
}
