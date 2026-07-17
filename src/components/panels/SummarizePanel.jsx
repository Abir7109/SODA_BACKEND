import { useState, useMemo } from 'react'
import SlidePanel from '../SlidePanel'
import { FileText, Minimize2, BarChart3, Quote, TrendingUp, PieChart, Hash, AlertCircle } from 'lucide-react'

function CompressionBar({ original, summary }) {
  const origLen = original || 1
  const sumLen = summary || 0
  const ratio = Math.min(Math.round((1 - sumLen / origLen) * 100), 99)

  return (
    <div className="agent-compress-section">
      <div className="agent-compress-bar-wrap">
        <div className="agent-compress-bar-bg">
          <div className="agent-compress-bar-fill" style={{ width: `${ratio}%` }} />
          <div className="agent-compress-bar-marker" style={{ left: `${ratio}%` }} />
        </div>
      </div>
      <div className="agent-compress-stats">
        <div className="agent-compress-stat-item">
          <span className="agent-compress-stat-label">Original</span>
          <span className="agent-compress-stat-value">{origLen.toLocaleString()}</span>
          <span className="agent-compress-stat-unit">chars</span>
        </div>
        <div className="agent-compress-arrow">→</div>
        <div className="agent-compress-stat-item">
          <span className="agent-compress-stat-label">Summary</span>
          <span className="agent-compress-stat-value highlight">{sumLen.toLocaleString()}</span>
          <span className="agent-compress-stat-unit">chars</span>
        </div>
        <div className="agent-compress-pct-badge">-{ratio}%</div>
      </div>
    </div>
  )
}

function extractKeyPoints(text) {
  if (!text) return []
  const points = []
  const lines = text.split(/[.\n]+/).filter(l => l.trim().length > 25)
  for (const line of lines.slice(0, 8)) {
    const trimmed = line.trim()
    if (trimmed.length > 20) points.push(trimmed)
  }
  return points
}

function ReadabilityBar({ text }) {
  if (!text) return null
  const score = useMemo(() => {
    const words = text.split(/\s+/).filter(Boolean)
    const sentences = text.split(/[.!?]+/).filter(Boolean).length || 1
    const syllables = words.reduce((sum, w) => sum + Math.max(1, Math.floor(w.length / 3)), 0)
    return Math.min(100, Math.round(206.835 - 1.015 * (words.length / sentences) - 84.6 * (syllables / words.length)))
  }, [text])

  const label = score > 60 ? 'Easy to read' : score > 30 ? 'Moderate' : 'Complex'
  const color = score > 60 ? '#22c55e' : score > 30 ? '#f59e0b' : '#ef4444'

  return (
    <div className="agent-readability">
      <div className="agent-readability-header">
        <TrendingUp size={10} />
        Readability: {label}
        <span className="agent-readability-score" style={{ color }}>{score}</span>
      </div>
      <div className="agent-readability-bar">
        <div className="agent-readability-fill" style={{ width: `${score}%`, backgroundColor: color }} />
      </div>
    </div>
  )
}

function WordFrequencyBar({ words }) {
  const freq = useMemo(() => {
    if (!words) return []
    const map = {}
    const text = words.toLowerCase().replace(/[^a-z\s]/g, '')
    text.split(/\s+/).filter(w => w.length > 3).forEach(w => { map[w] = (map[w] || 0) + 1 })
    return Object.entries(map).sort((a, b) => b[1] - a[1]).slice(0, 8)
  }, [words])

  if (freq.length < 3) return null
  const maxFreq = Math.max(...freq.map(([, c]) => c), 1)

  return (
    <div className="agent-freq-section">
      <div className="agent-freq-header">
        <Hash size={10} />
        Word Frequency
      </div>
      <div className="agent-freq-list">
        {freq.map(([word, count], i) => (
          <div key={i} className="agent-freq-row">
            <span className="agent-freq-word">{word}</span>
            <div className="agent-freq-bar-bg">
              <div className="agent-freq-bar-fill" style={{ width: `${(count / maxFreq) * 100}%` }} />
            </div>
            <span className="agent-freq-count">{count}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function SentimentBar({ text }) {
  if (!text) return null
  const { positive, negative, neutral } = useMemo(() => {
    const pos = ['good', 'great', 'excellent', 'positive', 'success', 'benefit', 'improve', 'growth', 'opportunity', 'best', 'leading', 'innovation']
    const neg = ['bad', 'poor', 'negative', 'fail', 'crisis', 'risk', 'loss', 'decline', 'damage', 'threat', 'worst', 'danger']
    const words = text.toLowerCase().split(/\s+/)
    const p = words.filter(w => pos.includes(w)).length
    const n = words.filter(w => neg.includes(w)).length
    const total = words.length || 1
    return { positive: (p / total * 100).toFixed(0), negative: (n / total * 100).toFixed(0), neutral: (100 - (p + n) / total * 100).toFixed(0) }
  }, [text])

  return (
    <div className="agent-sentiment-section">
      <div className="agent-sentiment-header">
        <PieChart size={10} />
        Sentiment Analysis
      </div>
      <div className="agent-sentiment-bar">
        <div className="agent-sentiment-seg" style={{ width: `${positive}%`, backgroundColor: '#22c55e' }} title={`Positive ${positive}%`} />
        <div className="agent-sentiment-seg" style={{ width: `${neutral}%`, backgroundColor: '#6b7280' }} title={`Neutral ${neutral}%`} />
        <div className="agent-sentiment-seg" style={{ width: `${negative}%`, backgroundColor: '#ef4444' }} title={`Negative ${negative}%`} />
      </div>
      <div className="agent-sentiment-labels">
        <span style={{ color: '#22c55e' }}>Pos {positive}%</span>
        <span style={{ color: '#6b7280' }}>Neu {neutral}%</span>
        <span style={{ color: '#ef4444' }}>Neg {negative}%</span>
      </div>
    </div>
  )
}

export default function SummarizePanel({ visible, data, onClose }) {
  const d = data?.result || data || {}
  const [previewMode, setPreviewMode] = useState('summary')
  const summary = d.summary || ''
  const origLen = d.original_length || 0
  const style = d.style || 'normal'
  const keyPoints = extractKeyPoints(summary)

  const styleLabels = { concise: 'CONCISE', normal: 'STANDARD', detailed: 'DETAILED' }

  return (
    <SlidePanel visible={visible} direction="bottom" title="SUMMARY" icon={<FileText size={11} />} accentColor="#f59e0b" onClose={onClose} autoDismissMs={0}>
      <div className="agent-summary-hero">
        <div className="agent-summary-hero-icon"><FileText size={20} /></div>
        <div>
          <div className="agent-summary-hero-title">Text Summary</div>
          <div className="agent-summary-hero-badge">{styleLabels[style] || style.toUpperCase()}</div>
        </div>
      </div>

      <div className="agent-summary-mode-tabs">
        <button className={`agent-summary-mode-tab ${previewMode === 'summary' ? 'active' : ''}`} onClick={() => setPreviewMode('summary')}>Summary</button>
        <button className={`agent-summary-mode-tab ${previewMode === 'points' ? 'active' : ''}`} onClick={() => setPreviewMode('points')}>Key Points</button>
        <button className={`agent-summary-mode-tab ${previewMode === 'analytics' ? 'active' : ''}`} onClick={() => setPreviewMode('analytics')}>Analytics</button>
      </div>

      <div className="agent-divider" />

      {previewMode === 'summary' && (
        <>
          {origLen > 0 && <CompressionBar original={origLen} summary={summary.length} />}
          <div className="agent-summary-content">
            <div className="agent-summary-content-header"><Quote size={12} />Summary</div>
            {summary ? (
              <div className="agent-summary-text">{summary}</div>
            ) : (
              <div className="agent-empty">No summary content</div>
            )}
          </div>
        </>
      )}

      {previewMode === 'points' && (
        <div className="agent-summary-points">
          <div className="agent-summary-points-header"><BarChart3 size={12} />Key Points ({keyPoints.length})</div>
          {keyPoints.length > 0 ? (
            keyPoints.map((point, i) => (
              <div key={i} className="agent-summary-point">
                <span className="agent-summary-point-num">{i + 1}</span>
                <span className="agent-summary-point-text">{point}.</span>
              </div>
            ))
          ) : (
            <div className="agent-empty">Switch to Summary view to extract key points</div>
          )}
        </div>
      )}

      {previewMode === 'analytics' && (
        <div className="agent-summary-analytics">
          <ReadabilityBar text={summary} />
          <div className="agent-divider" />
          <SentimentBar text={summary} />
          <div className="agent-divider" />
          <WordFrequencyBar words={summary} />
        </div>
      )}

      {d.error && <div className="agent-error-msg">{d.error}</div>}
    </SlidePanel>
  )
}
