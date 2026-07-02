import { useState } from 'react'
import SlidePanel from '../SlidePanel'
import { Mail, Reply, ChevronDown, ChevronUp, Eye, EyeOff } from 'lucide-react'

export default function EmailPanel({ visible, data, onClose }) {
  const [expandedId, setExpandedId] = useState(null)
  const [replyTarget, setReplyTarget] = useState(null)
  const [setupGuide, setSetupGuide] = useState(false)

  if (!data) return null

  if (data.setup_instructions) {
    return (
      <SlidePanel visible={visible} direction="right" title="EMAIL SETUP" icon={<Mail size={11} />}
        accentColor="#00fbfb" onClose={onClose} autoDismissMs={0}>
        <div style={{ padding: '16px', fontSize: '12px', lineHeight: '1.6', color: '#c8c8c8', whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
          {data.setup_instructions}
        </div>
      </SlidePanel>
    )
  }

  if (data.error) {
    return (
      <SlidePanel visible={visible} direction="right" title="EMAIL" icon={<Mail size={11} />}
        accentColor="#ffb4ab" onClose={onClose} autoDismissMs={0}>
        <div style={{ padding: '16px', fontSize: '12px', color: '#ffb4ab', fontFamily: 'monospace' }}>{data.error}</div>
        {data.setup_instructions && (
          <button onClick={() => setSetupGuide(true)}
            style={{ margin: '8px 16px', padding: '6px 12px', background: 'transparent', border: '1px solid #00fbfb33', color: '#00fbfb', fontSize: '11px', fontFamily: 'monospace', cursor: 'pointer' }}>
            SHOW SETUP GUIDE
          </button>
        )}
        {setupGuide && (
          <div style={{ padding: '0 16px 16px', fontSize: '11px', color: '#c8c8c8', whiteSpace: 'pre-wrap', fontFamily: 'monospace', lineHeight: '1.5' }}>
            {data.setup_instructions}
          </div>
        )}
      </SlidePanel>
    )
  }

  const emails = data.emails || []
  const total = data.total || 0

  return (
    <SlidePanel visible={visible} direction="right" title={`EMAIL (${total})`} icon={<Mail size={11} />}
      accentColor="#00fbfb" onClose={onClose} autoDismissMs={0}>
      <div style={{ padding: emails.length === 0 ? '16px' : 0 }}>
        {emails.length === 0 && (
          <div style={{ color: '#888', fontSize: '12px', fontFamily: 'monospace', textAlign: 'center', padding: '32px 0' }}>
            No emails found
          </div>
        )}
        {emails.map((email, i) => (
          <div key={email.id || i} style={{
            borderBottom: '1px solid rgba(0, 251, 251, 0.08)',
            padding: '10px 14px',
            cursor: replyTarget === email.id ? 'default' : 'pointer',
            background: replyTarget === email.id ? 'rgba(0, 251, 251, 0.04)' : 'transparent',
          }}>
            <div onClick={() => setExpandedId(expandedId === email.id ? null : email.id)}
              style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ color: '#e0e0e0', fontSize: '12px', fontFamily: 'monospace', fontWeight: '600', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {email.from || 'Unknown'}
                </div>
                <div style={{ color: '#c8c8c8', fontSize: '11px', fontFamily: 'monospace', marginTop: '2px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {email.subject || '(no subject)'}
                </div>
                <div style={{ color: '#888', fontSize: '9px', fontFamily: 'monospace', marginTop: '2px' }}>
                  {email.date || ''}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '4px', flexShrink: 0, marginTop: '2px' }}>
                <button onClick={(e) => { e.stopPropagation(); setReplyTarget(replyTarget === email.id ? null : email.id) }}
                  style={{ background: 'none', border: 'none', color: '#00fbfb', opacity: 0.5, cursor: 'pointer', padding: '2px' }}
                  title="Reply">
                  <Reply size={12} />
                </button>
                <span style={{ color: '#888', opacity: 0.4 }}>
                  {expandedId === email.id ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                </span>
              </div>
            </div>

            {expandedId === email.id && (
              <div style={{ marginTop: '10px', padding: '8px', background: 'rgba(0, 0, 0, 0.2)', borderRadius: '2px' }}>
                <div style={{ color: '#a0a0a0', fontSize: '10px', fontFamily: 'monospace', marginBottom: '6px', lineHeight: '1.5', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {email.body || '(no content)'}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </SlidePanel>
  )
}
