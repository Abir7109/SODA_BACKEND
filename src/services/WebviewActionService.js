class WebviewActionService {
  constructor() {
    this.webviews = new Map()
    this.pendingActions = new Map()
  }

  register(id, webviewElement) {
    this.webviews.set(id, webviewElement)
  }

  unregister(id) {
    this.webviews.delete(id)
    this.pendingActions.delete(id)
  }

  get(id) {
    return this.webviews.get(id) || null
  }

  getAllIds() {
    return Array.from(this.webviews.keys())
  }

  async executeJS(id, code) {
    const el = this.webviews.get(id)
    if (!el) return { error: 'webview_not_found' }
    // Electron <webview> guest — full JS control
    if (el.tagName === 'WEBVIEW') {
      try {
        const result = await el.executeJavaScript(code)
        return { success: true, result }
      } catch (err) {
        return { error: err.message }
      }
    }
    // Browser <iframe> fallback — same-origin only
    try {
      const origin = el.src ? new URL(el.src).origin : ''
      if (origin && origin !== window.location.origin) {
        return { error: 'cross-origin iframe: JS control needs the Electron window' }
      }
      const result = el.contentWindow?.eval(code)
      return { success: true, result }
    } catch (err) {
      return { error: err.message }
    }
  }

  async click(id, selector) {
    return this.executeJS(id, `
      (() => {
        const el = document.querySelector(${JSON.stringify(selector)});
        if (!el) return { error: 'element not found' };
        el.scrollIntoView({ block: 'center', behavior: 'instant' });
        el.click();
        return { success: true, tag: el.tagName, text: (el.textContent || '').trim().slice(0, 100) };
      })()
    `)
  }

  async type(id, selector, text) {
    return this.executeJS(id, `
      (() => {
        const el = document.querySelector(${JSON.stringify(selector)});
        if (!el) return { error: 'element not found' };
        el.focus();
        el.value = '';
        el.value = ${JSON.stringify(text)};
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        return { success: true };
      })()
    `)
  }

  async scroll(id, selector, x, y) {
    if (selector) {
      return this.executeJS(id, `
        (() => {
          const el = document.querySelector(${JSON.stringify(selector)});
          if (!el) return { error: 'element not found' };
          el.scrollBy({ left: ${x || 0}, top: ${y || 200}, behavior: 'smooth' });
          return { success: true, scrollX: el.scrollLeft, scrollY: el.scrollTop };
        })()
      `)
    }
    const dy = y || 200
    return this.executeJS(id, `
      (() => {
        const scrollEl = document.scrollingElement || document.documentElement;
        scrollEl.scrollBy({ left: ${x || 0}, top: ${dy}, behavior: 'smooth' });
        return { success: true, scrollX: window.scrollX, scrollY: window.scrollY };
      })()
    `)
  }

  async scrollTo(id, selector) {
    if (!selector) return this.scroll(id, null, 0, 500)
    return this.executeJS(id, `
      (() => {
        const el = document.querySelector(${JSON.stringify(selector)});
        if (!el) return { error: 'element not found' };
        el.scrollIntoView({ block: 'center', behavior: 'smooth' });
        return { success: true, tag: el.tagName };
      })()
    `)
  }

  async getContent(id) {
    return this.executeJS(id, `
      (() => {
        const scrollEl = document.scrollingElement || document.documentElement;
        return {
          title: document.title,
          url: location.href,
          text: document.body.innerText.slice(0, 8000),
          scrollY: scrollEl.scrollTop,
          scrollHeight: scrollEl.scrollHeight,
          clientHeight: scrollEl.clientHeight,
          links: Array.from(document.querySelectorAll('a[href]')).map(a => ({
            text: (a.textContent || '').trim().slice(0, 80),
            href: a.href
          })).slice(0, 50)
        }
      })()
    `)
  }

  async getUrl(id) {
    const el = this.webviews.get(id)
    if (!el) return { error: 'webview_not_found' }
    try {
      if (el.tagName === 'WEBVIEW') {
        return { success: true, result: { url: el.getURL?.() || '', title: el.getTitle?.() || '' } }
      }
      return { success: true, result: { url: el.src || '', title: el.title || '' } }
    } catch { return { error: 'failed to get url' } }
  }

  async goBack(id) {
    return this.executeJS(id, `window.history.back(); { success: true }`)
  }

  async goForward(id) {
    return this.executeJS(id, `window.history.forward(); { success: true }`)
  }

  async navigate(id, url) {
    const el = this.webviews.get(id)
    if (!el) return { error: 'webview_not_found' }
    if (el.tagName === 'WEBVIEW') {
      return new Promise((resolve) => {
        const handler = () => {
          el.removeEventListener('did-finish-load', handler)
          resolve({ success: true, url: el.getURL(), title: el.getTitle() })
        }
        el.addEventListener('did-finish-load', handler)
        el.loadURL(url)
      })
    }
    el.src = url
    return new Promise((resolve) => {
      const handler = () => {
        el.removeEventListener('load', handler)
        resolve({ success: true, url: el.src })
      }
      el.addEventListener('load', handler)
    })
  }

  async waitForLoad(id, timeoutMs = 10000) {
    const el = this.webviews.get(id)
    if (!el) return { error: 'webview_not_found' }
    const isWebview = el.tagName === 'WEBVIEW'
    const evt = isWebview ? 'did-finish-load' : 'load'
    if (isWebview && el.isLoading && !el.isLoading()) return { success: true, loaded: true }
    return new Promise((resolve) => {
      const timer = setTimeout(() => resolve({ success: false, error: 'timeout' }), timeoutMs)
      const handler = () => {
        clearTimeout(timer)
        el.removeEventListener(evt, handler)
        resolve({ success: true, url: isWebview ? el.getURL() : el.src })
      }
      el.addEventListener(evt, handler)
    })
  }
}

const instance = new WebviewActionService()
export default instance
