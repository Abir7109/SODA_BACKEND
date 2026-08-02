import { useEffect, useRef } from 'react'
import { animate, createTimeline } from 'animejs'

export default function NightWinddown({ active, onComplete }) {
  const overlayRef = useRef(null)
  const ring1Ref = useRef(null)
  const ring2Ref = useRef(null)
  const ring3Ref = useRef(null)
  const textRef = useRef(null)

  useEffect(() => {
    if (!active) return
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (prefersReduced) {
      const t = setTimeout(() => onComplete?.(), 3000)
      return () => clearTimeout(t)
    }

    const tl = createTimeline({ defaults: { ease: 'outExpo' } })

    tl.add(animate(overlayRef.current, { opacity: [0, 1], duration: 600 }), 0)

    tl.add(animate([ring1Ref.current, ring2Ref.current, ring3Ref.current], {
      opacity: [0, 0.55],
      scale: [0.4, 1],
      duration: 900,
    }), 0.3)

    tl.add(animate(textRef.current, {
      opacity: [0, 1],
      translateY: [14, 0],
      letterSpacing: ['0.5em', '0.3em'],
      duration: 800,
    }), 0.8)

    const rings = animate([ring1Ref.current, ring2Ref.current, ring3Ref.current], {
      scale: [1, 1.25],
      opacity: [0.55, 0],
      duration: 3200,
      ease: 'inOutSine',
      loop: true,
      delay: (el, i) => i * 400,
    })

    tl.add({ targets: {}, duration: 3200 }, 1.2)

    const finish = () => onComplete?.()
    const finishTimer = setTimeout(finish, 5600)

    return () => {
      tl.pause()
      tl.seek(0)
      rings.pause()
      clearTimeout(finishTimer)
    }
  }, [active, onComplete])

  if (!active) return null

  return (
    <div ref={overlayRef}
      className="fixed inset-0 z-[9999] pointer-events-none"
      style={{
        opacity: 0,
        background: 'radial-gradient(ellipse at center, rgba(10,10,25,0.92) 0%, rgba(4,8,11,0.98) 70%)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
      <svg className="absolute w-[420px] h-[420px]" style={{ top: '50%', left: '50%', margin: '-210px 0 0 -210px' }} viewBox="0 0 200 200">
        <circle ref={ring1Ref} cx="100" cy="100" r="42" fill="none" stroke="rgba(167,139,250,0.5)" strokeWidth="1" style={{ transformOrigin: '100px 100px' }} />
        <circle ref={ring2Ref} cx="100" cy="100" r="58" fill="none" stroke="rgba(0,251,251,0.35)" strokeWidth="1" style={{ transformOrigin: '100px 100px' }} />
        <circle ref={ring3Ref} cx="100" cy="100" r="74" fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth="1" style={{ transformOrigin: '100px 100px' }} />
      </svg>

      <div ref={textRef}
        className="absolute text-center"
        style={{
          fontFamily: "'Fira Code', 'JetBrains Mono', monospace",
          fontSize: '13px', letterSpacing: '0.3em',
          color: 'rgba(167,139,250,0.85)', opacity: 0,
          textShadow: '0 0 16px rgba(167,139,250,0.35)',
        }}>
        GOOD NIGHT, SIR
        <div className="db-winddown-sub">soda will be here when you wake</div>
      </div>
    </div>
  )
}
