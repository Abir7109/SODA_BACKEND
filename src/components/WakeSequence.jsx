import { useRef, useEffect } from 'react'
import gsap from 'gsap'

export default function WakeSequence({ active, onComplete }) {
  const overlayRef = useRef(null)
  const scan1Ref = useRef(null)
  const scan2Ref = useRef(null)
  const scan3Ref = useRef(null)
  const barRef = useRef(null)
  const titleRef = useRef(null)
  const statusRef = useRef(null)
  const bracketTLRef = useRef(null)
  const bracketTRRef = useRef(null)
  const bracketBLRef = useRef(null)
  const bracketBRRef = useRef(null)
  const ringRef = useRef(null)
  const onlineRef = useRef(null)

  useEffect(() => {
    if (!active) return

    const ctx = gsap.context(() => {
      const tl = gsap.timeline({
        onComplete: () => onComplete?.(),
      })

      const ov = overlayRef.current
      const s1 = scan1Ref.current
      const s2 = scan2Ref.current
      const s3 = scan3Ref.current
      const bar = barRef.current
      const title = titleRef.current
      const status = statusRef.current
      const bTL = bracketTLRef.current
      const bTR = bracketTRRef.current
      const bBL = bracketBLRef.current
      const bBR = bracketBRRef.current
      const ring = ringRef.current
      const online = onlineRef.current

      gsap.set([s1, s2, s3, bar, title, status, bTL, bTR, bBL, bBR, ring, online], { autoAlpha: 0 })
      gsap.set(s1, { y: '-100%' })
      gsap.set(s2, { y: '-100%' })
      gsap.set(s3, { y: '-100%' })
      gsap.set(bTL, { scaleX: 0, scaleY: 0 })
      gsap.set(bTR, { scaleX: 0, scaleY: 0 })
      gsap.set(bBL, { scaleX: 0, scaleY: 0 })
      gsap.set(bBR, { scaleX: 0, scaleY: 0 })
      gsap.set(bar, { scaleX: 0 })
      gsap.set(ring, { scale: 0, opacity: 0.5 })
      gsap.set(online, { opacity: 0 })

      // Overlay fade in
      tl.to(ov, { autoAlpha: 0.3, duration: 0.15, ease: 'power2.out' })

      // Scan lines (staggered)
      tl.to(s1, { autoAlpha: 1, y: '100vh', duration: 0.5, ease: 'power1.inOut' }, 0.08)
      tl.to(s2, { autoAlpha: 1, y: '100vh', duration: 0.55, ease: 'power1.inOut' }, 0.12)
      tl.to(s3, { autoAlpha: 0.5, y: '100vh', duration: 0.6, ease: 'power1.inOut' }, 0.16)

      // Progress bar
      tl.to(bar, { autoAlpha: 1, scaleX: 1, duration: 0.7, ease: 'power3.out', transformOrigin: '0% 50%' }, 0.15)

      // Title
      tl.to(title, { autoAlpha: 1, y: 0, duration: 0.35, ease: 'power2.out' }, 0.2)

      // Status text
      tl.to(status, { autoAlpha: 1, duration: 0.3, ease: 'power2.out' }, 0.35)
      tl.to(status, { duration: 0.2, ease: 'power1.inOut' }, 0.7)
      tl.to(status, { autoAlpha: 0, duration: 0.15, ease: 'power2.in' }, 0.75)
      tl.set(status, { textContent: '' })

      // Crossfade to "ALL SYSTEMS ONLINE"
      tl.to(online, { autoAlpha: 1, duration: 0.3, ease: 'power2.out' }, 0.8)

      // HUD corner brackets
      tl.to(bTL, { autoAlpha: 1, scaleX: 1, duration: 0.25, ease: 'power2.out', transformOrigin: '0% 0%' }, 0.5)
      tl.to(bTL, { scaleY: 1, duration: 0.2, ease: 'power2.out', transformOrigin: '0% 0%' }, 0.55)
      tl.to(bTR, { autoAlpha: 1, scaleX: 1, duration: 0.25, ease: 'power2.out', transformOrigin: '100% 0%' }, 0.5)
      tl.to(bTR, { scaleY: 1, duration: 0.2, ease: 'power2.out', transformOrigin: '100% 0%' }, 0.55)
      tl.to(bBL, { autoAlpha: 1, scaleX: 1, duration: 0.25, ease: 'power2.out', transformOrigin: '0% 100%' }, 0.5)
      tl.to(bBL, { scaleY: 1, duration: 0.2, ease: 'power2.out', transformOrigin: '0% 100%' }, 0.55)
      tl.to(bBR, { autoAlpha: 1, scaleX: 1, duration: 0.25, ease: 'power2.out', transformOrigin: '100% 100%' }, 0.5)
      tl.to(bBR, { scaleY: 1, duration: 0.2, ease: 'power2.out', transformOrigin: '100% 100%' }, 0.55)

      // Ring pulse
      tl.to(ring, { autoAlpha: 1, scale: 3, opacity: 0, duration: 0.6, ease: 'power2.out' }, 0.85)

      // Hold
      tl.to({}, { duration: 0.15 }, 1.1)

      // Everything fades out
      tl.to([ov, s1, s2, s3, bar, title, status, bTL, bTR, bBL, bBR, ring, online],
        { autoAlpha: 0, duration: 0.25, ease: 'power2.in', stagger: 0.02 }, 1.25)
    }, overlayRef)

    return () => ctx.revert()
  }, [active, onComplete])

  if (!active) return null

  return (
    <div ref={overlayRef}
      className="fixed inset-0 z-[9999] pointer-events-none"
      style={{ opacity: 0, background: 'rgba(0,0,0,0.3)', willChange: 'opacity' }}>
      {/* Scan line 1 (cyan) */}
      <div ref={scan1Ref}
        className="absolute inset-x-0"
        style={{
          height: '2px', top: 0, willChange: 'transform',
          background: 'linear-gradient(to bottom, transparent, rgba(0,251,251,0.5), transparent)',
          boxShadow: '0 0 12px rgba(0,251,251,0.35)',
        }} />
      {/* Scan line 2 (blue, thinner) */}
      <div ref={scan2Ref}
        className="absolute inset-x-0"
        style={{
          height: '1px', top: 0, willChange: 'transform',
          background: 'linear-gradient(to bottom, transparent, rgba(0,100,255,0.4), transparent)',
          boxShadow: '0 0 8px rgba(0,100,255,0.25)',
        }} />
      {/* Scan line 3 (white, faint) */}
      <div ref={scan3Ref}
        className="absolute inset-x-0"
        style={{
          height: '1px', top: 0, willChange: 'transform',
          background: 'linear-gradient(to bottom, transparent, rgba(255,255,255,0.2), transparent)',
        }} />

      {/* Progress bar at bottom */}
      <div ref={barRef}
        className="absolute bottom-0 inset-x-0"
        style={{
          height: '1.5px', willChange: 'transform',
          background: 'linear-gradient(to right, rgba(0,251,251,0.8), rgba(0,100,255,0.4))',
          boxShadow: '0 0 8px rgba(0,251,251,0.3)',
        }} />

      {/* Title — top left */}
      <div ref={titleRef}
        className="absolute top-5 left-5"
        style={{
          fontFamily: "'Fira Code', 'JetBrains Mono', monospace",
          fontSize: '10px', letterSpacing: '0.2em',
          color: 'rgba(0,251,251,0.8)', opacity: 0, willChange: 'opacity, transform',
        }}>
        SODA v2.0
      </div>

      {/* Status — center */}
      <div ref={statusRef}
        className="absolute inset-0 flex items-center justify-center"
        style={{ fontFamily: "'Fira Code', 'JetBrains Mono', monospace", opacity: 0, willChange: 'opacity' }}>
        <span style={{ fontSize: '11px', letterSpacing: '0.3em', color: 'rgba(0,251,251,0.6)' }}>
          INITIALIZING
          <span className="inline-block" style={{ animation: 'ws-dot-pulse 0.8s steps(1) infinite' }}>.</span>
          <span className="inline-block" style={{ animation: 'ws-dot-pulse 0.8s steps(1) 0.15s infinite' }}>.</span>
          <span className="inline-block" style={{ animation: 'ws-dot-pulse 0.8s steps(1) 0.3s infinite' }}>.</span>
        </span>
      </div>

      {/* Online text — center */}
      <div ref={onlineRef}
        className="absolute inset-0 flex items-center justify-center"
        style={{ fontFamily: "'Fira Code', 'JetBrains Mono', monospace", opacity: 0, willChange: 'opacity' }}>
        <span style={{ fontSize: '11px', letterSpacing: '0.3em', color: 'rgba(0,251,251,0.85)' }}>
          ALL SYSTEMS ONLINE
        </span>
      </div>

      {/* HUD corner brackets (SVG) */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ willChange: 'opacity' }}>
        {/* Top-Left */}
        <path ref={bracketTLRef}
          d="M 30 55 L 30 30 L 55 30" fill="none" stroke="rgba(0,251,251,0.4)" strokeWidth="1.5" />
        {/* Top-Right */}
        <path ref={bracketTRRef}
          d="M -webkit-calc(100% - 30) 55 L -webkit-calc(100% - 30) 30 L -webkit-calc(100% - 55) 30"
          fill="none" stroke="rgba(0,251,251,0.4)" strokeWidth="1.5"
          style={{ transformOrigin: 'calc(100% - 15px) 15px' }} />
        {/* Bottom-Left */}
        <path ref={bracketBLRef}
          d="M 30 calc(100% - 55) L 30 calc(100% - 30) L 55 calc(100% - 30)"
          fill="none" stroke="rgba(0,251,251,0.4)" strokeWidth="1.5"
          style={{ transformOrigin: '15px calc(100% - 15px)' }} />
        {/* Bottom-Right */}
        <path ref={bracketBRRef}
          d="M calc(100% - 30) calc(100% - 55) L calc(100% - 30) calc(100% - 30) L calc(100% - 55) calc(100% - 30)"
          fill="none" stroke="rgba(0,251,251,0.4)" strokeWidth="1.5"
          style={{ transformOrigin: 'calc(100% - 15px) calc(100% - 15px)' }} />
      </svg>

      {/* Expanding ring */}
      <svg ref={ringRef}
        className="absolute w-48 h-48" style={{ top: '50%', left: '50%', margin: '-96px 0 0 -96px', willChange: 'transform, opacity' }}
        viewBox="0 0 200 200">
        <circle cx="100" cy="100" r="30" fill="none" stroke="rgba(0,251,251,0.4)" strokeWidth="1" />
      </svg>

      <style>{`
        @keyframes ws-dot-pulse {
          0% { opacity: 0; }
          50% { opacity: 1; }
          100% { opacity: 0; }
        }
      `}</style>
    </div>
  )
}
