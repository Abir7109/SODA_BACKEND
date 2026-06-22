import { useEffect, useRef, useState, useCallback } from 'react'
import SlidePanel from '../SlidePanel'
import { Folder, FileText, Search, Plus } from 'lucide-react'
import socket from '../../services/SocketService'

function formatSize(bytes) {
  if (!bytes || bytes === 0) return '—'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

export default function FileBrowserPanel({ visible, path, items, success, searchQuery: initialSearch, onClose }) {
  const scrollRef = useRef(null)
  const [searchQuery, setSearchQuery] = useState(initialSearch || '')
  const searchInputRef = useRef(null)
  const [showNewFolder, setShowNewFolder] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const newFolderInputRef = useRef(null)

  useEffect(() => {
    setSearchQuery(initialSearch || '')
  }, [visible, path, initialSearch])

  useEffect(() => {
    if (!visible) return
    const handler = (data) => {
      const el = scrollRef.current
      if (!el) return
      if (data.action === 'bottom') {
        el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
      } else if (data.action === 'down') {
        el.scrollBy({ top: el.clientHeight * 0.5, behavior: 'smooth' })
      } else if (data.action === 'up') {
        el.scrollBy({ top: -el.clientHeight * 0.5, behavior: 'smooth' })
      } else if (data.action === 'stop') {
        el.style.overflow = 'hidden'
        el.style.overflow = ''
      }
    }
    socket.on('file_scroll', handler)
    return () => socket.off('file_scroll', handler)
  }, [visible])

  const filtered = items
    ? items.filter(item =>
        item.name.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : []

  const handleSearchKeyDown = (e) => {
    if (e.key === 'Escape') {
      setSearchQuery('')
      searchInputRef.current?.blur()
    }
  }

  const handleNewFolder = () => {
    setShowNewFolder(true)
    setTimeout(() => newFolderInputRef.current?.focus(), 50)
  }

  const handleNewFolderKeyDown = (e) => {
    if (e.key === 'Enter' && newFolderName.trim() && path) {
      const folderPath = path.replace(/\/$/, '') + '/' + newFolderName.trim()
      socket.emit('create_folder', { path: folderPath })
      setNewFolderName('')
      setShowNewFolder(false)
    }
    if (e.key === 'Escape') {
      setShowNewFolder(false)
      setNewFolderName('')
    }
  }

  return (
    <SlidePanel
      visible={visible}
      direction="bottom"
      title={path ? `FILES — ${path}` : 'FILE BROWSER'}
      icon={<Folder size={11} />}
      accentColor="#00fbfb"
      onClose={onClose}
      autoDismissMs={0}
      scrollToTop={true}
    >
      {items && items.length > 0 && (
        <div className="sp-search-bar">
          <Search size={11} className="sp-search-bar-icon" />
          <input
            ref={searchInputRef}
            className="sp-search-bar-input"
            type="text"
            placeholder="Search files..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            onKeyDown={handleSearchKeyDown}
            spellCheck={false}
          />
          {searchQuery && (
            <button className="sp-search-bar-clear" onClick={() => setSearchQuery('')}>✕</button>
          )}
          <button className="sp-new-folder-btn" onClick={handleNewFolder} title="New Folder">
            <Plus size={11} />
          </button>
        </div>
      )}

      {showNewFolder && path && (
        <div className="sp-new-folder-bar">
          <input
            ref={newFolderInputRef}
            className="sp-new-folder-input"
            type="text"
            placeholder="Folder name... (Enter to create)"
            value={newFolderName}
            onChange={e => setNewFolderName(e.target.value)}
            onKeyDown={handleNewFolderKeyDown}
            spellCheck={false}
          />
          <button className="sp-new-folder-cancel" onClick={() => { setShowNewFolder(false); setNewFolderName('') }}>✕</button>
        </div>
      )}

      <div ref={scrollRef}
        style={{ maxHeight: '35vh', overflowY: 'auto' }}>
        {!success ? (
          <div className="sp-empty">Could not list directory.</div>
        ) : !items || items.length === 0 ? (
          <div className="sp-empty">Directory is empty.</div>
        ) : filtered.length === 0 ? (
          <div className="sp-empty">No files match "{searchQuery}"</div>
        ) : (
          <div className="sp-file-list">
            {filtered.map((item, i) => (
              <div key={i} className="sp-file-item">
                <div className="sp-file-number">{item.number}</div>
                <div className="sp-file-icon">
                  {item.type === 'folder' ? <Folder size={13} /> : <FileText size={13} />}
                </div>
                <div className="sp-file-info">
                  <div className="sp-file-name">{item.name}</div>
                  <div className="sp-file-meta">
                    {item.type === 'folder' ? 'Folder' : formatSize(item.size)}
                    {item.modified ? ` · ${item.modified}` : ''}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {items && items.length > 0 && !searchQuery && (
        <div className="sp-search-prompt">
          Tell SODA which file to open (e.g., "open the first file")
        </div>
      )}
    </SlidePanel>
  )
}
