import React, { useEffect, useRef, useMemo, useState } from 'react'
import { StyleSheet, Dimensions } from 'react-native'
import {
  Canvas,
  Circle,
  Path,
  Skia,
  RadialGradient,
  BlendMode,
  DashPathEffect,
  vec,
} from '@shopify/react-native-skia'
import { COLORS } from '../constants/colors'

const { width: SCREEN_WIDTH } = Dimensions.get('window')
const SIZE = Math.min(SCREEN_WIDTH * 0.55, 260)
const C = SIZE / 2
const R = SIZE * 0.35

export default function SodaOrb({ micLevel = 0, isSpeaking = false }) {
  const [tick, setTick] = useState(0)
  const s = useRef({
    time: 0, swirl1: 0, swirl2: 0, pulse: 0, smoothMic: 0, lastTime: 0,
  }).current

  useEffect(() => {
    let frame
    const loop = (now) => {
      if (s.lastTime === 0) s.lastTime = now
      const dt = Math.min(now - s.lastTime, 50) / 1000
      s.lastTime = now

      s.smoothMic += (micLevel - s.smoothMic) * 0.06
      const sm = s.smoothMic
      const speedMul = (isSpeaking ? 0.4 : 1.0) * (1.0 + sm * 1.5)
      s.time += dt * (0.8 + sm * 1.0)
      s.swirl1 += 0.85 * speedMul * dt
      s.swirl2 -= 1.65 * speedMul * dt
      s.pulse = Math.sin(s.time * 2.5) * 0.5 + 0.5

      setTick((n) => n + 1)
      frame = requestAnimationFrame(loop)
    }
    frame = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(frame)
  }, [micLevel, isSpeaking])

  const cc = isSpeaking ? COLORS.orbColors.speaking : COLORS.orbColors.neutral
  const bounce = 1.0 + s.smoothMic * 0.12 + 0.03 * Math.sin(s.time * 3)
  const ar = R * bounce
  const coreR = ar * (0.33 + s.pulse * 0.3 + s.smoothMic * 0.35)
  const coronaR = ar * 1.7

  const gasFlares = useMemo(
    () => Array.from({ length: 8 }, (_, i) => ({ angle: (i / 8) * Math.PI * 2, idx: i })),
    []
  )
  const fiberOffsets = useMemo(
    () => Array.from({ length: 8 }, (_, i) => (i / 8) * Math.PI * 2),
    []
  )

  const buildHaloPath = () => {
    const p = Skia.Path.Make()
    const rr = ar * 1.12
    for (let i = 0; i <= 90; i++) {
      const angle = (i / 90) * Math.PI * 2
      const wave =
        Math.sin(angle * 6 + s.time * 2) * 4 +
        Math.sin(angle * 3 + s.time * 1.3) * 2 +
        (isSpeaking ? Math.sin(angle * 8 + s.time * 3) * s.smoothMic * 18 : 0)
      const rrr = rr + wave
      const x = C + Math.cos(angle) * rrr
      const y = C + Math.sin(angle) * rrr
      if (i === 0) p.moveTo(x, y)
      else p.lineTo(x, y)
    }
    p.close()
    return p
  }

  const buildFiberPath = (offset) => {
    const p = Skia.Path.Make()
    const startAngle = offset + s.swirl2
    for (let j = 0; j <= 20; j++) {
      const t = j / 20
      const angle = startAngle + t * Math.PI * 1.5
      const rr = ar * (1 - t * 0.85)
      const x = C + Math.cos(angle) * rr
      const y = C + Math.sin(angle) * rr
      if (j === 0) p.moveTo(x, y)
      else p.lineTo(x, y)
    }
    return p
  }

  const fiberColor = isSpeaking ? 'rgba(168,85,247,0.4)' : 'rgba(0,251,251,0.3)'

  return (
    <Canvas style={styles.canvas}>
      {/* Layer 1: Corona */}
      <Circle cx={C} cy={C} r={coronaR}>
        <RadialGradient
          c={vec(C, C)}
          r={coronaR}
          colors={[cc.coronaInner, cc.coronaOuter, 'rgba(0,0,0,0)']}
        />
      </Circle>

      {/* Layer 2: Gas flares */}
      {gasFlares.map((f) => {
        const angle = f.angle + s.swirl1
        const dist = ar * 0.5
        const fx = C + Math.cos(angle) * dist
        const fy = C + Math.sin(angle) * dist
        const fr = ar * (0.3 + Math.sin(s.time + f.idx) * 0.08)
        return (
          <Circle key={f.idx} cx={fx} cy={fy} r={fr} blendMode={BlendMode.Screen}>
            <RadialGradient
              c={vec(fx, fy)}
              r={fr}
              colors={[cc.gasInner, cc.gasOuter, 'rgba(0,0,0,0)']}
            />
          </Circle>
        )
      })}

      {/* Layer 3: Stream fibers */}
      {fiberOffsets.map((off, i) => (
        <Path
          key={i}
          path={buildFiberPath(off)}
          style="stroke"
          strokeWidth={isSpeaking ? 4 : 3}
          blendMode={BlendMode.Screen}
          color={fiberColor}
        />
      ))}

      {/* Layer 4: Halo */}
      <Path path={buildHaloPath()} style="stroke" strokeWidth={2} blendMode={BlendMode.Screen}>
        <RadialGradient
          c={vec(C, C)}
          r={ar * 1.5}
          colors={[
            isSpeaking ? 'rgba(168,85,247,0.5)' : 'rgba(0,251,251,0.4)',
            'rgba(0,0,0,0)',
          ]}
        />
      </Path>

      {/* Layer 5: Core */}
      <Circle cx={C} cy={C} r={coreR}>
        <RadialGradient
          c={vec(C, C)}
          r={coreR}
          colors={[
            'rgba(255,255,255,0.7)',
            cc.coreGlow,
            cc.coreOuter,
            'rgba(0,0,0,0)',
          ]}
        />
      </Circle>

      {/* Layer 6: Holographic lines */}
      <Circle cx={C} cy={C} r={ar * 0.98} style="stroke" strokeWidth={1}
        color={isSpeaking ? 'rgba(168,85,247,0.3)' : 'rgba(0,251,251,0.2)'}
        blendMode={BlendMode.Screen} />
      <Circle cx={C} cy={C} r={ar * 1.05 + 6} style="stroke" strokeWidth={1}
        color={isSpeaking ? 'rgba(168,85,247,0.2)' : 'rgba(0,251,251,0.15)'}
        blendMode={BlendMode.Screen}>
        <DashPathEffect intervals={[3, 24]} />
      </Circle>

      {/* Layer 7: Highlight shine */}
      <Circle cx={C - ar * 0.25} cy={C - ar * 0.25} r={ar * 0.5}
        style="stroke" strokeWidth={2}
        color="rgba(255,255,255,0.08)" blendMode={BlendMode.Screen} />
    </Canvas>
  )
}

const styles = StyleSheet.create({
  canvas: {
    width: SIZE,
    height: SIZE,
  },
})
