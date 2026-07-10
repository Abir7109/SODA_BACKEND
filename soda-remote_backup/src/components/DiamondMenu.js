import React, { useEffect, useRef } from 'react'
import {
  View, Text, TouchableOpacity, StyleSheet,
  Animated, Dimensions, Easing,
} from 'react-native'
import {
  Canvas, Circle, Path, Skia, RadialGradient, vec,
} from '@shopify/react-native-skia'
import { COLORS } from '../constants/colors'
import { DIAMOND_OPTIONS } from '../constants/options'

const { width: SW, height: SH } = Dimensions.get('window')
const SPREAD = Math.min(SW, SH) * 0.32
const NODE_SIZE = 68

const POSITIONS = [
  { x: 0, y: -SPREAD },
  { x: -SPREAD * 0.65, y: -SPREAD * 0.45 },
  { x: SPREAD * 0.65, y: -SPREAD * 0.45 },
  { x: -SPREAD, y: 0 },
  { x: SPREAD, y: 0 },
  { x: -SPREAD * 0.65, y: SPREAD * 0.45 },
  { x: SPREAD * 0.65, y: SPREAD * 0.45 },
  { x: 0, y: SPREAD },
]

function DiamondNodeIcon({ color, icon }) {
  const iconPaths = {
    camera: () => {
      const p = Skia.Path.Make()
      p.addCircle(12, 12, 6)
      p.addCircle(12, 12, 3)
      return p
    },
    mouse: () => {
      const p = Skia.Path.Make()
      p.moveTo(8, 4); p.lineTo(16, 4); p.lineTo(12, 18); p.close()
      return p
    },
    keyboard: () => {
      const p = Skia.Path.Make()
      for (let row = 0; row < 3; row++)
        for (let col = 0; col < 5; col++)
          p.addRect(Skia.XYWHRect(3 + col * 4.5, 3 + row * 4.5, 3.2, 2.8))
      return p
    },
    volume: () => {
      const p = Skia.Path.Make()
      p.moveTo(5, 8); p.lineTo(9, 8); p.lineTo(13, 4); p.lineTo(13, 20); p.lineTo(9, 16); p.lineTo(5, 16); p.close()
      p.moveTo(15, 8); p.addArc(Skia.XYWHRect(15, 8, 5, 8), 0, 180)
      return p
    },
    sun: () => {
      const p = Skia.Path.Make()
      p.addCircle(12, 12, 5)
      for (let i = 0; i < 8; i++) {
        const a = (i / 8) * Math.PI * 2
        p.moveTo(12 + Math.cos(a) * 7, 12 + Math.sin(a) * 7)
        p.lineTo(12 + Math.cos(a) * 10, 12 + Math.sin(a) * 10)
      }
      return p
    },
    folder: () => {
      const p = Skia.Path.Make()
      p.moveTo(3, 5); p.lineTo(10, 5); p.lineTo(12, 8); p.lineTo(21, 8); p.lineTo(21, 19)
      p.lineTo(3, 19); p.close()
      return p
    },
    terminal: () => {
      const p = Skia.Path.Make()
      p.moveTo(4, 6); p.lineTo(8, 12); p.lineTo(4, 18)
      p.moveTo(12, 17); p.lineTo(20, 17)
      return p
    },
    grid: () => {
      const p = Skia.Path.Make()
      p.addRect(Skia.XYWHRect(3, 3, 6, 6))
      p.addRect(Skia.XYWHRect(15, 3, 6, 6))
      p.addRect(Skia.XYWHRect(3, 15, 6, 6))
      p.addRect(Skia.XYWHRect(15, 15, 6, 6))
      return p
    },
  }

  const path = iconPaths[icon]?.()
  if (!path) return null

  return (
    <Canvas style={{ width: 24, height: 24 }}>
      <Path path={path} style="stroke" strokeWidth={1.5} color={color} />
    </Canvas>
  )
}

export default function DiamondMenu({ visible, onSelect, onDismiss }) {
  const centerOpacity = useRef(new Animated.Value(0)).current
  const nodeAnims = useRef(DIAMOND_OPTIONS.map(() => new Animated.Value(0))).current
  const bgOpacity = useRef(new Animated.Value(0)).current
  const rotationAnims = useRef(DIAMOND_OPTIONS.map(() => new Animated.Value(0))).current

  useEffect(() => {
    if (visible) {
      Animated.timing(bgOpacity, {
        toValue: 1, duration: 300, useNativeDriver: true,
      }).start()

      Animated.spring(centerOpacity, {
        toValue: 1, friction: 6, tension: 100, useNativeDriver: true,
      }).start()

      const springs = DIAMOND_OPTIONS.map((_, i) =>
        Animated.spring(nodeAnims[i], {
          toValue: 1, friction: 5, tension: 80,
          delay: 40 + i * 50, useNativeDriver: true,
        })
      )
      Animated.stagger(30, springs).start()

      DIAMOND_OPTIONS.forEach((_, i) => {
        Animated.spring(rotationAnims[i], {
          toValue: 1, friction: 6, tension: 60,
          delay: 40 + i * 50, useNativeDriver: true,
        }).start()
      })
    } else {
      Animated.parallel([
        Animated.timing(bgOpacity, { toValue: 0, duration: 200, useNativeDriver: true }),
        Animated.timing(centerOpacity, { toValue: 0, duration: 150, useNativeDriver: true }),
        ...nodeAnims.map((anim) =>
          Animated.timing(anim, { toValue: 0, duration: 120, useNativeDriver: true })
        ),
        ...rotationAnims.map((anim) =>
          Animated.timing(anim, { toValue: 0, duration: 120, useNativeDriver: true })
        ),
      ]).start()
    }
  }, [visible])

  if (!visible) return null

  return (
    <View style={styles.container} pointerEvents="box-none">
      <Animated.View style={[styles.backdrop, { opacity: bgOpacity }]}>
        <TouchableOpacity style={StyleSheet.absoluteFill} onPress={onDismiss} activeOpacity={1} />
      </Animated.View>

      <View style={styles.centerArea} pointerEvents="box-none">
        <Animated.View style={[styles.centerGlow, { opacity: centerOpacity }]} />
        <Animated.View style={[styles.centerDot, { opacity: centerOpacity }]} />

        {DIAMOND_OPTIONS.map((opt, i) => {
          const tx = nodeAnims[i].interpolate({
            inputRange: [0, 1], outputRange: [0, POSITIONS[i].x],
          })
          const ty = nodeAnims[i].interpolate({
            inputRange: [0, 1], outputRange: [0, POSITIONS[i].y],
          })
          const op = nodeAnims[i].interpolate({
            inputRange: [0, 0.3, 1], outputRange: [0, 0.1, 1],
          })
          const sc = nodeAnims[i].interpolate({
            inputRange: [0, 1], outputRange: [0.2, 1],
          })
          const rot = rotationAnims[i].interpolate({
            inputRange: [0, 1], outputRange: ['180deg', '0deg'],
          })

          return (
            <Animated.View
              key={opt.id}
              style={{
                position: 'absolute',
                opacity: op,
                transform: [
                  { translateX: tx },
                  { translateY: ty },
                  { scale: sc },
                  { rotate: rot },
                ],
              }}
            >
              <TouchableOpacity
                style={[styles.node, { borderColor: opt.color }]}
                onPress={() => onSelect(opt)}
                activeOpacity={0.8}
              >
                <DiamondNodeIcon color={opt.color} icon={opt.icon} />
                <Text style={[styles.nodeLabel, { color: opt.color }]}>{opt.label}</Text>
              </TouchableOpacity>
            </Animated.View>
          )
        })}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { ...StyleSheet.absoluteFillObject, zIndex: 100 },
  backdrop: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(4,8,11,0.7)' },
  centerArea: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  centerGlow: {
    position: 'absolute', width: 60, height: 60, borderRadius: 30,
    backgroundColor: COLORS.accentGlow,
    borderWidth: 1, borderColor: 'rgba(0,251,251,0.15)',
  },
  centerDot: {
    position: 'absolute', width: 6, height: 6, borderRadius: 3,
    backgroundColor: COLORS.accent,
    shadowColor: COLORS.accent,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.6,
    shadowRadius: 8,
    elevation: 4,
  },
  node: {
    width: NODE_SIZE, height: NODE_SIZE,
    backgroundColor: '#0A0F14',
    borderWidth: 1,
    justifyContent: 'center', alignItems: 'center',
    gap: 3,
    shadowColor: COLORS.accent,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 6,
  },
  nodeLabel: {
    fontSize: 7, fontWeight: '700', letterSpacing: 2,
    textAlign: 'center',
  },
})
