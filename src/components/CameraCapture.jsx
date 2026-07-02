import { useEffect, useRef } from 'react'
import socket from '../services/SocketService'

const CAPTURE_INTERVAL = 5000

export default function CameraCapture() {
  const streamRef = useRef(null)
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const timerRef = useRef(null)

  useEffect(() => {
    let active = true

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

    async function sendFrame() {
      if (!active) return
      const b64 = await captureFrame()
      if (b64 && socket.connected) {
        socket.emit('video_frame', { image: b64 })
      }
    }

    async function start() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { min: 640, ideal: 1280, max: 1920 },
            height: { min: 480, ideal: 720, max: 1080 },
            facingMode: { ideal: 'environment' },
          }
        })
        if (!active) { stream.getTracks().forEach(t => t.stop()); return }
        streamRef.current = stream

        const video = document.createElement('video')
        video.srcObject = stream
        video.setAttribute('playsinline', '')
        video.play()
        videoRef.current = video

        const canvas = document.createElement('canvas')
        canvasRef.current = canvas

        video.onloadeddata = async () => {
          await sendFrame()
          timerRef.current = setInterval(sendFrame, CAPTURE_INTERVAL)
        }
      } catch (err) {
        console.warn('[CameraCapture] Camera unavailable:', err?.message)
      }
    }

    const onRequestFaceFrame = async (data) => {
      const b64 = await captureFrame()
      if (b64) socket.emit('face_frame_response', { id: data.id, image: b64 })
    }

    const onRequestFrame = async (data) => {
      const b64 = await captureFrame()
      if (b64) socket.emit('frame_response', { id: data.id, image: b64 })
    }

    socket.on('request_face_frame', onRequestFaceFrame)
    socket.on('request_frame', onRequestFrame)
    start()

    return () => {
      active = false
      if (timerRef.current) clearInterval(timerRef.current)
      if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop())
      socket.off('request_face_frame', onRequestFaceFrame)
      socket.off('request_frame', onRequestFrame)
    }
  }, [])

  return null
}
