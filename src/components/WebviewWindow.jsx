import { useState, useRef, useEffect, useCallback } from 'react'

// Electron exposes window.electron → real <webview> guest with full control.
// In a plain browser (Netlify HUD) we fall back to <iframe> (sandboxed, no JS control).
const IS_ELECTRON = typeof window !== 'undefined' && !!window.electron

export default function WebviewWindow({ webviewRef, url, id }) {
  const [currentUrl, setCurrentUrl] = useState(url)
  const [canGoBack, setCanGoBack] = useState(false)
  const [canGoForward, setCanGoForward] = useState(false)
  const [loading, setLoading] = useState(true)
  const navRef = useRef(null)
  const urlInputRef = useRef(null)
  const iframeRef = useRef(null)

  useEffect(() => {
    if (!IS_ELECTRON) {
      webviewRef.current = iframeRef.current
      return
    }
    const wv = webviewRef.current
    if (!wv) return

    const onNav = (e) => {
      setCurrentUrl(e.url)
      try { setCanGoBack(wv.canGoBack()) } catch {}
      try { setCanGoForward(wv.canGoForward()) } catch {}
      setLoading(false)
    }
    const onStart = () => setLoading(true)
    const onStop = () => setLoading(false)

    wv.addEventListener('did-navigate', onNav)
    wv.addEventListener('did-navigate-in-page', onNav)
    wv.addEventListener('did-start-loading', onStart)
    wv.addEventListener('did-stop-loading', onStop)

    setLoading(true)

    return () => {
      wv.removeEventListener('did-navigate', onNav)
      wv.removeEventListener('did-navigate-in-page', onNav)
      wv.removeEventListener('did-start-loading', onStart)
      wv.removeEventListener('did-stop-loading', onStop)
    }
  }, [webviewRef])

  const handleBack = useCallback(() => {
    if (IS_ELECTRON) {
      const wv = webviewRef.current
      if (wv?.canGoBack?.()) wv.goBack()
    } else {
      try { iframeRef.current?.contentWindow?.history?.back() } catch {}
    }
  }, [webviewRef])

  const handleForward = useCallback(() => {
    if (IS_ELECTRON) {
      const wv = webviewRef.current
      if (wv?.canGoForward?.()) wv.goForward()
    } else {
      try { iframeRef.current?.contentWindow?.history?.forward() } catch {}
    }
  }, [webviewRef])

  const handleReload = useCallback(() => {
    if (IS_ELECTRON) {
      webviewRef.current?.reload?.()
    } else if (iframeRef.current) {
      iframeRef.current.src = iframeRef.current.src
    }
  }, [webviewRef])

  const handleUrlSubmit = useCallback((e) => {
    e.preventDefault()
    let inputUrl = urlInputRef.current?.value || currentUrl
    if (!/^https?:\/\//i.test(inputUrl)) inputUrl = 'https://' + inputUrl
    setCurrentUrl(inputUrl)
    if (IS_ELECTRON) {
      webviewRef.current?.loadURL?.(inputUrl)
    } else if (iframeRef.current) {
      iframeRef.current.src = inputUrl
    }
  }, [webviewRef, currentUrl])

  const handleIframeLoad = useCallback(() => {
    if (IS_ELECTRON) return
    try {
      const src = iframeRef.current?.contentWindow?.location?.href
      if (src && src !== 'about:blank') setCurrentUrl(src)
    } catch {}
    setLoading(false)
  }, [])

  if (!IS_ELECTRON && webviewRef) webviewRef.current = iframeRef.current

  const backDisabled = IS_ELECTRON && !canGoBack
  const fwdDisabled = IS_ELECTRON && !canGoForward

  return (
    <div className="webview-container" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="webview-toolbar" ref={navRef}
        style={{
          display: 'flex', alignItems: 'center', gap: 4, padding: '4px 6px',
          background: 'rgba(0,0,0,0.6)', borderBottom: '1px solid rgba(0,251,251,0.15)',
          flexShrink: 0,
        }}
      >
        <button className="webview-nav-btn" onClick={handleBack} disabled={backDisabled}
          style={{ opacity: backDisabled ? 0.3 : 1, cursor: backDisabled ? 'default' : 'pointer' }}>◀</button>
        <button className="webview-nav-btn" onClick={handleForward} disabled={fwdDisabled}
          style={{ opacity: fwdDisabled ? 0.3 : 1, cursor: fwdDisabled ? 'default' : 'pointer' }}>▶</button>
        <button className="webview-nav-btn" onClick={handleReload}
          style={{ cursor: 'pointer' }}>
          {loading ? '◉' : '⟳'}
        </button>
        <form onSubmit={handleUrlSubmit} style={{ flex: 1, margin: 0 }}>
          <input ref={urlInputRef} defaultValue={currentUrl}
            className="webview-url-input"
            style={{
              width: '100%', boxSizing: 'border-box',
              background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(0,251,251,0.2)',
              borderRadius: 3, color: '#c8c8c8', fontSize: 11, padding: '2px 6px',
              fontFamily: 'inherit', outline: 'none',
            }}
          />
        </form>
      </div>
      <div style={{ flex: 1, position: 'relative' }}>
        {IS_ELECTRON ? (
          <webview
            ref={webviewRef}
            src={url}
            style={{ width: '100%', height: '100%', border: 'none', background: '#fff' }}
            allowpopups
          />
        ) : (
          <iframe
            ref={iframeRef}
            src={url}
            title="webview"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
            style={{ width: '100%', height: '100%', border: 'none', background: '#fff' }}
            onLoad={handleIframeLoad}
          />
        )}
      </div>
    </div>
  )
}
