import { useState, useMemo, useCallback } from 'react'
import SlidePanel from '../SlidePanel'
import { Code, Copy, Check, FileCode, Download, Sun, Moon, WrapText, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react'

const LANG_COLORS = {
  python: '#3572A5', javascript: '#f7df1e', typescript: '#3178c6', java: '#b07219',
  'c++': '#f34b7d', go: '#00ADD8', rust: '#dea584', ruby: '#701516', php: '#4F5D95',
  swift: '#ffac45', kotlin: '#F18E33', dart: '#00B4AB', html: '#e34c26', css: '#563d7c',
  sql: '#e38c00', shell: '#89e051', json: '#292929', yaml: '#cb171e',
}

const SYNTAX_THEMES = {
  dark: {
    bg: 'rgba(0,0,0,0.5)', gutterBg: 'rgba(255,255,255,0.03)',
    keyword: '#ff79c6', string: '#f1fa8c', comment: '#6272a4', number: '#bd93f9', decorator: '#50fa7b', builtin: '#8be9fd',
    text: '#e0e0e0', lineNum: '#495162',
  },
  light: {
    bg: '#f8f9fa', gutterBg: '#e9ecef',
    keyword: '#d63384', string: '#198754', comment: '#6c757d', number: '#fd7e14', decorator: '#20c997', builtin: '#0d6efd',
    text: '#212529', lineNum: '#adb5bd',
  },
}

const FONT_SIZES = [10, 11, 12, 13, 14, 15]

function detectLanguage(code, hint) {
  if (hint) return hint.toLowerCase()
  if (!code) return ''
  const c = code
  if (/def |import |class.*:|:\s*\n\s+/.test(c)) return 'python'
  if (/function |const |let |=>/.test(c)) return 'javascript'
  if (/interface |: string|: number|: boolean/.test(c)) return 'typescript'
  if (/public class|System\.out|@Override/.test(c)) return 'java'
  if (/fn |let mut|->/.test(c)) return 'rust'
  if (/package main|func /.test(c)) return 'go'
  if (/#include|int main/.test(c)) return 'c++'
  if (/require|gem |def |end\s*$/.test(c)) return 'ruby'
  if (/<\w+[^>]*>/.test(c) && /<\/\w+>/.test(c)) return 'html'
  if (/\{[^}]*:/.test(c) && !/def |function /.test(c)) return 'json'
  return ''
}

function highlightCode(code, lang, theme) {
  if (!code) return ''
  let escaped = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const t = theme
  const patterns = [
    { regex: /("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/g, cls: 'syn-string', color: t.string },
    { regex: /(\/\/.*$)/gm, cls: 'syn-comment', color: t.comment },
    { regex: /(\/\*[\s\S]*?\*\/)/g, cls: 'syn-comment', color: t.comment },
    { regex: /(`(?:[^`\\]|\\.)*`)/g, cls: 'syn-string', color: t.string },
    { regex: /\b(\d+\.?\d*)\b/g, cls: 'syn-number', color: t.number },
  ]

  if (lang === 'python') {
    patterns.push({ regex: /\b(def|class|import|from|return|if|else|elif|for|while|try|except|with|as|pass|None|True|False|and|or|not|in|is|lambda|yield|raise|break|continue|async|await)\b/g, cls: 'syn-keyword', color: t.keyword })
    patterns.push({ regex: /(@\w+)/g, cls: 'syn-decorator', color: t.decorator })
  } else if (lang === 'javascript' || lang === 'typescript') {
    patterns.push({ regex: /\b(function|const|let|var|return|if|else|for|while|class|import|export|default|from|async|await|try|catch|throw|new|this|typeof|instanceof|switch|case|break|continue|true|false|null|undefined|interface|type|extends|implements)\b/g, cls: 'syn-keyword', color: t.keyword })
  } else if (lang === 'go') {
    patterns.push({ regex: /\b(package|import|func|return|if|else|for|range|go|defer|select|case|switch|type|struct|interface|map|chan|var|const|true|false|nil)\b/g, cls: 'syn-keyword', color: t.keyword })
  } else if (lang === 'rust') {
    patterns.push({ regex: /\b(fn|let|mut|return|if|else|for|while|match|enum|struct|impl|trait|use|mod|pub|self|super|where|async|await|true|false|Some|None|Result|Ok|Err)\b/g, cls: 'syn-keyword', color: t.keyword })
  } else if (lang === 'java') {
    patterns.push({ regex: /\b(public|private|protected|class|interface|extends|implements|return|if|else|for|while|try|catch|throw|throws|new|this|super|static|final|void|int|String|boolean|null|true|false|import|package)\b/g, cls: 'syn-keyword', color: t.keyword })
  } else {
    patterns.push({ regex: /\b(function|class|import|return|if|else|for|while|try|catch|true|false|null|undefined|const|let|var|new|this|throw)\b/g, cls: 'syn-keyword', color: t.keyword })
  }

  for (const { regex, cls, color } of patterns) {
    escaped = escaped.replace(regex, `<span class="${cls}" style="color:${color}">$1</span>`)
  }
  return escaped
}

export default function CodePanel({ visible, data, onClose }) {
  const d = data?.result || data || {}
  const [theme, setTheme] = useState('dark')
  const [fontSize, setFontSize] = useState(11)
  const [wrapLines, setWrapLines] = useState(false)
  const [copied, setCopied] = useState(false)
  const [showFontPicker, setShowFontPicker] = useState(false)

  const language = detectLanguage(d.result || '', d.language)
  const lines = (d.result || '').split('\n')
  const themeColors = SYNTAX_THEMES[theme]
  const langColor = LANG_COLORS[language] || '#6b7280'

  const taskLabels = { generate: 'GENERATED', review: 'REVIEWED', debug: 'DEBUGGED', explain: 'EXPLAINED', refactor: 'REFACTORED', convert: 'CONVERTED' }

  const handleCopy = useCallback(async () => {
    if (!d.result) return
    try {
      await navigator.clipboard.writeText(d.result)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch { /* clip not avail */ }
  }, [d.result])

  const handleDownload = useCallback(() => {
    if (!d.result) return
    const ext = { python: 'py', javascript: 'js', typescript: 'ts', java: 'java', go: 'go', rust: 'rs', ruby: 'rb', html: 'html', css: 'css', json: 'json' }[language] || 'txt'
    const blob = new Blob([d.result], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `code.${ext}`; a.click()
    URL.revokeObjectURL(url)
  }, [d.result, language])

  const highlighted = useMemo(() => highlightCode(d.result, language, themeColors), [d.result, language, themeColors])

  return (
    <SlidePanel visible={visible} direction="bottom" title="CODE" icon={<Code size={11} />} accentColor="#22c55e" onClose={onClose} autoDismissMs={0}>
      <div className="agent-code-toolbar">
        <div className="agent-code-toolbar-left">
          <div className="agent-code-lang-badge" style={{ borderColor: langColor, color: langColor }}>
            <FileCode size={10} />
            {language || 'text'}
          </div>
          {d.task && taskLabels[d.task] && (
            <span className="agent-code-task-badge">{taskLabels[d.task]}</span>
          )}
          <span className="agent-code-line-count">{lines.length} lines · {d.result?.length || 0} chars</span>
        </div>
        <div className="agent-code-toolbar-right">
          <div className="agent-code-toolbar-group">
            <button className={`agent-code-tool-btn ${theme === 'dark' ? 'active' : ''}`} onClick={() => setTheme('dark')} title="Dark theme"><Moon size={10} /></button>
            <button className={`agent-code-tool-btn ${theme === 'light' ? 'active' : ''}`} onClick={() => setTheme('light')} title="Light theme"><Sun size={10} /></button>
          </div>
          <div className="agent-code-toolbar-group">
            <button className={`agent-code-tool-btn ${wrapLines ? 'active' : ''}`} onClick={() => setWrapLines(!wrapLines)} title="Toggle word wrap"><WrapText size={10} /></button>
          </div>
          <div className="agent-code-toolbar-group" style={{ position: 'relative' }}>
            <button className="agent-code-tool-btn" onClick={() => setShowFontPicker(!showFontPicker)} title="Font size">{fontSize}</button>
            {showFontPicker && (
              <div className="agent-code-font-picker">
                {FONT_SIZES.map(s => (
                  <button key={s} className={`agent-code-font-opt ${s === fontSize ? 'active' : ''}`} onClick={() => { setFontSize(s); setShowFontPicker(false) }}>{s}</button>
                ))}
              </div>
            )}
          </div>
          <div className="agent-code-toolbar-group">
            <button className="agent-code-tool-btn" onClick={handleDownload} title="Download"><Download size={10} /></button>
            <button className={`agent-code-tool-btn ${copied ? 'copied' : ''}`} onClick={handleCopy} title="Copy">
              {copied ? <Check size={10} /> : <Copy size={10} />}
            </button>
          </div>
        </div>
      </div>

      {!d.success && d.error && (
        <div className="agent-code-error"><AlertCircle size={14} />{d.error}</div>
      )}

      {d.result ? (
        <div className="agent-code-block-wrap" style={{ backgroundColor: themeColors.bg, borderColor: theme === 'dark' ? 'var(--border)' : '#dee2e6' }}>
          <div className="agent-code-gutter" style={{ backgroundColor: themeColors.gutterBg, borderRightColor: theme === 'dark' ? 'var(--border)' : '#dee2e6' }}>
            {lines.map((_, i) => (
              <div key={i} className="agent-code-line-num" style={{ color: themeColors.lineNum, fontSize }}>{i + 1}</div>
            ))}
          </div>
          <pre className="agent-code-content" style={{ color: themeColors.text, fontSize, whiteSpace: wrapLines ? 'pre-wrap' : 'pre', wordBreak: wrapLines ? 'break-all' : undefined }}
            dangerouslySetInnerHTML={{ __html: highlighted + '\n' }} />
        </div>
      ) : (
        <div className="agent-empty">No code output</div>
      )}

      {d.result && d.result.length > 5000 && (
        <div className="agent-code-truncate-notice">
          Large output ({d.result.length.toLocaleString()} chars) — scroll within the code block above
        </div>
      )}
    </SlidePanel>
  )
}
