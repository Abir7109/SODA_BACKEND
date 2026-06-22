import { useState, useEffect, useRef } from 'react'
import socket from '../../services/SocketService'
import SlidePanel from '../SlidePanel'
import { X, Check, Circle, Loader, AlertTriangle } from 'lucide-react'

const STATUS_ICONS = {
  done: <Check size={12} className="text-[#00ff88]" />,
  running: <Loader size={12} className="text-[#00f0ff] animate-spin" />,
  failed: <AlertTriangle size={12} className="text-[#ff3355]" />,
  pending: <Circle size={12} className="text-[#444450]" />,
}

const STATUS_COLORS = {
  done: '#00ff88',
  running: '#00f0ff',
  failed: '#ff3355',
  pending: '#444450',
}

export default function TaskTerminalPanel({ visible, onClose }) {
  const [plan, setPlan] = useState(null)
  const scrollRef = useRef(null)

  useEffect(() => {
    if (!visible) return
    const onUpdate = (data) => setPlan(data)
    const onClear = (d) => {
      if (d && d.panel === 'task_terminal') {
        setPlan(null)
        onClose()
      }
    }
    socket.on('task_plan_update', onUpdate)
    socket.on('close_panel', onClear)
    return () => {
      socket.off('task_plan_update', onUpdate)
      socket.off('close_panel', onClear)
    }
  }, [visible, onClose])

  const handleDismiss = () => {
    socket.emit('force_tool', { tool: 'cancel_plan', args: {} })
    setPlan(null)
    onClose()
  }

  const tasks = plan?.tasks || []
  const done = tasks.filter(t => t.status === 'done' || t.status === 'failed').length
  const total = tasks.length
  const progress = total > 0 ? (done / total) * 100 : 0

  return (
    <SlidePanel visible={visible} direction="left" title={plan?.title || 'TASK PLAN'}
      accentColor="#00f0ff" onClose={handleDismiss} autoDismissMs={0}>
      <div className="p-3 font-mono text-[#e0e0e0] select-none" style={{ minWidth: 240, maxWidth: 320 }}>
        {!plan ? (
          <div className="text-[10px] text-[#666680] text-center py-4">No active task plan.</div>
        ) : (
          <div className="space-y-3">
            {/* Header: status badge + dismiss */}
            <div className="flex items-center justify-between">
              <span className="text-[9px] text-[#666680] uppercase tracking-wider">
                Created · {plan.created_at ? plan.created_at.slice(0, 10) : ''}
              </span>
              <div className="flex items-center gap-2">
                <span className="text-[9px] px-1.5 py-0.5 border font-bold uppercase tracking-wider"
                  style={{
                    color: plan.status === 'completed' ? '#00ff88' : '#00f0ff',
                    borderColor: plan.status === 'completed' ? 'rgba(0,255,136,0.3)' : 'rgba(0,240,255,0.3)',
                  }}>
                  {plan.status === 'completed' ? 'done' : 'running'}
                </span>
                <button onClick={handleDismiss}
                  className="text-[#666680] hover:text-[#ff3355] transition-colors p-0.5"
                  title="Dismiss task plan">
                  <X size={13} />
                </button>
              </div>
            </div>

            {/* Progress bar */}
            <div className="relative h-1.5 bg-[#1e1e2e] rounded-none overflow-hidden">
              <div className="absolute inset-y-0 left-0 bg-[#00f0ff] transition-all duration-700 ease-out"
                style={{ width: `${progress}%`, opacity: 0.7 }} />
            </div>
            <div className="text-[9px] text-[#666680] -mt-2">{done}/{total} tasks complete</div>

            {/* Task list */}
            <div ref={scrollRef} className="space-y-1 max-h-[55vh] overflow-y-auto custom-scrollbar pr-1">
              {tasks.map((task) => (
                <div key={task.id}
                  className="flex items-start gap-2.5 p-2 border transition-all"
                  style={{
                    borderColor: task.status === 'running' ? 'rgba(0,240,255,0.3)' : '#1e1e2e',
                    backgroundColor: task.status === 'running' ? 'rgba(0,240,255,0.04)' : 'transparent',
                  }}>
                  <div className="mt-0.5 shrink-0">
                    {STATUS_ICONS[task.status] || STATUS_ICONS.pending}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[11px] text-white font-medium leading-relaxed">{task.title}</div>
                    {task.description && (
                      <div className="text-[9px] text-[#666680] mt-0.5 leading-relaxed">{task.description}</div>
                    )}
                    {task.result && task.status === 'done' && (
                      <div className="text-[9px] text-[#00ff88]/70 mt-0.5 leading-relaxed">{task.result}</div>
                    )}
                    {task.result && task.status === 'failed' && (
                      <div className="text-[9px] text-[#ff3355]/70 mt-0.5 leading-relaxed">{task.result}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Dismiss button at bottom */}
            <button onClick={handleDismiss}
              className="w-full py-2 text-[10px] font-bold uppercase tracking-wider
                bg-[#1e1e2e] hover:bg-[#2a2a3a] border border-[#2a2a3a]
                text-[#666680] hover:text-white transition-all">
              Dismiss Tasks
            </button>
          </div>
        )}
      </div>
    </SlidePanel>
  )
}
