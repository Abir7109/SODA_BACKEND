import { useRef, useEffect, useCallback } from 'react'

const FRAME_INTERVAL = 2000

export default function CameraWidget({ socket }) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const frameTimerRef = useRef(null)
  const canvasRef = useRef(null)

  const captureFrame = useCallback(() => {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas || !socket?.connected) return
    canvas.width = video.videoWidth || 640
    canvas.height = video.videoHeight || 480
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0)
    canvas.toBlob((blob) => {
      if (!blob || !socket?.connected) return
      const reader = new FileReader()
      reader.onloadend = () => {
        const b64 = reader.result.split(',')[1]
        socket.emit('camera_frame', { image: b64 })
      }
      reader.readAsDataURL(blob)
    }, 'image/jpeg', 0.85)
  }, [socket])

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { min: 640, ideal: 1280, max: 1920 },
          height: { min: 480, ideal: 720, max: 1080 },
          facingMode: { ideal: 'environment' },
        }
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
      }
    } catch (err) {
      console.error('[CAMERA] getUserMedia failed:', err)
    }
  }, [])

  const switchCamera = useCallback(() => {
    const video = videoRef.current
    if (!video) return
    const current = streamRef.current?.getVideoTracks()[0]?.getSettings().facingMode
    const newFacing = current === 'user' ? 'environment' : 'user'
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
    }
    navigator.mediaDevices.getUserMedia({
      video: {
        width: { min: 640, ideal: 1280, max: 1920 },
        height: { min: 480, ideal: 720, max: 1080 },
        facingMode: { ideal: newFacing },
      }
    }).then(stream => {
      streamRef.current = stream
      video.srcObject = stream
    }).catch(err => {
      console.error('[CAMERA] switch failed:', err)
    })
  }, [])

  const stopCamera = useCallback(() => {
    if (frameTimerRef.current) {
      clearInterval(frameTimerRef.current)
      frameTimerRef.current = null
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
  }, [])

  useEffect(() => {
    startCamera()
    const firstFrameTimer = setTimeout(() => captureFrame(), 500)
    frameTimerRef.current = setInterval(captureFrame, FRAME_INTERVAL)
    return () => {
      clearTimeout(firstFrameTimer)
      stopCamera()
    }
  }, [startCamera, captureFrame, stopCamera])

  useEffect(() => {
    if (!socket) return
    const onSwitch = () => switchCamera()
    const onClose = () => stopCamera()
    socket.on('camera_switch', onSwitch)
    socket.on('camera_close', onClose)
    return () => {
      socket.off('camera_switch', onSwitch)
      socket.off('camera_close', onClose)
    }
  }, [socket, switchCamera, stopCamera])

  return (
    <div className="camera-widget">
      <canvas ref={canvasRef} style={{ display: 'none' }} />
      <video ref={videoRef} autoPlay playsInline muted className="camera-video" />
      <div className="camera-controls">
        <button className="camera-btn camera-btn-capture" title="Capture" onClick={captureFrame}>
          <span className="camera-btn-icon" />
        </button>
        <button className="camera-btn camera-btn-switch" title="Switch camera" onClick={switchCamera}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
            <circle cx="12" cy="13" r="4" />
          </svg>
        </button>
      </div>
    </div>
  )
}
