import { useState, useEffect, useRef, useCallback } from 'react'
import SlidePanel from '../SlidePanel'
import { Wrench, Code, Globe, FileText, Terminal, Monitor, Brain, Clock, MessageSquare, GripVertical } from 'lucide-react'

const CATEGORIES = [
  {
    key: 'files', label: 'Files & Storage', icon: <FileText size={10} />, color: '#4fc3f7',
    tools: new Set(['write_file','read_file','edit_file','open_file','list_files','create_folder','delete_items','rename_item','copy_item','move_item','list_drives','scroll_file_list','view_file','notepad_open','notepad_write','notepad_read','export_data'])
  },
  {
    key: 'code', label: 'Code & Terminal', icon: <Code size={10} />, color: '#81c784',
    tools: new Set(['terminal_execute','execute_command','run_code','open_app'])
  },
  {
    key: 'web', label: 'Web & Search', icon: <Globe size={10} />, color: '#ffb74d',
    tools: new Set(['web_search_live','browse_webpage','open_browser','show_search_results','get_weather','get_news','news_control','get_exchange_rate','define_word','get_wikipedia_summary','scrape_site','get_pagespeed_insights','webview_action'])
  },
  {
    key: 'system', label: 'System', icon: <Monitor size={10} />, color: '#e57373',
    tools: new Set(['control_system','get_system_status','list_processes','get_active_window','close_window','close_panel','shutdown_soda','shutdown_system','go_to_sleep','wake_up','go_background','come_back','welcome_home'])
  },
  {
    key: 'vision', label: 'Vision & Screen', icon: <Monitor size={10} />, color: '#ba68c8',
    tools: new Set(['screenshot','analyze_screen','read_screen_text','recognize_face','remember_face','take_photo'])
  },
  {
    key: 'clipboard', label: 'Clipboard', icon: <GripVertical size={10} />, color: '#4db6ac',
    tools: new Set(['clipboard_read','clipboard_write'])
  },
  {
    key: 'memory', label: 'Memory & Knowledge', icon: <Brain size={10} />, color: '#fff176',
    tools: new Set(['remember_fact','recall_facts','forget_fact','list_memory','remember_person','recall_person','remember_lesson','get_user_profile','set_preference','show_memory'])
  },
  {
    key: 'schedule', label: 'Schedule & Reminders', icon: <Clock size={10} />, color: '#a1887f',
    tools: new Set(['set_reminder','list_reminders','cancel_reminder','set_schedule','list_schedules','delete_schedule','show_calendar','plan_tasks','update_task','cancel_plan','get_plan','create_scheduled_task','list_scheduled_tasks','delete_scheduled_task'])
  },
  {
    key: 'comm', label: 'Communication', icon: <MessageSquare size={10} />, color: '#90caf9',
    tools: new Set(['send_telegram_message','send_telegram_file','search_and_send_telegram','whatsapp_find_and_call','whatsapp_find_and_message','send_whatsapp','send_discord'])
  },
  {
    key: 'devops', label: 'DevOps & Git', icon: <Terminal size={10} />, color: '#aed581',
    tools: new Set(['github_list_repos','github_create_repo','github_get_repo','github_create_pr','github_list_issues','github_create_issue','vercel_list_projects','vercel_deploy','vercel_list_deployments','vercel_get_deployment','netlify_list_sites','netlify_get_site','netlify_deploy','netlify_create_site','netlify_list_deploys'])
  },
  {
    key: 'input', label: 'Input Control', icon: <Terminal size={10} />, color: '#ff8a65',
    tools: new Set(['mouse_click','mouse_move','mouse_scroll','mouse_drag','keyboard_type','keyboard_press','window_focus','window_list','window_move'])
  },
  {
    key: 'other', label: 'Other', icon: <Wrench size={10} />, color: '#bdbdbd',
    tools: new Set(['play_music','control_music','workbase_list','workbase_get','workbase_save_progress','workbase_import','workbase_save_context','workbase_compare','show_agents','open_pastebox'])
  },
]

function getCategoryForTool(name) {
  for (const cat of CATEGORIES) {
    if (cat.tools.has(name)) return cat
  }
  return CATEGORIES[CATEGORIES.length - 1]
}

function toolLabel(name) {
  return (name || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

export default function ToolShowcasePanel({ visible, tools, onClose }) {
  const [revealedCount, setRevealedCount] = useState(0)
  const scrollRef = useRef(null)
  const [activeCategory, setActiveCategory] = useState(null)
  const [briefing, setBriefing] = useState(null)

  useEffect(() => {
    if (!visible) {
      setRevealedCount(0)
      setActiveCategory(null)
      setBriefing(null)
      return
    }
    if (!tools || tools.length === 0) return
    setRevealedCount(0)
    setActiveCategory(null)
    setBriefing(null)
    let i = 0
    const interval = setInterval(() => {
      i++
      setRevealedCount(i)
      if (i >= tools.length) clearInterval(interval)
    }, 60)
    return () => clearInterval(interval)
  }, [visible, tools])

  useEffect(() => {
    if (!tools || revealedCount === 0) return
    const idx = Math.min(revealedCount - 1, tools.length - 1)
    const tool = tools[idx]
    if (!tool) return
    const cat = getCategoryForTool(tool.name || tool)
    setActiveCategory(cat.key)
    setBriefing({
      name: tool.name || tool,
      description: tool.description || '',
      category: cat
    })
  }, [revealedCount, tools])

  if (!tools || tools.length === 0) return null

  const total = tools.length

  return (
    <SlidePanel
      visible={visible}
      direction="right"
      title="SODA TOOLKIT"
      icon={<Wrench size={11} />}
      accentColor="#00fbfb"
      onClose={onClose}
      autoDismissMs={0}
    >
      <div ref={scrollRef} style={{ maxHeight: '65vh', overflowY: 'auto', padding: '0 2px' }}>
        <div style={{ padding: '8px 0', borderBottom: '1px solid rgba(0,251,251,0.15)', marginBottom: 8 }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#00fbfb', letterSpacing: 1 }}>
            {total} TOOLS
          </div>
          <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', letterSpacing: 2, marginTop: 2 }}>
            Loaded &amp; Ready
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {tools.filter(Boolean).map((tool, i) => {
            const name = (typeof tool === 'string' ? tool : tool?.name) || ''
            const desc = (typeof tool === 'object' && tool ? tool.description : '') || ''
            const cat = getCategoryForTool(name)
            const isRevealed = i < revealedCount
            const isActive = isRevealed && briefing && briefing.name === name

            return (
              <div
                key={name}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 8,
                  padding: '6px 8px',
                  borderRadius: 3,
                  background: isActive ? 'rgba(0,251,251,0.08)' : 'transparent',
                  borderLeft: `2px solid ${isActive ? cat.color : 'transparent'}`,
                  opacity: isRevealed ? 1 : 0,
                  transform: isRevealed ? 'translateX(0)' : 'translateX(-8px)',
                  transition: 'all 0.3s ease',
                  transitionDelay: `${i * 0.03}s`,
                }}
              >
                <div style={{
                  width: 18, height: 18, borderRadius: 2,
                  background: cat.color, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 8, fontWeight: 700, color: '#0a0a0a', flexShrink: 0, marginTop: 1
                }}>
                  {i + 1}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: 10, fontWeight: 600, color: '#e0e0e0',
                    textTransform: 'uppercase', letterSpacing: 0.5
                  }}>
                    {toolLabel(name)}
                  </div>
                  {desc && (
                    <div style={{
                      fontSize: 9, color: 'rgba(255,255,255,0.5)', marginTop: 1,
                      lineHeight: 1.3, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
                      overflow: 'hidden'
                    }}>
                      {desc}
                    </div>
                  )}
                </div>
                <div style={{
                  fontSize: 7, color: cat.color, whiteSpace: 'nowrap',
                  padding: '1px 4px', borderRadius: 2,
                  background: `${cat.color}15`, marginLeft: 4, flexShrink: 0, marginTop: 2
                }}>
                  {cat.label}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div style={{
        borderTop: '1px solid rgba(0,251,251,0.15)', padding: '6px 8px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        fontSize: 9, color: 'rgba(255,255,255,0.4)'
      }}>
        <span>
          <span style={{ color: '#00fbfb', fontWeight: 700 }}>{revealedCount}</span> / {total} tools
        </span>
        {briefing && activeCategory && revealedCount < total && (
          <span style={{ color: briefing.category.color }}>
            {briefing.category.label}
          </span>
        )}
        {revealedCount >= total && (
          <span style={{ color: '#81c784' }}>Complete</span>
        )}
      </div>
    </SlidePanel>
  )
}
