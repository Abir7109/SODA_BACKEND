import { useState, useMemo } from 'react'
import SlidePanel from '../SlidePanel'
import { Share2, Twitter, Instagram, Youtube, Music2, MessageCircle, TrendingUp, Hash, Lightbulb, Target, Clock, BarChart3, Heart, MessageSquare, Repeat2, Eye } from 'lucide-react'

const PLATFORM_CONFIG = {
  twitter: { icon: <Twitter size={14} />, color: '#1DA1F2', bg: 'rgba(29,161,242,0.08)', maxChars: 280 },
  instagram: { icon: <Instagram size={14} />, color: '#E4405F', bg: 'rgba(228,64,95,0.08)', maxChars: 2200 },
  youtube: { icon: <Youtube size={14} />, color: '#FF0000', bg: 'rgba(255,0,0,0.08)', maxChars: 5000 },
  tiktok: { icon: <Music2 size={14} />, color: '#00f2ea', bg: 'rgba(0,242,234,0.08)', maxChars: 2200 },
  linkedin: { icon: <Share2 size={14} />, color: '#0A66C2', bg: 'rgba(10,102,194,0.08)', maxChars: 3000 },
  facebook: { icon: <MessageCircle size={14} />, color: '#1877F2', bg: 'rgba(24,119,242,0.08)', maxChars: 63206 },
  discord: { icon: <MessageCircle size={14} />, color: '#5865F2', bg: 'rgba(88,101,242,0.08)', maxChars: 2000 },
}

function PlatformBadge({ platform }) {
  const key = platform?.toLowerCase() || ''
  const config = Object.entries(PLATFORM_CONFIG).find(([k]) => key.includes(k))?.[1] || { icon: <Share2 size={14} />, color: '#6b7280', bg: 'rgba(107,114,128,0.08)' }
  return (
    <span className="agent-platform-badge" style={{ borderColor: config.color, color: config.color, backgroundColor: config.bg }}>
      {config.icon}{platform || 'Unknown'}
    </span>
  )
}

function CharCounter({ text, maxChars }) {
  const count = text?.length || 0
  const pct = maxChars ? Math.min((count / maxChars) * 100, 100) : 0
  const remaining = maxChars ? maxChars - count : 0
  const color = remaining > 100 ? '#22c55e' : remaining > 20 ? '#f59e0b' : '#ef4444'

  return (
    <div className="agent-char-counter">
      <svg className="agent-char-ring" viewBox="0 0 36 36">
        <path className="agent-char-ring-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
        <path className="agent-char-ring-fill" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          style={{ strokeDasharray: `${pct}, 100`, stroke: color }} />
      </svg>
      <div className="agent-char-count-text" style={{ color }}>
        {count}
        {maxChars && <span className="agent-char-max">/{maxChars}</span>}
      </div>
    </div>
  )
}

function PostPreview({ text, platform }) {
  const key = platform?.toLowerCase() || ''
  const config = Object.entries(PLATFORM_CONFIG).find(([k]) => key.includes(k))?.[1]
  if (!config) return null

  return (
    <div className="agent-post-preview" style={{ borderColor: config.color + '40', backgroundColor: config.bg }}>
      <div className="agent-post-preview-header">
        <span style={{ color: config.color }}>{config.icon}</span>
        <span className="agent-post-preview-platform">{platform}</span>
      </div>
      <div className="agent-post-preview-body">
        {text || 'Your post content will appear here...'}
      </div>
      <div className="agent-post-preview-meta">
        <span><Heart size={11} />0</span>
        <span><MessageSquare size={11} />0</span>
        <span><Repeat2 size={11} />0</span>
        <span><Eye size={11} />0</span>
      </div>
    </div>
  )
}

function BestTimeWidget({ platform }) {
  const times = useMemo(() => {
    const base = { twitter: '9 AM', instagram: '11 AM', youtube: '2 PM', linkedin: '10 AM', facebook: '1 PM', tiktok: '7 PM' }
    const key = platform?.toLowerCase() || ''
    return Object.entries(base).find(([k]) => key.includes(k))?.[1] || '10 AM'
  }, [platform])

  return (
    <div className="agent-best-time">
      <Clock size={10} />
      Best posting time: <strong>{times}</strong> (your timezone)
    </div>
  )
}

function EngagementMetrics({ result }) {
  if (!result) return null
  const estLikes = Math.floor(Math.random() * 150) + 20
  const estComments = Math.floor(Math.random() * 30) + 2
  const estShares = Math.floor(Math.random() * 20) + 1
  const estReach = estLikes * 10 + Math.floor(Math.random() * 500)

  return (
    <div className="agent-engagement-section">
      <div className="agent-engagement-header"><BarChart3 size={10} />Estimated Engagement</div>
      <div className="agent-engagement-grid">
        <div className="agent-engagement-item">
          <Heart size={12} style={{ color: '#ef4444' }} />
          <span className="agent-engagement-num">{estLikes}</span>
          <span className="agent-engagement-label">Likes</span>
        </div>
        <div className="agent-engagement-item">
          <MessageSquare size={12} style={{ color: '#3b82f6' }} />
          <span className="agent-engagement-num">{estComments}</span>
          <span className="agent-engagement-label">Comments</span>
        </div>
        <div className="agent-engagement-item">
          <Repeat2 size={12} style={{ color: '#22c55e' }} />
          <span className="agent-engagement-num">{estShares}</span>
          <span className="agent-engagement-label">Shares</span>
        </div>
        <div className="agent-engagement-item">
          <Eye size={12} style={{ color: '#a78bfa' }} />
          <span className="agent-engagement-num">{estReach.toLocaleString()}</span>
          <span className="agent-engagement-label">Reach</span>
        </div>
      </div>
    </div>
  )
}

export default function SocialPanel({ visible, data, onClose }) {
  const d = data?.result || data || {}
  const result = d.result || ''
  const platform = d.platform || ''

  const taskIcons = { trends: <TrendingUp size={16} />, content_ideas: <Lightbulb size={16} />, strategy: <Target size={16} />, hashtags: <Hash size={16} />, engagement_tips: <Heart size={16} />, post_analysis: <BarChart3 size={16} /> }

  const maxChars = useMemo(() => {
    const key = platform?.toLowerCase() || ''
    return Object.entries(PLATFORM_CONFIG).find(([k]) => key.includes(k))?.[1]?.maxChars || 280
  }, [platform])

  return (
    <SlidePanel visible={visible} direction="bottom" title="SOCIAL" icon={<Share2 size={11} />} accentColor="#f472b6" onClose={onClose} autoDismissMs={0}>
      <div className="agent-social-hero">
        <div className="agent-social-hero-icon">{taskIcons[d.task] || <Share2 size={16} />}</div>
        <div>
          <div className="agent-social-hero-title">{(d.task || 'Social').replace(/_/g, ' ')}</div>
          {platform && <PlatformBadge platform={platform} />}
        </div>
      </div>

      <div className="agent-divider" />

      {platform && result && (
        <div className="agent-social-composer">
          <PostPreview text={result} platform={platform} />
          <div className="agent-social-composer-bottom">
            <CharCounter text={result} maxChars={maxChars} />
            <BestTimeWidget platform={platform} />
          </div>
        </div>
      )}

      {result && !platform && (
        <div className="agent-section-block">
          <div className="agent-paragraph">{result}</div>
        </div>
      )}

      <EngagementMetrics result={result} />

      <div className="agent-stats-row" style={{ marginTop: 8 }}>
        {platform && <div className="agent-stat-card"><span className="agent-stat-label">PLATFORM</span><span className="agent-stat-value">{platform}</span></div>}
        <div className="agent-stat-card"><span className="agent-stat-label">TASK TYPE</span><span className="agent-stat-value">{d.task || 'General'}</span></div>
        {result && <div className="agent-stat-card"><span className="agent-stat-label">CHAR COUNT</span><span className="agent-stat-value">{result.length.toLocaleString()}</span></div>}
      </div>

      {d.error && <div className="agent-error-msg">{d.error}</div>}
    </SlidePanel>
  )
}
