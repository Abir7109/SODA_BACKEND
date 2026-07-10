import { useEffect, useRef } from 'react'
import socket from '../services/SocketService'

export default function CameraCapture() {
  const streamRef = useRef(null)
  const videoRef = useRef(null)
  const canvasRef = useRef(null)

  async function acquireCamera() {
    if (streamRef.current) return streamRef.current
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { min: 640, ideal: 1280, max: 1920 },
        height: { min: 480, ideal: 720, max: 1080 },
        facingMode: { ideal: 'environment' },
      }
    })
    streamRef.current = stream
    const video = document.createElement('video')
    video.srcObject = stream
    video.setAttribute('playsinline', '')
    await video.play()
    videoRef.current = video
    const canvas = document.createElement('canvas')
    canvasRef.current = canvas
    return stream
  }

  function releaseCamera() {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
    videoRef.current = null
    canvasRef.current = null
  }

  async function captureFrame() {
    const canvas = canvasRef.current
    const video = videoRef.current
    if (!canvas || !video || video.readyState < 2) return null
    canvas.width = video.videoWidth || 1280
    canvas.height = video.videoHeight || 720
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0)
    return new Promise(resolve => {
      canvas.toBlob(blob => {
        if (!blob) { resolve(null); return }
        const reader = new FileReader()
        reader.onloadend = () => resolve(reader.result.split(',')[1])
        reader.readAsDataURL(blob)
      }, 'image/jpeg', 0.85)
    })
  }

  async function captureOneFrame() {
    await acquireCamera()
    const video = videoRef.current
    if (!video) return null
    if (video.readyState < 2) {
      await new Promise(resolve => { video.onloadeddata = resolve })
    }
    const b64 = await captureFrame()
    releaseCamera()
    return b64
  }

  useEffect(() => {
    let active = true

    const onRequestFaceFrame = async (data) => {
      if (!active) return
      const b64 = await captureOneFrame()
      if (b64) socket.emit('face_frame_response', { id: data.id, image: b64 })
    }

    const onRequestFrame = async (data) => {
      if (!active) return
      const b64 = await captureOneFrame()
      if (b64) socket.emit('frame_response', { id: data.id, image: b64 })
    }

    socket.on('request_face_frame', onRequestFaceFrame)
    socket.on('request_frame', onRequestFrame)

    return () => {
      active = false
      releaseCamera()
      socket.off('request_face_frame', onRequestFaceFrame)
      socket.off('request_frame', onRequestFrame)
    }
  }, [])

  return null
}
