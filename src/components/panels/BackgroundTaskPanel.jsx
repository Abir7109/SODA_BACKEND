import { useState, useEffect } from 'react'
import { Terminal, X, Play, CheckCircle, XCircle, Clock } from 'lucide-react'
import SlidePanel from '../SlidePanel'

function TaskCard({ task }) {
  const [expanded, setExpanded] = useState(true)
  const isRunning = task.phase === 'running'
  const isDone = task.phase === 'completed' || task.phase === 'failed'
  const isFailed = task.phase === 'failed'

  return (
    <div className={`border ${isFailed ? 'border-[#ff3355]/40' : isRunning ? 'border-[#00f0ff]/40' : 'border-[#00ff88]/40'} bg-[#0a0a0f]`}>
      <div className="p-3 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            {isRunning ? <Play size={10} className="text-[#00f0ff] animate-pulse shrink-0" />
              : isDone ? <CheckCircle size={10} className={`${isFailed ? 'text-[#ff3355]' : 'text-[#00ff88]'} shrink-0`} />
              : <Clock size={10} className="text-[#666680] shrink-0" />}
            <div className="text-[10px] text-white font-bold truncate">{task.prompt?.substring(0, 60)}...</div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className={`text-[8px] uppercase tracking-wider font-bold px-1 py-0.5 ${isRunning ? 'text-[#00f0ff] bg-[#00f0ff]/10' : isFailed ? 'text-[#ff3355] bg-[#ff3355]/10' : 'text-[#00ff88] bg-[#00ff88]/10'}`}>
              {task.phase}
            </span>
            <span className="text-[8px] text-[#666680]">{task.elapsed?.toFixed(0) || '0'}s</span>
          </div>
        </div>
        {task.exit_code !== null && (
          <div className="text-[8px] text-[#666680] mt-1">Exit code: {task.exit_code}</div>
        )}
        {isRunning && (
          <div className="mt-2 h-1 bg-[#1e1e2e] overflow-hidden">
            <div className="h-full bg-[#00f0ff] animate-pulse w-3/4" style={{ animationDuration: '2s' }} />
          </div>
        )}
      </div>
      {expanded && task.output && (
        <div className="border-t border-[#1e1e2e] bg-[#050508] p-2">
          <pre className="text-[9px] text-[#b0b0cc] font-mono whitespace-pre-wrap max-h-[200px] overflow-y-auto custom-scrollbar leading-relaxed">
            {task.output}
          </pre>
        </div>
      )}
    </div>
  )
}

export default function BackgroundTaskPanel({ visible, data, onClose }) {
  const [tasks, setTasks] = useState([])
  const [socketEvents, setSocketEvents] = useState([])

  useEffect(() => {
    if (data?.tasks) setTasks(data.tasks)
  }, [data])

  useEffect(() => {
    if (!visible) return
    const socket = window._sodaSocket
    if (!socket) return
    const handler = (eventData) => {
      if (eventData?.task_id) {
        setTasks(prev => {
          const idx = prev.findIndex(t => t.task_id === eventData.task_id)
          if (idx >= 0) {
            const next = [...prev]
            next[idx] = { ...next[idx], ...eventData }
            return next
          }
          return [...prev, eventData]
        })
      }
    }
    socket.on('bg_task_status', handler)
    return () => socket.off('bg_task_status', handler)
  }, [visible])

  return (
    <SlidePanel visible={visible} direction="right" title="BACKGROUND TASKS" icon={<Terminal size={11} />}
      accentColor="#00f0ff" onClose={onClose} autoDismissMs={0}>
      <div className="p-4 space-y-3 font-mono text-[#e0e0e0] select-none custom-scrollbar" style={{ maxHeight: 'calc(100vh - 60px)', overflowY: 'auto' }}>
        {tasks.length === 0 ? (
          <div className="text-[#666680] text-[10px] text-center py-8 italic">No background tasks running</div>
        ) : (
          <div className="space-y-2">
            {tasks.map(t => <TaskCard key={t.task_id} task={t} />)}
          </div>
        )}
        <div className="flex gap-2 border-t border-[#1e1e2e] pt-3">
          <button onClick={onClose}
            className="flex items-center gap-1 text-[#666680] hover:text-white text-[10px] px-2 transition-all ml-auto">
            <X size={10} /> Close
          </button>
        </div>
      </div>
    </SlidePanel>
  )
}
