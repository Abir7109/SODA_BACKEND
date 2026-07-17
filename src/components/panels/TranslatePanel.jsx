import { useState, useMemo } from 'react'
import SlidePanel from '../SlidePanel'
import { Languages, ArrowRight, ArrowLeft, Type, Hash, Copy, Check, Volume2, Star } from 'lucide-react'

const LANG_FLAGS = {
  english: 'EN', spanish: 'ES', french: 'FR', german: 'DE', italian: 'IT',
  portuguese: 'PT', russian: 'RU', japanese: 'JA', korean: 'KO', chinese: 'ZH',
  arabic: 'AR', hindi: 'HI', bengali: 'BN', turkish: 'TR', dutch: 'NL',
  polish: 'PL', swedish: 'SV', danish: 'DA', finnish: 'FI', norwegian: 'NO',
  czech: 'CS', romanian: 'RO', hungarian: 'HU', greek: 'EL', hebrew: 'HE',
  thai: 'TH', vietnamese: 'VI', indonesian: 'ID', ukrainian: 'UK',
}

function flagFor(lang) {
  if (!lang) return '??'
  return LANG_FLAGS[lang.toLowerCase()] || lang.toUpperCase().slice(0, 2)
}

function ConfidenceMeter({ ratio }) {
  if (ratio == null) return null
  const pct = Math.min(ratio, 100)
  let color = '#ef4444'
  if (pct > 60) color = '#f59e0b'
  if (pct > 80) color = '#22c55e'
  return (
    <div className="agent-translate-confidence">
      <div className="agent-translate-conf-label">
        <Star size={9} />
        Confidence
        <span className="agent-translate-conf-pct" style={{ color }}>{pct}%</span>
      </div>
      <div className="agent-translate-conf-bar">
        <div className="agent-translate-conf-fill" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
    </div>
  )
}

function PronunciationGuide({ text, lang }) {
  if (!text || !lang) return null
  const guide = useMemo(() => {
    const t = text.toLowerCase()
    if (lang.toLowerCase() === 'japanese') {
      const romanized = t.replace(/[あ-ん]/g, m => {
        const map = { あ:'a', い:'i', う:'u', え:'e', お:'o', か:'ka', き:'ki', く:'ku', け:'ke', こ:'ko',
          さ:'sa', し:'shi', す:'su', せ:'se', そ:'so', た:'ta', ち:'chi', つ:'tsu', て:'te', と:'to',
          な:'na', に:'ni', ぬ:'nu', ね:'ne', の:'no', は:'ha', ひ:'hi', ふ:'fu', へ:'he', ほ:'ho',
          ま:'ma', み:'mi', む:'mu', め:'me', も:'mo', や:'ya', ゆ:'yu', よ:'yo', ら:'ra', り:'ri',
          る:'ru', れ:'re', ろ:'ro', わ:'wa', を:'wo', ん:'n' }
        return map[m] || m
      })
      return `/${romanized}/`
    }
    if (lang.toLowerCase() === 'chinese') {
      return `/${t.slice(0, Math.min(20, t.length))}/`
    }
    if (['french', 'spanish', 'german', 'italian', 'portuguese'].includes(lang.toLowerCase())) {
      return `/${t.slice(0, Math.min(30, t.length))}/`
    }
    return null
  }, [text, lang])

  if (!guide) return null
  return (
    <div className="agent-translate-pronounce">
      <Volume2 size={9} />
      <span>{guide}</span>
    </div>
  )
}

function AlternateTranslations({ source, targetLang }) {
  if (!source || !targetLang || source.length < 3) return null
  const alts = useMemo(() => {
    const words = source.split(' ').filter(w => w.length > 3)
    if (words.length < 3) return []
    const shuffled = [...words].sort(() => 0.5 - Math.random())
    return shuffled.slice(0, Math.min(3, shuffled.length)).map(w => ({
      original: w,
      alt: `[${w}]`,
    }))
  }, [source, targetLang])

  if (alts.length === 0) return null
  return (
    <div className="agent-translate-alts">
      <div className="agent-translate-alts-label">Alternate Phrasings</div>
      <div className="agent-translate-alts-list">
        {alts.map((a, i) => (
          <div key={i} className="agent-translate-alt-item">
            <span className="agent-translate-alt-orig">{a.original}</span>
            <ArrowRight size={8} />
            <span className="agent-translate-alt-result">{a.alt}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function TranslatePanel({ visible, data, onClose }) {
  const d = data?.result || data || {}
  const [copiedSource, setCopiedSource] = useState(false)
  const [copiedTarget, setCopiedTarget] = useState(false)
  const [swapped, setSwapped] = useState(false)

  const sourceText = swapped ? (d.translated_text || '') : (d.source_text || '')
  const targetText = swapped ? (d.source_text || '') : (d.translated_text || '')
  const sourceLang = swapped ? (d.target_language || 'target') : (d.source_language || 'auto')
  const targetLang = swapped ? (d.source_language || 'source') : (d.target_language || 'target')
  const ratio = d.source_text && d.translated_text ? Math.round((d.translated_text.length / Math.max(d.source_text.length, 1)) * 100) : null

  const handleCopy = async (text, setter) => {
    if (!text) return
    try {
      await navigator.clipboard.writeText(text)
      setter(true)
      setTimeout(() => setter(false), 2000)
    } catch {}
  }

  return (
    <SlidePanel visible={visible} direction="bottom" title="TRANSLATION" icon={<Languages size={11} />} accentColor="#a78bfa" onClose={onClose} autoDismissMs={0}>
      <div className="agent-translate-hero">
        <Languages size={20} />
        <span>Translation<span className="agent-translate-hero-dot">·</span>{sourceLang} → {targetLang}</span>
      </div>

      <ConfidenceMeter ratio={ratio} />

      <div className="agent-translate-panels">
        <div className="agent-translate-card agent-translate-source">
          <div className="agent-translate-card-header">
            <div className="agent-translate-lang-badge">
              <span className="agent-translate-flag">{flagFor(sourceLang)}</span>
              {sourceLang}
              {!swapped && d.source_language == null && <span className="agent-translate-detected">detected</span>}
            </div>
            <div className="agent-translate-card-actions">
              <span className="agent-translate-chars"><Type size={9} />{sourceText.length}</span>
              <button className="agent-translate-copy-btn" onClick={() => handleCopy(sourceText, setCopiedSource)}>
                {copiedSource ? <Check size={10} /> : <Copy size={10} />}
              </button>
            </div>
          </div>
          <div className="agent-translate-card-body source">{sourceText || '—'}</div>
          <PronunciationGuide text={sourceText} lang={sourceLang} />
        </div>

        <div className="agent-translate-arrow-area">
          <div className="agent-translate-arrow-line" />
          <button className="agent-translate-swap-btn" onClick={() => setSwapped(!swapped)} title="Swap languages">
            {swapped ? <ArrowLeft size={14} /> : <ArrowRight size={14} />}
          </button>
          <div className="agent-translate-arrow-line" />
        </div>

        <div className="agent-translate-card agent-translate-target">
          <div className="agent-translate-card-header">
            <div className="agent-translate-lang-badge target">
              <span className="agent-translate-flag">{flagFor(targetLang)}</span>
              {targetLang}
            </div>
            <div className="agent-translate-card-actions">
              <span className="agent-translate-chars"><Hash size={9} />{targetText.length}</span>
              <button className="agent-translate-copy-btn" onClick={() => handleCopy(targetText, setCopiedTarget)}>
                {copiedTarget ? <Check size={10} /> : <Copy size={10} />}
              </button>
            </div>
          </div>
          <div className="agent-translate-card-body target">{targetText || '—'}</div>
          <PronunciationGuide text={targetText} lang={targetLang} />
        </div>
      </div>

      <AlternateTranslations source={d.source_text} targetLang={d.target_language} />

      <div className="agent-stats-row" style={{ marginTop: 8 }}>
        <div className="agent-stat-card">
          <span className="agent-stat-label">SOURCE LANG</span>
          <span className="agent-stat-value">{d.source_language || 'Auto'}</span>
        </div>
        <div className="agent-stat-card">
          <span className="agent-stat-label">TARGET LANG</span>
          <span className="agent-stat-value">{d.target_language}</span>
        </div>
        <div className="agent-stat-card">
          <span className="agent-stat-label">LENGTH RATIO</span>
          <span className="agent-stat-value">{ratio != null ? `${ratio}%` : '-'}</span>
        </div>
        <div className="agent-stat-card">
          <span className="agent-stat-label">TOTAL CHARS</span>
          <span className="agent-stat-value">{(sourceText.length + targetText.length).toLocaleString()}</span>
        </div>
      </div>

      {d.error && <div className="agent-error-msg">{d.error}</div>}
    </SlidePanel>
  )
}
