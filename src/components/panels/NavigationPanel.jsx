import { useEffect, useRef, useState, useCallback } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'

const OBSTACLE_ICONS = { construction: '\uD83D\uDEA7', road_closed: '\uD83D\uDEAB', hazard: '\u26A0\uFE0F', traffic_signal: '\uD83D\uDEA6', barrier: '\uD83D\uDDD1\uFE0F', crossing: '\uD83D\uDEB6', obstacle: '\u26A0\uFE0F' }
const SEVERITY_COLORS = { high: '#ff3b3b', medium: '#ffaa00', low: '#00ffcc' }
const MODE_ICONS = { drive: '\uD83D\uDE97', walk: '\uD83D\uDEB6', bike: '\uD83D\uDEB2' }
const TRAFFIC_COLORS = { clear: { label: 'Clear', color: '#00ff88' }, light: { label: 'Light', color: '#88ff00' }, moderate: { label: 'Moderate', color: '#ffaa00' }, heavy: { label: 'Heavy', color: '#ff3b3b' } }

function formatDuration(mins) {
  const h = Math.floor(mins / 60)
  const m = Math.round(mins % 60)
  if (h > 0) return `${h}h ${m}m`
  return `${m} min`
}

function formatDistance(km) {
  if (km < 1) return `${Math.round(km * 1000)} m`
  return `${km.toFixed(1)} km`
}

export default function NavigationPanel({ data, onClose, socket }) {
  const mapContainer = useRef(null)
  const mapRef = useRef(null)
  const markersRef = useRef([])
  const [activeRoute, setActiveRoute] = useState(0)
  const [activeStep, setActiveStep] = useState(null)
  const [mapLoaded, setMapLoaded] = useState(false)
  const [is3D, setIs3D] = useState(true)
  const [showObstacles, setShowObstacles] = useState(true)

  const best = data?.best_route || data?.routes?.[0]
  const routes = data?.routes || []
  const obstacles = data?.obstacles || []
  const origin = data?.origin || {}
  const destination = data?.destination || {}
  const mode = data?.mode || 'drive'

  const _fitBounds = useCallback((map) => {
    if (!origin.lat || !destination.lat) return
    const bounds = new maplibregl.LngLatBounds()
    bounds.extend([origin.lon, origin.lat])
    bounds.extend([destination.lon, destination.lat])
    if (best?.geometry?.coordinates) {
      best.geometry.coordinates.forEach(coord => bounds.extend(coord))
    }
    map.fitBounds(bounds, { padding: { top: 80, bottom: 80, left: 80, right: 80 }, duration: 1500 })
  }, [origin, destination, best])

  const _drawRoutes = useCallback((map) => {
    routes.forEach((route, idx) => {
      const isActive = idx === activeRoute
      const sourceId = `route-${idx}`
      const layerId = `route-layer-${idx}`
      const casingId = `route-casing-${idx}`
      if (!route.geometry) return
      if (map.getLayer(layerId)) map.removeLayer(layerId)
      if (map.getLayer(casingId)) map.removeLayer(casingId)
      if (map.getSource(sourceId)) map.removeSource(sourceId)
      map.addSource(sourceId, { type: 'geojson', data: { type: 'Feature', geometry: route.geometry } })
      map.addLayer({
        id: casingId, type: 'line', source: sourceId,
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: { 'line-color': isActive ? '#003366' : '#111', 'line-width': isActive ? 12 : 7, 'line-opacity': isActive ? 0.9 : 0.4 }
      })
      map.addLayer({
        id: layerId, type: 'line', source: sourceId,
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: {
          'line-color': isActive ? (route.traffic_score === 'heavy' ? '#ff3b3b' : route.traffic_score === 'moderate' ? '#ffaa00' : '#00d4ff') : '#445566',
          'line-width': isActive ? 7 : 3, 'line-opacity': isActive ? 1 : 0.4,
          'line-dasharray': isActive ? [] : [3, 2]
        }
      })
      map.on('click', layerId, () => setActiveRoute(idx))
      map.on('mouseenter', layerId, () => { map.getCanvas().style.cursor = 'pointer' })
      map.on('mouseleave', layerId, () => { map.getCanvas().style.cursor = '' })
    })
  }, [routes, activeRoute])

  const _drawObstacles = useCallback((map) => {
    if (!showObstacles) return
    obstacles.forEach((obs) => {
      const el = document.createElement('div')
      el.style.cssText = `width:28px;height:28px;background:${SEVERITY_COLORS[obs.severity] || '#ffaa00'}22;border:2px solid ${SEVERITY_COLORS[obs.severity] || '#ffaa00'};border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;cursor:pointer;box-shadow:0 0 12px ${SEVERITY_COLORS[obs.severity]}88;transition:transform 0.2s`
      el.innerHTML = OBSTACLE_ICONS[obs.type] || '\u26A0\uFE0F'
      el.addEventListener('mouseenter', () => { el.style.transform = 'scale(1.3)' })
      el.addEventListener('mouseleave', () => { el.style.transform = 'scale(1)' })
      const popup = new maplibregl.Popup({ offset: 25, className: 'soda-popup' }).setHTML(
        `<div style="background:#0a0f1a;color:#e0e8f0;padding:10px;border-radius:8px;border:1px solid ${SEVERITY_COLORS[obs.severity]}55;font-family:'Space Grotesk',sans-serif;font-size:12px;min-width:150px">
          <div style="font-weight:700;margin-bottom:4px;color:${SEVERITY_COLORS[obs.severity]}">${OBSTACLE_ICONS[obs.type] || ''} ${obs.type.replace('_', ' ').toUpperCase()}</div>
          <div style="opacity:0.8">${obs.description}</div>
          <div style="margin-top:6px;padding:2px 6px;background:${SEVERITY_COLORS[obs.severity]}22;border-radius:4px;display:inline-block;font-size:10px;color:${SEVERITY_COLORS[obs.severity]}">${obs.severity.toUpperCase()} SEVERITY</div>
        </div>`
      )
      new maplibregl.Marker({ element: el }).setLngLat([obs.lon, obs.lat]).setPopup(popup).addTo(map)
    })
  }, [obstacles, showObstacles])

  const _placeMarkers = useCallback((map) => {
    markersRef.current.forEach(m => m.remove())
    markersRef.current = []
    const createMarker = (lat, lon, label, color, icon) => {
      const el = document.createElement('div')
      el.style.cssText = 'display:flex;flex-direction:column;align-items:center;cursor:default'
      el.innerHTML = `<div style="width:40px;height:40px;background:${color}22;border:2px solid ${color};border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:20px;box-shadow:0 0 20px ${color}88">${icon}</div>
        <div style="margin-top:4px;background:#0a0f1a;border:1px solid ${color}55;padding:2px 8px;border-radius:12px;font-size:10px;color:${color};font-family:'Space Grotesk',sans-serif;white-space:nowrap;max-width:120px;overflow:hidden;text-overflow:ellipsis">${label}</div>`
      const marker = new maplibregl.Marker({ element: el }).setLngLat([lon, lat]).addTo(map)
      markersRef.current.push(marker)
    }
    if (origin.lat && origin.lon) createMarker(origin.lat, origin.lon, 'Start', '#00ff88', '\uD83D\uDCCD')
    if (destination.lat && destination.lon) createMarker(destination.lat, destination.lon, destination.display_name?.split(',')[0] || 'Destination', '#ff6b9d', '\uD83C\uDFC1')
  }, [origin, destination])

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return
    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          osm: { type: 'raster', tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'], tileSize: 256, attribution: '\u00A9 OpenStreetMap contributors', maxzoom: 19 }
        },
        layers: [{
          id: 'osm-tiles', type: 'raster', source: 'osm',
          paint: { 'raster-opacity': 1, 'raster-hue-rotate': 200, 'raster-brightness-min': 0, 'raster-brightness-max': 0.4, 'raster-saturation': -0.3 }
        }]
      },
      center: [origin.lon || 0, origin.lat || 0],
      zoom: 12, pitch: is3D ? 45 : 0, bearing: 0, antialias: true
    })
    map.addControl(new maplibregl.NavigationControl(), 'top-right')
    map.addControl(new maplibregl.ScaleControl(), 'bottom-right')
    map.on('load', () => {
      setMapLoaded(true)
      _drawRoutes(map)
      _drawObstacles(map)
      _placeMarkers(map)
      _fitBounds(map)
    })
    mapRef.current = map
    return () => { map.remove(); mapRef.current = null }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return
    _drawRoutes(mapRef.current)
  }, [activeRoute, mapLoaded, _drawRoutes])

  const toggle3D = () => {
    setIs3D(prev => { const next = !prev; mapRef.current?.easeTo({ pitch: next ? 45 : 0, duration: 800 }); return next })
  }

  useEffect(() => {
    if (!socket) return
    const handleMapControl = (data) => {
      const map = mapRef.current
      if (!map) return
      switch (data.action) {
        case 'fly_to':
          map.flyTo({ center: [data.lon, data.lat], zoom: data.zoom || 15, pitch: 45, duration: 2000 })
          break
        case 'pin_location': {
          const el = document.createElement('div')
          el.style.cssText = `width:32px;height:32px;background:${data.color || '#00ffff'}22;border:2px solid ${data.color || '#00ffff'};border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px;box-shadow:0 0 16px ${data.color || '#00ffff'}88`
          el.innerHTML = '\uD83D\uDCCC'
          const popup = new maplibregl.Popup({ offset: 25 }).setText(data.label || '')
          const pin = new maplibregl.Marker({ element: el }).setLngLat([data.lon, data.lat]).setPopup(popup).addTo(map)
          popup.addTo(map)
          markersRef.current.push(pin)
          break
        }
        case 'highlight_step':
          setActiveStep(data.step_index)
          const step = routes[activeRoute]?.steps?.[data.step_index]
          if (step?.location) map.flyTo({ center: [step.location[0], step.location[1]], zoom: 16, pitch: 60, duration: 1500 })
          break
        case 'fit_route':
          _fitBounds(map)
          break
      }
    }
    socket.on('map_control', handleMapControl)
    return () => socket.off('map_control', handleMapControl)
  }, [socket, routes, activeRoute, _fitBounds])

  const handleStepClick = (step, idx) => {
    setActiveStep(idx)
    if (step.location && mapRef.current) mapRef.current.flyTo({ center: [step.location[0], step.location[1]], zoom: 17, pitch: 60, duration: 1200 })
  }

  const currentRoute = routes[activeRoute] || best
  const traffic = TRAFFIC_COLORS[currentRoute?.traffic_score] || TRAFFIC_COLORS.clear

  return (
    <div className="navigation-panel">
      <div className="nav-header">
        <div className="nav-title">
          <span className="nav-icon">{MODE_ICONS[mode]}</span>
          <div>
            <div className="nav-title-text">SODA Navigation</div>
            <div className="nav-subtitle">{origin.name || 'Origin'} \u2192 {destination.display_name?.split(',')[0] || 'Destination'}</div>
          </div>
        </div>
        <div className="nav-header-actions">
          <button className={`nav-btn ${is3D ? 'active' : ''}`} onClick={toggle3D} title="Toggle 3D view">3D</button>
          <button className={`nav-btn ${showObstacles ? 'active' : ''}`} onClick={() => setShowObstacles(p => !p)} title="Toggle obstacles">{'\u26A0\uFE0F'}</button>
          <button className="nav-close-btn" onClick={onClose}>{'\u2715'}</button>
        </div>
      </div>

      {currentRoute && (
        <div className="nav-summary-bar">
          <div className="nav-summary-stat"><span className="stat-icon">{MODE_ICONS[mode]}</span><span>{formatDistance(currentRoute.distance_km)}</span></div>
          <div className="nav-summary-stat"><span className="stat-icon">{'\u23F1'}</span><span>{formatDuration(currentRoute.duration_min)}</span></div>
          <div className="nav-summary-stat" style={{ color: traffic.color }}><span className="stat-icon">{'\uD83D\uDEA6'}</span><span>{traffic.label}</span></div>
          {currentRoute.obstacle_count > 0 && (
            <div className="nav-summary-stat" style={{ color: '#ffaa00' }}><span className="stat-icon">{'\uD83D\uDEA7'}</span><span>{currentRoute.obstacle_count} obstacle{currentRoute.obstacle_count > 1 ? 's' : ''}</span></div>
          )}
          {routes.length > 1 && (
            <div className="nav-route-switcher">
              {routes.map((r, idx) => (
                <button key={idx} className={`route-tab ${activeRoute === idx ? 'active' : ''}`} onClick={() => setActiveRoute(idx)}>
                  Route {idx + 1}{r.is_best && <span className="best-badge">Best</span>}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="nav-content">
        <div className="nav-map-container" ref={mapContainer} />
        {currentRoute?.steps && (
          <div className="nav-steps-panel">
            <div className="steps-header">Turn-by-Turn Directions<span className="steps-count">{currentRoute.steps.length} steps</span></div>
            <div className="steps-list">
              {currentRoute.steps.map((step, idx) => (
                <div key={idx} className={`step-item ${activeStep === idx ? 'active' : ''}`} onClick={() => handleStepClick(step, idx)}>
                  <div className="step-icon">{_getStepIcon(step.maneuver, step.modifier)}</div>
                  <div className="step-content">
                    <div className="step-instruction">{step.instruction}</div>
                    {step.distance_m > 0 && <div className="step-distance">{step.distance_m >= 1000 ? `${(step.distance_m / 1000).toFixed(1)} km` : `${step.distance_m} m`}</div>}
                  </div>
                  {activeStep === idx && <div className="step-active-indicator" />}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function _getStepIcon(maneuver, modifier) {
  const map = {
    'depart': '\uD83D\uDE80', 'arrive': '\uD83C\uDFC1',
    'turn-left': '\u21B0', 'turn-right': '\u21B1',
    'turn-sharp left': '\u2196', 'turn-sharp right': '\u2197',
    'continue': '\u2191', 'merge': '\u2935',
    'roundabout': '\uD83D\uDD04', 'fork-left': '\u2B05',
    'fork-right': '\u27A1', 'end of road': '\u26D4'
  }
  const key = modifier ? `${maneuver}-${modifier}` : maneuver
  return map[key] || map[maneuver] || '\u27A1'
}
