/**
 * Tool Animation Registry — maps every SODA tool to its animation component + variant.
 *
 * Each entry:
 *   component  — name of the lazy-loaded SVG animation (key in ANIMATION_MAP)
 *   variant    — sub-style passed as prop to the animation component
 *   panel      — (optional) specialized panel name for data-heavy tools
 *   panelDir   — (optional) slide direction for the panel (default 'bottom')
 */

export const TOOL_ANIMATIONS = {
  // ── File Operations ──────────────────────────────────────────
  write_file:      { component: 'FileAnimation',   variant: 'write' },
  read_file:       { component: 'FileAnimation',   variant: 'read' },
  open_file:       { component: 'FileTreeAnim',    variant: 'open' },
  create_project:  { component: 'FileTreeAnim',    variant: 'create' },
  switch_project:  { component: 'FileTreeAnim',    variant: 'create' },
  project_registry: { component: 'FileTreeAnim',    variant: 'list' },
  list_files:      { component: 'FileTreeAnim',    variant: 'list' },

  // ── Web / Search ─────────────────────────────────────────────
  web_search_live:      { component: 'SearchAnimation', variant: 'radar' },
  show_search_results:  { component: 'SearchAnimation', variant: 'results' },
  browse_webpage:       { component: 'WebpageAnim',     variant: 'load' },
  open_browser:         { component: 'WebpageAnim',     variant: 'open' },
  search_web:           { component: 'WebpageAnim',     variant: 'open' },
  search_youtube:       { component: 'WebpageAnim',     variant: 'open' },

  // ── System ───────────────────────────────────────────────────
  control_system:    { component: 'SystemAnimation', variant: 'control' },
  open_app:          { component: 'AppLaunchAnim',   variant: 'launch' },
  terminal_execute:  { component: 'BackgroundCommandAnim', variant: 'exec' },
  execute_command:   { component: 'BackgroundCommandAnim', variant: 'exec' },
  close_window:      { component: 'CloseAnim',       variant: 'window' },
  close_panel:       { component: 'CloseAnim',       variant: 'panel' },

  // ── Communication ────────────────────────────────────────────
  send_whatsapp: { component: 'MessageAnimation', variant: 'whatsapp' },
  send_discord:  { component: 'MessageAnimation', variant: 'discord' },

  // ── Search + Send ────────────────────────────────────────────
  search_and_send_telegram: { component: 'SearchSendAnim', variant: 'default' },

  // ── Code ─────────────────────────────────────────────────────
  run_code: { component: 'CodeAnim', variant: 'exec' },

  // ── Screenshot ───────────────────────────────────────────────
  screenshot:      { component: 'ScreenshotAnim',  variant: 'capture' },

  // ── Memory / Profile ─────────────────────────────────────────
  remember_fact:    { component: 'MemoryAnim', variant: 'store' },
  recall_facts:     { component: 'MemoryAnim', variant: 'recall' },
  get_user_profile: { component: 'MemoryAnim', variant: 'profile' },
  set_preference:   { component: 'MemoryAnim', variant: 'settings' },
  forget_fact:      { component: 'MemoryAnim', variant: 'store' },
  show_memory:      { component: 'MemoryAnim', variant: 'recall', panel: 'MemoryPanel', panelDir: 'bottom' },
  create_memory_schema: { component: 'MemoryAnim', variant: 'store' },
  list_custom_schemas:  { component: 'MemoryAnim', variant: 'recall' },
  store_custom_memory:  { component: 'MemoryAnim', variant: 'store' },
  query_custom_memory:  { component: 'MemoryAnim', variant: 'recall' },
  list_memory:      { component: 'MemoryAnim', variant: 'recall' },
  remember_person:  { component: 'MemoryAnim', variant: 'store' },
  recall_person:    { component: 'MemoryAnim', variant: 'recall' },
  remember_lesson:  { component: 'MemoryAnim', variant: 'store' },

  // ── Reminders (consolidated) ────────────────────────────────────
  reminder: { component: 'AiSchedulerAlarm', variant: 'default' },

  // ── Screen Analysis ──────────────────────────────────────────
  analyze_screen:   { component: 'ScreenAnim', variant: 'analyze' },
  read_screen_text: { component: 'ScreenAnim', variant: 'ocr' },
  get_active_window:{ component: 'ScreenAnim', variant: 'analyze' },
  recognize_face:   { component: 'ScreenAnim', variant: 'analyze' },
  remember_face:    { component: 'MemoryAnim', variant: 'store' },

  // ── Data Tools (rich panels) ─────────────────────────────────
  get_weather:           { component: 'AiWeatherDiagnostics', variant: 'default', panel: 'WeatherPanel', panelDir: 'top' },
  get_news:              { component: 'DataAnim', variant: 'news' },
  get_bangladeshi_news:  { component: 'DataAnim', variant: 'news' },
  get_exchange_rate:     { component: 'DataAnim', variant: 'currency', panel: 'CurrencyPanel',     panelDir: 'top' },
  get_system_status:     { component: 'AiSystemMonitor',   variant: 'default', panel: 'SystemStatusPanel', panelDir: 'right' },
  list_processes:        { component: 'DataAnim', variant: 'processes',panel: 'ProcessListPanel',  panelDir: 'right' },
  get_ip_info:           { component: 'DataAnim', variant: 'network',  panel: 'NetworkInfoPanel',  panelDir: 'top' },
  define_word:           { component: 'DataAnim', variant: 'define' },
  get_wikipedia_summary: { component: 'DataAnim', variant: 'wiki' },
  get_pagespeed_insights: { component: 'DataAnim', variant: 'speed', panel: 'PageSpeedPanel', panelDir: 'right' },

  // ── Webview ──────────────────────────────────────────────────
  webview_action: { component: 'WebpageAnim', variant: 'open' },

  // ── Research Engine V2 ───────────────────────────────────────
  deep_research:   { component: 'SearchAnimation', variant: 'results', panel: 'ResearchResultsPanel', panelDir: 'right' },
  export_research: { component: 'DefaultAnimation', variant: 'default' },

  // ── Background Agent Management (consolidated) ───────────────
  bg_tasks: { component: 'BackgroundCommandAnim', variant: 'exec', panel: 'BackgroundTaskPanel', panelDir: 'right' },

  // ── Task Planning (consolidated) ──────────────────────────────
  plan: { component: 'AiTerminalCompiler', variant: 'default' },

  // ── GitHub (consolidated) ──────────────────────────────────────
  github: { component: 'GitDeployAnim', variant: 'branch', panel: 'GitHubPanel', panelDir: 'bottom' },

  // ── Vercel (consolidated) ──────────────────────────────────────
  vercel: { component: 'GitDeployAnim', variant: 'deploy', panel: 'DeployPanel', panelDir: 'bottom' },

  // ── Netlify (consolidated) ─────────────────────────────────────
  netlify: { component: 'GitDeployAnim', variant: 'deploy', panel: 'DeployPanel', panelDir: 'bottom' },

  // ── Email (consolidated) ───────────────────────────────────────
  email: { component: 'DataAnim', variant: 'email', panel: 'EmailPanel', panelDir: 'right' },

  // ── Project Registry (consolidated) ────────────────────────────
  project_registry: { component: 'DefaultAnimation', variant: 'default', panel: 'ProjectStatsPanel', panelDir: 'right' },

  // ── Scheduled Tasks (consolidated) ────────────────────────────
  scheduled_task: { component: 'AiSchedulerAlarm', variant: 'default' },

  // ── Window (consolidated) ──────────────────────────────────────
  window: { component: 'DefaultAnimation', variant: 'default' },

  // ── File Manager (consolidated) ────────────────────────────────
  file_manager: { component: 'FileTreeAnim', variant: 'list' },

  // ── Credential (consolidated) ──────────────────────────────────
  credential: { component: 'DefaultAnimation', variant: 'default' },

  // ── Schedule (consolidated) ────────────────────────────────────
  schedule: { component: 'AiSchedulerAlarm', variant: 'default' },

  // ── Agent Sub-Agent Tools ────────────────────────────────────
  show_agents:       { component: 'DataAnim',        variant: 'analytics', panel: 'AgentsPanel',    panelDir: 'bottom' },
  agent_search:      { component: 'SearchAnimation', variant: 'radar' },
  agent_news:        { component: 'DataAnim',        variant: 'news',    panel: 'NewsPanel',        panelDir: 'bottom' },
  agent_wikipedia:   { component: 'DataAnim',        variant: 'search',  panel: 'WikipediaPanel',   panelDir: 'bottom' },
  agent_browse:      { component: 'WebpageAnim',     variant: 'load' },
  agent_code:        { component: 'CodeAnim',        variant: 'generate', panel: 'CodePanel',      panelDir: 'bottom' },
  agent_data:        { component: 'DataAnim',        variant: 'analytics', panel: 'DataPanel',     panelDir: 'bottom' },
  agent_research:    { component: 'SearchAnimation', variant: 'results',  panel: 'ResearchPanel',   panelDir: 'bottom' },
  agent_translate:   { component: 'MessageAnimation', variant: 'message', panel: 'TranslatePanel', panelDir: 'bottom' },
  agent_summarize:   { component: 'DataAnim',        variant: 'analytics', panel: 'SummarizePanel', panelDir: 'bottom' },
  agent_monitor:     { component: 'SystemAnimation',  variant: 'control',  panel: 'MonitorPanel',   panelDir: 'bottom' },
  agent_social:       { component: 'MessageAnimation', variant: 'message', panel: 'SocialPanel',    panelDir: 'bottom' },
  agent_security:     { component: 'SystemAnimation',  variant: 'control',  panel: 'CodePanel',     panelDir: 'bottom' },
  agent_database:     { component: 'DataAnim',         variant: 'analytics', panel: 'DataPanel',    panelDir: 'bottom' },
  agent_devops:       { component: 'BackgroundCommandAnim', variant: 'exec', panel: 'MonitorPanel', panelDir: 'bottom' },
}

/**
 * Get animation config for a tool.
 * Returns { component, variant, panel?, panelDir? } or null if unknown.
 */
export function getToolAnimation(toolName) {
  return TOOL_ANIMATIONS[toolName] || null
}

/**
 * Get the panel name for a tool (if it has a specialized panel).
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
