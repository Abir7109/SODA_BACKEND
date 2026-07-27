import { useState } from 'react'
import { Globe, ChevronDown, ChevronRight, Terminal, MessageSquare, X, ExternalLink, RefreshCw } from 'lucide-react'
import SlidePanel from '../SlidePanel'

function SnapshotTree({ nodes, depth = 0 }) {
  const [expanded, setExpanded] = useState(new Set())
  if (!nodes || nodes.length === 0) return <div className="text-[#666680] text-[10px] italic">No elements</div>
  const toggle = (i) => {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(i) ? next.delete(i) : next.add(i)
      return next
    })
  }
  return (
    <div style={{ marginLeft: depth * 12 }}>
      {nodes.map((n, i) => {
        const key = `${depth}-${i}`
        const hasChildren = n.children && n.children.length > 0
        const isExpanded = expanded.has(key)
        return (
          <div key={key}>
            <div className="flex items-center gap-1 py-[2px] cursor-pointer hover:bg-[#1e1e2e]/40" onClick={() => toggle(key)}>
              {hasChildren ? (
                isExpanded ? <ChevronDown size={10} className="text-[#00f0ff] shrink-0" /> : <ChevronRight size={10} className="text-[#666680] shrink-0" />
              ) : <span className="w-[10px] shrink-0" />}
              <span className="text-[10px] text-[#b0b0cc] font-mono truncate max-w-[250px]">
                {n.tag || n.role || '?'}
                {n.ref && <span className="text-[#00ff88] ml-1">@{n.ref}</span>}
                {n.name && <span className="text-[#e0e0e0] ml-1">"{n.name}"</span>}
              </span>
            </div>
            {isExpanded && hasChildren && <SnapshotTree nodes={n.children} depth={depth + 1} />}
          </div>
        )
      })}
    </div>
  )
}

function ConsoleLog({ entries }) {
  if (!entries || entries.length === 0) return <div className="text-[#666680] text-[10px] italic">No console output</div>
  return (
    <div className="space-y-1 max-h-[200px] overflow-y-auto custom-scrollbar">
      {entries.map((e, i) => (
        <div key={i} className="flex gap-2 text-[10px] font-mono border-l-2 pl-2 py-[2px]"
          style={{ borderColor: e.level === 'error' ? '#ff3355' : e.level === 'warn' ? '#ffaa00' : '#444450' }}>
          <span className="text-[#666680] shrink-0 w-8">{e.source || 'page'}</span>
          <span className={e.level === 'error' ? 'text-[#ff3355]' : e.level === 'warn' ? 'text-[#ffaa00]' : 'text-[#b0b0cc]'}>{e.text}</span>
        </div>
      ))}
    </div>
  )
}

function DialogBox({ dialog, onRespond }) {
  if (!dialog) return null
  return (
    <div className="border border-[#ffaa00]/40 bg-[#ffaa00]/5 p-3 space-y-2">
      <div className="flex items-center gap-2 text-[10px] text-[#ffaa00] uppercase tracking-wider font-bold">
        <MessageSquare size={10} />
        <span>{dialog.type} Dialog</span>
      </div>
      <div className="text-[11px] text-[#e0e0e0] font-mono">{dialog.message}</div>
      {dialog.type === 'prompt' && (
        <input className="w-full bg-[#0a0a0f] border border-[#1e1e2e] text-[11px] text-white px-2 py-1 outline-none focus:border-[#ffaa00]" placeholder="Type response..." />
      )}
      <div className="flex gap-2">
        <button onClick={() => onRespond('accept', '')}
          className="bg-[#ffaa00]/20 hover:bg-[#ffaa00]/30 border border-[#ffaa00]/40 text-[10px] text-white px-3 py-1 uppercase tracking-wider font-bold transition-all">OK</button>
        <button onClick={() => onRespond('dismiss', '')}
          className="bg-[#1e1e2e] hover:bg-[#2a2a3a] border border-[#1e1e2e] text-[10px] text-white px-3 py-1 uppercase tracking-wider font-bold transition-all">Cancel</button>
      </div>
    </div>
  )
}

export default function BrowserPanel({ visible, data, onClose }) {
  const [activeTab, setActiveTab] = useState('snapshot')
  const [snapshotExpanded, setSnapshotExpanded] = useState(true)

  if (!data) return null

  const { url, title, snapshot, console: consoleEntries, dialog, screenshot, error } = data

  if (error) {
    return (
      <SlidePanel visible={visible} direction="right" title="BROWSER" icon={<Globe size={11} />}
        accentColor="#ff3355" onClose={onClose} autoDismissMs={0}>
        <div className="flex items-center justify-center h-full text-[#ff3355] text-xs p-6">{error}</div>
      </SlidePanel>
    )
  }

  const tabs = [
    { id: 'snapshot', label: 'DOM Tree', icon: ChevronDown },
    { id: 'console', label: 'Console', icon: Terminal },
    { id: 'dialog', label: 'Dialog', icon: MessageSquare },
  ]

  return (
    <SlidePanel visible={visible} direction="right" title="BROWSER" icon={<Globe size={11} />}
      accentColor="#00f0ff" onClose={onClose} autoDismissMs={0}>
      <div className="p-4 space-y-3 font-mono text-[#e0e0e0] select-none custom-scrollbar" style={{ maxHeight: 'calc(100vh - 60px)', overflowY: 'auto' }}>

        {/* URL Bar */}
        <div className="bg-[#0a0a0f] border border-[#1e1e2e] p-2 flex items-center gap-2">
          <Globe size={10} className="text-[#00f0ff] shrink-0" />
          <span className="text-[10px] text-[#b0b0cc] truncate">{url || '—'}</span>
          {url && <ExternalLink size={10} className="text-[#666680] shrink-0 cursor-pointer hover:text-[#00f0ff]" />}
        </div>

        {/* Title */}
        <div className="text-[11px] text-[#e0e0e0] font-bold truncate">{title || 'No title'}</div>

        {/* Tabs */}
        <div className="flex border-b border-[#1e1e2e]">
          {tabs.map(t => {
            const Icon = t.icon
            return (
              <button key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={`flex items-center gap-1.5 px-3 py-2 text-[10px] uppercase tracking-wider font-bold border-b-2 transition-all ${activeTab === t.id ? 'border-[#00f0ff] text-[#00f0ff]' : 'border-transparent text-[#666680] hover:text-[#b0b0cc]'}`}>
                <Icon size={10} />
                {t.label}
              </button>
            )
          })}
        </div>

        {/* Tab Content */}
        {activeTab === 'snapshot' && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] text-[#00f0ff] uppercase tracking-widest font-bold">Accessibility Tree</span>
              <button onClick={() => setSnapshotExpanded(!snapshotExpanded)} className="text-[#666680] hover:text-[#b0b0cc] transition-colors">
                <RefreshCw size={10} />
              </button>
            </div>
            <div className="bg-[#0a0a0f] border border-[#1e1e2e] p-2 max-h-[350px] overflow-y-auto custom-scrollbar">
              <SnapshotTree nodes={snapshot?.elements} />
            </div>
          </div>
        )}

        {activeTab === 'console' && (
          <div>
            <span className="text-[10px] text-[#00f0ff] uppercase tracking-widest font-bold block mb-2">Console Output</span>
            <div className="bg-[#0a0a0f] border border-[#1e1e2e] p-2">
              <ConsoleLog entries={consoleEntries} />
            </div>
          </div>
        )}

        {activeTab === 'dialog' && (
          <DialogBox dialog={dialog} onRespond={(action, text) => {
            // ponytail: dialog response via socket — wire when backend emits dialog events
            console.log('dialog respond', action, text)
          }} />
        )}

        {/* Screenshot */}
        {screenshot && (
          <div>
            <span className="text-[10px] text-[#00f0ff] uppercase tracking-widest font-bold block mb-2">Visual Snapshot</span>
            <img src={`data:image/png;base64,${screenshot}`} alt="page screenshot"
              className="w-full border border-[#1e1e2e] bg-[#0a0a0f]" />
          </div>
        )}

        {/* Actions */}
        <div className="border-t border-[#1e1e2e] pt-3 flex gap-2">
          <button onClick={onClose}
            className="flex items-center gap-1 bg-[#1e1e2e] hover:bg-[#2a2a3a] border border-[#1e1e2e] text-[10px] text-white px-3 py-2 uppercase tracking-wider font-bold transition-all">
            <X size={10} /> Close
          </button>
        </div>
      </div>
    </SlidePanel>
  )
}
