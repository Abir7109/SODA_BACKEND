import { lazy } from 'react'

// ── Lazy-loaded animation components ────────────────────────────
// Only ONE renders at a time (behind the SODA orb), so no perf impact.
const DefaultAnimation = lazy(() => import('./DefaultAnimation'))
const SearchAnimation  = lazy(() => import('./SearchAnimation'))
const SystemAnimation  = lazy(() => import('./SystemAnimation'))
const MessageAnimation = lazy(() => import('./MessageAnimation'))
const FileAnimation    = lazy(() => import('./FileAnimation'))
const FileTreeAnim     = lazy(() => import('./FileTreeAnim'))
const WebpageAnim      = lazy(() => import('./WebpageAnim'))
const TerminalAnim     = lazy(() => import('./TerminalAnim'))
const CodeAnim         = lazy(() => import('./CodeAnim'))
const ClipboardAnim    = lazy(() => import('./ClipboardAnim'))
const ScreenshotAnim   = lazy(() => import('./ScreenshotAnim'))
const MemoryAnim       = lazy(() => import('./MemoryAnim'))
const ReminderAnim     = lazy(() => import('./ReminderAnim'))
const ScreenAnim       = lazy(() => import('./ScreenAnim'))
const AppLaunchAnim    = lazy(() => import('./AppLaunchAnim'))
const CloseAnim        = lazy(() => import('./CloseAnim'))
const DataAnim             = lazy(() => import('./DataAnim'))
const AiSystemMonitor     = lazy(() => import('./AiSystemMonitor'))
const AiWeatherDiagnostics = lazy(() => import('./AiWeatherDiagnostics'))
const AiTerminalCompiler  = lazy(() => import('./AiTerminalCompiler'))
const AiSchedulerAlarm    = lazy(() => import('./AiSchedulerAlarm'))
const GitDeployAnim       = lazy(() => import('./GitDeployAnim'))
const SearchSendAnim      = lazy(() => import('./SearchSendAnim'))
const BackgroundCommandAnim = lazy(() => import('./BackgroundCommandAnim'))

// ── Animation map (component name → lazy component) ─────────────
export const ANIMATION_MAP = {
  DefaultAnimation,
  SearchAnimation,
  SystemAnimation,
  MessageAnimation,
  FileAnimation,
  FileTreeAnim,
  WebpageAnim,
  TerminalAnim,
  CodeAnim,
  ClipboardAnim,
  ScreenshotAnim,
  MemoryAnim,
  ReminderAnim,
  ScreenAnim,
  AppLaunchAnim,
  CloseAnim,
  DataAnim,
  AiSystemMonitor,
  AiWeatherDiagnostics,
  AiTerminalCompiler,
  AiSchedulerAlarm,
  GitDeployAnim,
  SearchSendAnim,
  BackgroundCommandAnim,
}

// ── Full 34-tool category mapping (backward compatible) ─────────
export const CATEGORIES = {
  FILE: 'file',
  SEARCH: 'search',
  SYSTEM: 'system',
  MESSAGE: 'message',
  CODE: 'code',
  CLIPBOARD: 'clipboard',
  MEMORY: 'memory',
  REMINDER: 'reminder',
  SCREEN: 'screen',
  DATA: 'data',
  DEFAULT: 'default',
}

export const TOOL_CATEGORY = {
  // File
  write_file: CATEGORIES.FILE,
  read_file: CATEGORIES.FILE,
  open_file: CATEGORIES.FILE,
  create_project: CATEGORIES.FILE,
  switch_project: CATEGORIES.FILE,
  project_registry: CATEGORIES.FILE,
  list_files: CATEGORIES.FILE,

  // Search / Web
  web_search_live: CATEGORIES.SEARCH,
  show_search_results: CATEGORIES.SEARCH,
  browse_webpage: CATEGORIES.SEARCH,
  open_browser: CATEGORIES.SEARCH,

  // System
  control_system: CATEGORIES.SYSTEM,
  open_app: CATEGORIES.SYSTEM,
  search_web: CATEGORIES.SYSTEM,
  search_youtube: CATEGORIES.SYSTEM,
  terminal_execute: CATEGORIES.SYSTEM,
  execute_command: CATEGORIES.SYSTEM,
  close_window: CATEGORIES.SYSTEM,
  close_panel: CATEGORIES.SYSTEM,
  webview_action: CATEGORIES.SYSTEM,

  // Communication
  send_whatsapp: CATEGORIES.MESSAGE,
  send_discord: CATEGORIES.MESSAGE,
  search_and_send_telegram: CATEGORIES.MESSAGE,

  // Code
  run_code: CATEGORIES.CODE,

  // Screenshot
  screenshot: CATEGORIES.SCREEN,

  // Memory / Profile
  remember_fact: CATEGORIES.MEMORY,
  recall_facts: CATEGORIES.MEMORY,
  get_user_profile: CATEGORIES.MEMORY,
  set_preference: CATEGORIES.MEMORY,
  forget_fact: CATEGORIES.MEMORY,
  list_memory: CATEGORIES.MEMORY,
  remember_person: CATEGORIES.MEMORY,
  recall_person: CATEGORIES.MEMORY,
  remember_lesson: CATEGORIES.MEMORY,

  // Reminders
  reminder: CATEGORIES.REMINDER,

  // Screen Analysis
  analyze_screen: CATEGORIES.SCREEN,
  read_screen_text: CATEGORIES.SCREEN,
  get_active_window: CATEGORIES.SCREEN,
  recognize_face: CATEGORIES.SCREEN,
  remember_face: CATEGORIES.MEMORY,

  // Data Tools
  get_weather: CATEGORIES.DATA,
  get_news: CATEGORIES.DATA,
  get_exchange_rate: CATEGORIES.DATA,
  get_system_status: CATEGORIES.DATA,
  list_processes: CATEGORIES.DATA,
  get_ip_info: CATEGORIES.DATA,
  define_word: CATEGORIES.DATA,
  get_wikipedia_summary: CATEGORIES.DATA,

  // Git / Deploy
  plan: CATEGORIES.SYSTEM,
  github: CATEGORIES.DATA,
  vercel: CATEGORIES.DATA,
  netlify: CATEGORIES.DATA,

  // Email
  email: CATEGORIES.DATA,

  // Navigation
  get_navigation_route: CATEGORIES.DATA,
}

export function getCategory(toolName) {
  if (!toolName) return CATEGORIES.DEFAULT
  return TOOL_CATEGORY[toolName] || CATEGORIES.DEFAULT
}

// ── Tool → Animation resolution ─────────────────────────────────
import { TOOL_ANIMATIONS } from './ToolAnimationRegistry'

/**
 * Get the lazy-loaded animation component for a tool.
 * Falls back to DefaultAnimation if unknown.
 */
export function getAnimationForTool(toolName) {
  const entry = TOOL_ANIMATIONS[toolName]
  if (!entry) return DefaultAnimation
  return ANIMATION_MAP[entry.component] || DefaultAnimation
}

/**
 * Get the variant prop for a tool's animation.
 */
export function getVariantForTool(toolName) {
  const entry = TOOL_ANIMATIONS[toolName]
  return entry?.variant || 'default'
}

/**
 * Get the specialized panel name for a tool (if any).
 * Returns null if the tool uses the generic ToolOutputPanel.
 */
export function getSpecializedPanel(toolName) {
  const entry = TOOL_ANIMATIONS[toolName]
  return entry?.panel || null
}

/**
 * Get slide direction for a specialized panel.
 */
export function getPanelDirection(toolName) {
  const entry = TOOL_ANIMATIONS[toolName]
  return entry?.panelDir || 'bottom'
}
