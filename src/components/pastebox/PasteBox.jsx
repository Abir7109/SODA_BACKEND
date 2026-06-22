import { useState, useCallback } from 'react'
import socket from '../../services/SocketService'

export default function PasteBox({ id }) {
  const [text, setText] = useState('')

  const handleSubmit = useCallback(() => {
    const trimmed = text.trim()
    if (!trimmed) return
    socket.emit('pastebox_content', { text: trimmed })
    setText('')
  }, [text])

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      handleSubmit()
    }
  }, [handleSubmit])

  const charCount = text.length

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: 0 }}>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Paste or type content here..."
        style={{
          flex: 1,
          width: '100%',
          background: 'rgba(0,0,0,0.3)',
          border: 'none',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          color: '#e0e0e0',
          fontFamily: "'Courier New', monospace",
          fontSize: 13,
          lineHeight: 1.6,
          padding: '14px 16px',
          resize: 'none',
          outline: 'none',
          letterSpacing: '0.3px',
        }}
      />
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '8px 14px', background: 'rgba(0,0,0,0.15)',
      }}>
        <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', fontFamily: 'monospace', letterSpacing: 1 }}>
          {charCount} CHARS
        </span>
        <button
          onClick={handleSubmit}
          disabled={!text.trim()}
          style={{
            background: text.trim() ? 'rgba(0,255,136,0.1)' : 'rgba(255,255,255,0.03)',
            border: `1px solid ${text.trim() ? 'rgba(0,255,136,0.3)' : 'rgba(255,255,255,0.06)'}`,
            color: text.trim() ? '#00ff88' : 'rgba(255,255,255,0.2)',
            padding: '5px 18px',
            fontSize: 11,
            fontFamily: 'monospace',
            letterSpacing: 2,
            cursor: text.trim() ? 'pointer' : 'default',
            transition: 'all 0.2s',
          }}
        >
          ▸ SUBMIT
        </button>
      </div>
    </div>
  )
}
