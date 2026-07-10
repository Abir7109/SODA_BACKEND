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
  list_projects:   { component: 'FileTreeAnim',    variant: 'list' },
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

  // ── Telegram ─────────────────────────────────────────────────
  send_telegram_message: { component: 'TelegramAnim', variant: 'message' },
  send_telegram_file:    { component: 'TelegramAnim', variant: 'file' },

  // ── Shutdown ─────────────────────────────────────────────────
  shutdown_soda: { component: 'CloseAnim', variant: 'window' },

  // ── Search + Send ────────────────────────────────────────────
  search_and_send_telegram: { component: 'SearchSendAnim', variant: 'default' },

  // ── Code ─────────────────────────────────────────────────────
  run_code: { component: 'CodeAnim', variant: 'exec' },

  // ── Clipboard / Screenshot ───────────────────────────────────
  clipboard_read:  { component: 'ClipboardAnim',   variant: 'read' },
  clipboard_write: { component: 'ClipboardAnim',   variant: 'write' },
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

  // ── Reminders ────────────────────────────────────────────────
  set_reminder:    { component: 'AiSchedulerAlarm', variant: 'default' },
  list_reminders:  { component: 'ReminderAnim', variant: 'list' },
  cancel_reminder: { component: 'ReminderAnim', variant: 'cancel' },

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
  get_system_status:     { component: 'AiSystemMonitor',   variant: 'default' },
  list_processes:        { component: 'DataAnim', variant: 'processes',panel: 'ProcessListPanel',  panelDir: 'right' },
  get_ip_info:           { component: 'DataAnim', variant: 'network',  panel: 'NetworkInfoPanel',  panelDir: 'top' },
  define_word:           { component: 'DataAnim', variant: 'define' },
  get_wikipedia_summary: { component: 'DataAnim', variant: 'wiki' },
  get_pagespeed_insights: { component: 'DataAnim', variant: 'speed', panel: 'PageSpeedPanel', panelDir: 'right' },

  // ── Webview ──────────────────────────────────────────────────
  webview_action: { component: 'WebpageAnim', variant: 'open' },

  // ── Task Planning ────────────────────────────────────────────
  plan_tasks:  { component: 'AiTerminalCompiler', variant: 'default' },
  update_task: { component: 'AiTerminalCompiler', variant: 'default' },

  // ── GitHub ───────────────────────────────────────────────────
  github_list_repos:    { component: 'GitDeployAnim', variant: 'branch', panel: 'GitHubPanel', panelDir: 'bottom' },
  github_create_repo:   { component: 'GitDeployAnim', variant: 'branch', panel: 'GitHubPanel', panelDir: 'bottom' },
  github_get_repo:      { component: 'GitDeployAnim', variant: 'branch', panel: 'GitHubPanel', panelDir: 'bottom' },
  github_create_pr:     { component: 'GitDeployAnim', variant: 'branch', panel: 'GitHubPanel', panelDir: 'bottom' },
  github_list_issues:   { component: 'GitDeployAnim', variant: 'branch', panel: 'GitHubPanel', panelDir: 'bottom' },
  github_create_issue:  { component: 'GitDeployAnim', variant: 'branch', panel: 'GitHubPanel', panelDir: 'bottom' },

  // ── Vercel ───────────────────────────────────────────────────
  vercel_list_projects:     { component: 'GitDeployAnim', variant: 'deploy', panel: 'DeployPanel', panelDir: 'bottom' },
  vercel_deploy:            { component: 'GitDeployAnim', variant: 'deploy', panel: 'DeployPanel', panelDir: 'bottom' },
  vercel_list_deployments:  { component: 'GitDeployAnim', variant: 'deploy', panel: 'DeployPanel', panelDir: 'bottom' },
  vercel_get_deployment:    { component: 'GitDeployAnim', variant: 'deploy', panel: 'DeployPanel', panelDir: 'bottom' },

  // ── Netlify ──────────────────────────────────────────────────
  netlify_list_sites:   { component: 'GitDeployAnim', variant: 'deploy', panel: 'DeployPanel', panelDir: 'bottom' },
  netlify_get_site:     { component: 'GitDeployAnim', variant: 'deploy', panel: 'DeployPanel', panelDir: 'bottom' },
  netlify_deploy:       { component: 'GitDeployAnim', variant: 'deploy', panel: 'DeployPanel', panelDir: 'bottom' },
  netlify_create_site:  { component: 'GitDeployAnim', variant: 'deploy', panel: 'DeployPanel', panelDir: 'bottom' },
  netlify_list_deploys: { component: 'GitDeployAnim', variant: 'deploy', panel: 'DeployPanel', panelDir: 'bottom' },

  // ── Email ─────────────────────────────────────────────────────
  read_emails:  { component: 'DataAnim', variant: 'email', panel: 'EmailPanel', panelDir: 'right' },
  send_email:   { component: 'MessageAnimation', variant: 'email' },
  email_config: { component: 'DefaultAnimation', variant: 'default' },
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
