import { useState, useEffect } from 'react'

const STORAGE_KEY = 'soda-location'

function loadSaved() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

export default function LocationSettings({ socket, onClose }) {
  const [city, setCity] = useState('')
  const [status, setStatus] = useState('idle')
  const [saved, setSaved] = useState(loadSaved)

  const handleSet = async () => {
    const q = city.trim()
    if (!q) return
    setStatus('geocoding')
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(q)}&format=json&limit=1&accept-language=en`,
        { headers: { 'User-Agent': 'SODA-HUD/2.0' } }
      )
      const data = await res.json()
      if (!data || !data.length) { setStatus('notfound'); return }
      const { lat, lon, display_name } = data[0]
      const location = { lat: parseFloat(lat), lon: parseFloat(lon), name: display_name }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(location))
      setSaved(location)
      if (socket?.connected) socket.emit('live_location', { lat: location.lat, lon: location.lon })
      setStatus('saved')
    } catch {
      setStatus('error')
    }
  }

  const handleClear = () => {
    localStorage.removeItem(STORAGE_KEY)
    setSaved(null)
    setCity('')
    setStatus('idle')
  }

  const statusMsg = status === 'geocoding' ? 'Looking up city…' :
    status === 'notfound' ? 'City not found' :
    status === 'error' ? 'Geocoding failed' :
    status === 'saved' ? `Saved: ${saved?.name?.split(',')[0]}` : ''

  return (
    <div className="location-settings">
      <p className="location-settings-desc">
        Set your location manually so navigation knows where you are.
      </p>
      {saved && (
        <div className="location-settings-current">
          <span className="location-settings-label">Current location</span>
          <span className="location-settings-name">{saved.name?.split(',').slice(0,3).join(',')}</span>
        </div>
      )}
      <div className="location-settings-input-row">
        <input
          className="location-settings-input"
          type="text"
          placeholder="e.g. New Delhi, India"
          value={city}
          onChange={e => setCity(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSet()}
        />
        <button className="location-settings-btn" onClick={handleSet} disabled={status === 'geocoding'}>
          {status === 'geocoding' ? '…' : 'Set'}
        </button>
      </div>
      {statusMsg && (
        <p className="location-settings-status">
          {statusMsg}
        </p>
      )}
      {saved && (
        <button className="location-settings-clear" onClick={handleClear}>
          Clear saved location
        </button>
      )}
    </div>
  )
}
