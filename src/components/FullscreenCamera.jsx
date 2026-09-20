import { useRef, useEffect, useCallback, useState } from 'react'

const FRAME_INTERVAL = 2000 // ms between frames sent to backend

export default function FullscreenCamera({ socket, onClose }) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const frameTimerRef = useRef(null)
  const canvasRef = useRef(null)
  const facingRef = useRef('user')
  const onCloseRef = useRef(onClose)
  const [facing, setFacing] = useState('user')
  const [active, setActive] = useState(false)

  // Keep latest onClose without re-triggering effects (App re-renders often)
  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  const stopCamera = useCallback(() => {
    if (frameTimerRef.current) {
      clearInterval(frameTimerRef.current)
      frameTimerRef.current = null
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
    setActive(false)
  }, [])

  const handleClose = useCallback(() => {
    stopCamera()
    // Tell backend so Gemini stops receiving frames
    if (socket?.connected) socket.emit('camera_fullscreen_close', {})
    if (onCloseRef.current) onCloseRef.current()
  }, [socket, stopCamera])

  const startCamera = useCallback(async (mode = 'user') => {
    try {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop())
        streamRef.current = null
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { min: 640, ideal: 1280, max: 1920 },
          height: { min: 480, ideal: 720, max: 1080 },
          facingMode: { ideal: mode },
        }
      })
      streamRef.current = stream
      setActive(true)
      if (videoRef.current) {
        videoRef.current.srcObject = stream
      }
    } catch (err) {
      console.error('[FULLSCREEN CAMERA] getUserMedia failed:', err)
      // No camera available — close the view
      if (onCloseRef.current) onCloseRef.current()
    }
  }, [])

  const captureFrame = useCallback(() => {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas || !socket?.connected || video.readyState < 2) return
    canvas.width = video.videoWidth || 1280
    canvas.height = video.videoHeight || 720
    const ctx = canvas.getContext('2d')
    if (facingRef.current === 'user') {
      // Mirror to match what the user sees on screen
      ctx.translate(canvas.width, 0)
      ctx.scale(-1, 1)
    }
    ctx.drawImage(video, 0, 0)
    canvas.toBlob((blob) => {
      if (!blob || !socket?.connected) return
      const reader = new FileReader()
      reader.onloadend = () => {
        const b64 = reader.result.split(',')[1]
        socket.emit('camera_frame', { image: b64 })
      }
      reader.readAsDataURL(blob)
    }, 'image/jpeg', 0.7)
  }, [socket])

  const switchCamera = useCallback(() => {
    const next = facingRef.current === 'user' ? 'environment' : 'user'
    facingRef.current = next
    setFacing(next)
    startCamera(next)
  }, [startCamera])

  useEffect(() => {
    startCamera('user')
    // First frame after 600ms warm-up, then continuous feed
    const firstFrameTimer = setTimeout(() => captureFrame(), 600)
    frameTimerRef.current = setInterval(captureFrame, FRAME_INTERVAL)
    return () => {
      clearTimeout(firstFrameTimer)
      stopCamera()
    }
  }, [startCamera, captureFrame, stopCamera])

  // Backend-driven controls: switch (camera_control switch) and close
  useEffect(() => {
    if (!socket) return
    const onSwitch = () => switchCamera()
    const onCloseEvent = () => {
      stopCamera()
      if (onCloseRef.current) onCloseRef.current()
    }
    socket.on('camera_switch', onSwitch)
    socket.on('camera_fullscreen_close', onCloseEvent)
    socket.on('camera_close', onCloseEvent)
    return () => {
      socket.off('camera_switch', onSwitch)
      socket.off('camera_fullscreen_close', onCloseEvent)
      socket.off('camera_close', onCloseEvent)
    }
  }, [socket, switchCamera, stopCamera])

  return (
    <div className="fullscreen-camera">
      <canvas ref={canvasRef} style={{ display: 'none' }} />
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="fsc-video"
        style={{ transform: facing === 'user' ? 'scaleX(-1)' : 'none' }}
      />
      {!active && (
        <div className="fsc-error">CAMERA UNAVAILABLE</div>
      )}
      <button className="fsc-close" onClick={handleClose} title="Close camera">
        ✕ CLOSE
      </button>
      <button className="fsc-switch" onClick={switchCamera} title="Switch camera">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
          <circle cx="12" cy="13" r="4" />
        </svg>
      </button>
      <div className="fsc-label">
        <span className="fsc-dot" />
        Camera On
      </div>
    </div>
  )
}
