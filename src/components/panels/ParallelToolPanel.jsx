import { useEffect, useRef } from 'react'
import SlidePanel from '../SlidePanel'
import { Loader, CheckCircle, XCircle, Zap } from 'lucide-react'

const STATUS_ICONS = {
  running: <Loader size={12} className="spin" />,
  done: <CheckCircle size={12} style={{ color: '#00fbfb' }} />,
  error: <XCircle size={12} style={{ color: '#ffb4ab' }} />,
}

function formatResult(result) {
  if (!result) return ''
  const text = result.result || result.error || result.detail || ''
  if (typeof text === 'string') return text.slice(0, 200)
  try { return JSON.stringify(text).slice(0, 200) } catch { return String(text) }
}

function ToolRow({ tool }) {
  const icon = STATUS_ICONS[tool.status] || STATUS_ICONS.running
  const resultText = tool.status === 'done' || tool.status === 'error'
    ? formatResult(tool.result)
    : null

  return (
    <div className="sp-parallel-tool-row">
      <div className="sp-parallel-tool-header">
        <span className="sp-parallel-tool-icon">{icon}</span>
        <span className="sp-parallel-tool-name">{tool.name}</span>
      </div>
      {tool.args && tool.status === 'running' && (
        <div className="sp-parallel-tool-args">
          {Object.entries(tool.args).slice(0, 3).map(([k, v]) => (
            <span key={k} className="sp-parallel-tool-arg">
              <span className="sp-parallel-tool-arg-key">{k}:</span>
              <span className="sp-parallel-tool-arg-val">
                {typeof v === 'object' ? JSON.stringify(v).slice(0, 60) : String(v).slice(0, 60)}
              </span>
            </span>
          ))}
        </div>
      )}
      {resultText && (
        <div className="sp-parallel-tool-result">{resultText}</div>
      )}
    </div>
  )
}

export default function ParallelToolPanel({ visible, tools, onClose }) {
  const timerRef = useRef(null)
  const allDone = tools.length > 0 && tools.every(t => t.status === 'done' || t.status === 'error')

  useEffect(() => {
    if (allDone && visible) {
      timerRef.current = setTimeout(onClose, 3000)
      return () => clearTimeout(timerRef.current)
    }
  }, [allDone, visible, onClose])

  const running = tools.filter(t => t.status === 'running').length
  const done = tools.filter(t => t.status === 'done' || t.status === 'error').length
  const title = allDone
    ? `TOOLS COMPLETE (${done})`
    : `EXECUTING (${running} running, ${done} done)`

  return (
    <SlidePanel
      visible={visible}
      direction="right"
      title={title}
      icon={<Zap size={11} />}
      accentColor={allDone ? '#00fbfb' : '#ffe2ab'}
      onClose={onClose}
      autoDismissMs={0}
    >
      <div className="sp-parallel-tool-list">
        {tools.map(tool => (
          <ToolRow key={tool.id} tool={tool} />
        ))}
      </div>
    </SlidePanel>
  )
}
