import { useState, useRef, useCallback } from 'react'

export default function usePanelState() {
  const [terminal, setTerminal] = useState({ visible: false, command: '', output: '', success: null, attempts: [], total_attempts: 1 })
  const terminalTimerRef = useRef(null)

  const [search, setSearch] = useState({ visible: false, query: '', results: [] })
  const searchTimerRef = useRef(null)

  const [dailyBrief, setDailyBrief] = useState({ visible: false, data: null })
  const [nightWinddown, setNightWinddown] = useState(false)

  const [fileOutput, setFileOutput] = useState({ visible: false, type: 'file', title: '', content: '', success: null })
  const fileTimerRef = useRef(null)

  const [infoPanel, setInfoPanel] = useState({ visible: false, type: 'info', data: null })
  const infoTimerRef = useRef(null)

  const [toolPanel, setToolPanel] = useState({ visible: false, toolName: '', status: 'running', output: null, args: null })
  const toolTimerRef = useRef(null)

  const [toolQueue, setToolQueue] = useState([])
  const [parallelPanelOpen, setParallelPanelOpen] = useState(false)

  // Agent result panels
  const [wikipediaPanel, setWikipediaPanel] = useState({ visible: false, data: null })
  const [newsPanel, setNewsPanel] = useState({ visible: false, data: null })
  const [codePanel, setCodePanel] = useState({ visible: false, data: null })
  const [dataPanel, setDataPanel] = useState({ visible: false, data: null })
  const [translatePanel, setTranslatePanel] = useState({ visible: false, data: null })
  const [summarizePanel, setSummarizePanel] = useState({ visible: false, data: null })
  const [monitorPanel, setMonitorPanel] = useState({ visible: false, data: null })
  const [metricsPanel, setMetricsPanel] = useState({ visible: false, data: null })
  const [socialPanel, setSocialPanel] = useState({ visible: false, data: null })
  const [researchPanel, setResearchPanel] = useState({ visible: false, data: null })
  const [agentsPanel, setAgentsPanel] = useState({ visible: false, data: null })

  const [webpageSummary, setWebpageSummary] = useState({ visible: false, url: '', content: '', success: null, images: [] })
  const webpageTimerRef = useRef(null)

  const [fileBrowser, setFileBrowser] = useState({ visible: false, path: '', items: [], success: null, searchQuery: '' })
  const fileBrowserTimerRef = useRef(null)

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
  const [researchResultsPanel, setResearchResultsPanel] = useState({ visible: false, data: null })
  const [backgroundTaskPanel, setBackgroundTaskPanel] = useState({ visible: false, data: null })
  const [emailPanel, setEmailPanel] = useState({ visible: false, data: null })
  const [projectStatsPanel, setProjectStatsPanel] = useState({ visible: false, data: null })

  // IELTS panels
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
  const [waking, setWaking] = useState(false)
  const [cameraFullscreen, setCameraFullscreen] = useState(false)
  const [worldMonitorOpen, setWorldMonitorOpen] = useState(false)
  const personalityTimerRef = useRef(null)

  const closeTerminal = useCallback(() => {
    if (terminalTimerRef.current) clearTimeout(terminalTimerRef.current)
    setTerminal(prev => ({ ...prev, visible: false }))
  }, [])

  const closeSearch = useCallback(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    setSearch(prev => ({ ...prev, visible: false }))
  }, [])

  const closeFileOutput = useCallback(() => {
    if (fileTimerRef.current) clearTimeout(fileTimerRef.current)
    setFileOutput(prev => ({ ...prev, visible: false }))
  }, [])

  const closeInfoPanel = useCallback(() => {
    if (infoTimerRef.current) clearTimeout(infoTimerRef.current)
    setInfoPanel(prev => ({ ...prev, visible: false }))
  }, [])

  const closeToolPanel = useCallback(() => {
    if (toolTimerRef.current) clearTimeout(toolTimerRef.current)
    setToolPanel(prev => ({ ...prev, visible: false }))
  }, [])

  const closeWebpageSummary = useCallback(() => {
    if (webpageTimerRef.current) clearTimeout(webpageTimerRef.current)
    setWebpageSummary(prev => ({ ...prev, visible: false }))
  }, [])

  const closeFileBrowser = useCallback(() => {
    if (fileBrowserTimerRef.current) clearTimeout(fileBrowserTimerRef.current)
    setFileBrowser(prev => ({ ...prev, visible: false }))
  }, [])

  const closeScrapedData = useCallback(() => {
    setScrapedData({ visible: false, data: null, url: '' })
  }, [])

  return {
    // Terminal
    terminal, setTerminal, terminalTimerRef, closeTerminal,
    // Search
    search, setSearch, searchTimerRef, closeSearch,
    // Daily brief
    dailyBrief, setDailyBrief, nightWinddown, setNightWinddown,
    // File output
    fileOutput, setFileOutput, fileTimerRef, closeFileOutput,
    // Info panel
    infoPanel, setInfoPanel, infoTimerRef, closeInfoPanel,
    // Tool panel
    toolPanel, setToolPanel, toolTimerRef, closeToolPanel,
    // Parallel tools
    toolQueue, setToolQueue, parallelPanelOpen, setParallelPanelOpen,
    // Agent panels
    wikipediaPanel, setWikipediaPanel, newsPanel, setNewsPanel,
    codePanel, setCodePanel, dataPanel, setDataPanel,
    translatePanel, setTranslatePanel, summarizePanel, setSummarizePanel,
    monitorPanel, setMonitorPanel, socialPanel, setSocialPanel,
    metricsPanel, setMetricsPanel,
    researchPanel, setResearchPanel, agentsPanel, setAgentsPanel,
    // Webpage
    webpageSummary, setWebpageSummary, webpageTimerRef, closeWebpageSummary,
    // File browser
    fileBrowser, setFileBrowser, fileBrowserTimerRef, closeFileBrowser,
    // Scraped data
    scrapedData, setScrapedData, closeScrapedData,
    // Specialized panels
    weatherPanel, setWeatherPanel, systemStatusPanel, setSystemStatusPanel,
    memoryPanel, setMemoryPanel, currencyPanel, setCurrencyPanel,
    processPanel, setProcessPanel, networkPanel, setNetworkPanel,
    taskTerminalVisible, setTaskTerminalVisible,
    pentestVisible, setPentestVisible, pentestActive, setPentestActive,
    pentestProgress, setPentestProgress, pentestResult, setPentestResult,
    gitHubPanel, setGitHubPanel, deployPanel, setDeployPanel,
    pageSpeedPanel, setPageSpeedPanel, researchResultsPanel, setResearchResultsPanel,
    backgroundTaskPanel, setBackgroundTaskPanel, emailPanel, setEmailPanel,
    projectStatsPanel, setProjectStatsPanel,
    // IELTS
    ieltsDashboard, setIeltsDashboard, ieltsWriting, setIeltsWriting,
    ieltsSpeaking, setIeltsSpeaking, ieltsReading, setIeltsReading,
    ieltsVocab, setIeltsVocab, ieltsProgress, setIeltsProgress,
    // Misc
    orbMicLevel, setOrbMicLevel, remoteCount, setRemoteCount,
    personalityText, setPersonalityText, personalityMood, setPersonalityMood,
    idleMode, setIdleMode, backgroundMode, setBackgroundMode,
    speakingState, setSpeakingState, waking, setWaking,
    cameraFullscreen, setCameraFullscreen, worldMonitorOpen, setWorldMonitorOpen,
    personalityTimerRef,
  }
}
