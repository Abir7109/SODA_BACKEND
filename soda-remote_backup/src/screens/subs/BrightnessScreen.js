import React, { useState, useEffect, useRef } from 'react'
import { View, Text, TouchableOpacity, StyleSheet, Animated } from 'react-native'
import { COLORS } from '../../constants/colors'
import socketService from '../../services/SocketService'

const ACCENT = COLORS.nodeColors.brightness

export default function BrightnessScreen({ onBack }) {
  const [level, setLevel] = useState(80)
  const [auto, setAuto] = useState(false)
  const sliderAnim = useRef(new Animated.Value(80)).current
  const pulseAnim = useRef(new Animated.Value(0)).current

  useEffect(() => {
    Animated.timing(sliderAnim, {
      toValue: level,
      duration: 300,
      useNativeDriver: true,
    }).start()
  }, [level])

  useEffect(() => {
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1, duration: 2000, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 0, duration: 2000, useNativeDriver: true }),
      ])
    )
    pulse.start()
    return () => pulse.stop()
  }, [])

  const adjust = (delta) => {
    setLevel((prev) => {
      const newLevel = Math.max(5, Math.min(100, prev + delta))
      socketService.emit('mobile_force_tool', {
        tool: 'control_system',
        args: { action: 'brightness_set', value: newLevel },
      })
      return newLevel
    })
  }

  const sunSize = 30 + (level / 100) * 40

  return (
    <View style={styles.container}>
      <View style={styles.cornerTL} pointerEvents="none" />
      <View style={styles.cornerTR} pointerEvents="none" />
      <View style={styles.cornerBL} pointerEvents="none" />
      <View style={styles.cornerBR} pointerEvents="none" />

      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.headerBtn}>
          <Text style={styles.headerBack}>{'<<'} BACK</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>BRIGHTNESS</Text>
        <Text style={styles.headerValue}>{level}%</Text>
      </View>
      <View style={styles.accentLine} />

      <View style={styles.content}>
        {/* Sun icon */}
        <Animated.View style={[styles.sunContainer, { opacity: Animated.add(0.6, Animated.multiply(pulseAnim, 0.3)) }]}>
          <View style={[styles.sun, { width: sunSize, height: sunSize }]}>
            <View style={[styles.sunCore, { opacity: level / 100 }]} />
            <View style={styles.sunRays}>
              {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => (
                <View
                  key={deg}
                  style={[
                    styles.sunRay,
                    {
                      transform: [{ rotate: `${deg}deg` }],
                      opacity: (level / 100) * 0.6,
                    },
                  ]}
                />
              ))}
            </View>
          </View>
        </Animated.View>

        {/* Animated slider */}
        <View style={styles.sliderSection}>
          <TouchableOpacity onPress={() => adjust(-10)} style={styles.stepBtn}>
            <Text style={styles.stepText}>-10</Text>
          </TouchableOpacity>
          <View style={styles.sliderRail}>
            <Animated.View
              style={[
                styles.sliderFill,
                {
                  width: sliderAnim.interpolate({
                    inputRange: [0, 100],
                    outputRange: ['0%', '100%'],
                  }),
                },
              ]}
            />
            <Animated.View
              style={[
                styles.sliderGlow,
                {
                  width: sliderAnim.interpolate({
                    inputRange: [0, 100],
                    outputRange: ['0%', '100%'],
                  }),
                  opacity: Animated.add(0.1, Animated.multiply(pulseAnim, 0.1)),
                },
              ]}
            />
          </View>
          <TouchableOpacity onPress={() => adjust(10)} style={styles.stepBtn}>
            <Text style={styles.stepText}>+10</Text>
          </TouchableOpacity>
        </View>

        {/* Quick presets */}
        <View style={styles.presetRow}>
          {[25, 50, 75, 100].map((v) => (
            <TouchableOpacity
              key={v}
              style={[styles.presetBtn, level === v && styles.presetBtnActive]}
              onPress={() => {
                setLevel(v)
                socketService.emit('mobile_force_tool', {
                  tool: 'control_system',
                  args: { action: 'brightness_set', value: v },
                })
              }}
              activeOpacity={0.7}
            >
              <Text style={[styles.presetText, level === v && styles.presetTextActive]}>{v}%</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Auto toggle */}
        <View style={styles.autoRow}>
          <TouchableOpacity
            style={[styles.autoBtn, auto && styles.autoBtnActive]}
            onPress={() => setAuto((prev) => !prev)}
            activeOpacity={0.7}
          >
            <Text style={[styles.autoText, auto && styles.autoTextActive]}>
              {auto ? 'AUTO BRIGHT: ON' : 'AUTO BRIGHT: OFF'}
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0d0d0a' },
  cornerTL: {
    position: 'absolute', top: 50, left: 12, width: 10, height: 10,
    borderTopWidth: 1, borderLeftWidth: 1, borderColor: 'rgba(255,200,50,0.3)', zIndex: 10,
  },
  cornerTR: {
    position: 'absolute', top: 50, right: 12, width: 10, height: 10,
    borderTopWidth: 1, borderRightWidth: 1, borderColor: 'rgba(255,200,50,0.3)', zIndex: 10,
  },
  cornerBL: {
    position: 'absolute', bottom: 60, left: 12, width: 10, height: 10,
    borderBottomWidth: 1, borderLeftWidth: 1, borderColor: 'rgba(255,200,50,0.3)', zIndex: 10,
  },
  cornerBR: {
    position: 'absolute', bottom: 60, right: 12, width: 10, height: 10,
    borderBottomWidth: 1, borderRightWidth: 1, borderColor: 'rgba(255,200,50,0.3)', zIndex: 10,
  },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 24, paddingTop: 54, paddingBottom: 10,
  },
  headerBtn: { paddingVertical: 4 },
  headerBack: { fontSize: 9, fontWeight: '700', color: COLORS.textDim, letterSpacing: 2, fontFamily: 'monospace' },
  headerTitle: { fontSize: 12, fontWeight: '700', color: ACCENT, letterSpacing: 5, fontFamily: 'monospace' },
  headerValue: { fontSize: 14, fontWeight: '700', color: ACCENT, fontFamily: 'monospace' },
  accentLine: { height: 1, backgroundColor: ACCENT, marginHorizontal: 20, opacity: 0.4, marginBottom: 4 },
  content: { flex: 1, padding: 24, gap: 24, alignItems: 'center', justifyContent: 'center' },
  sunContainer: {
    width: 100, height: 100,
    justifyContent: 'center', alignItems: 'center',
  },
  sun: {
    justifyContent: 'center', alignItems: 'center',
    position: 'relative',
  },
  sunCore: {
    width: '40%', height: '40%',
    borderRadius: 50,
    backgroundColor: ACCENT,
    shadowColor: ACCENT,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.6,
    shadowRadius: 15,
    elevation: 6,
  },
  sunRays: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center', alignItems: 'center',
  },
  sunRay: {
    position: 'absolute', width: 3, height: '60%',
    backgroundColor: ACCENT, borderRadius: 1,
  },
  sliderSection: {
    flexDirection: 'row', alignItems: 'center', gap: 10, width: '100%',
  },
  stepBtn: {
    paddingVertical: 6, paddingHorizontal: 12,
    borderWidth: 1, borderColor: 'rgba(255,200,50,0.2)',
    borderRadius: 2, backgroundColor: '#11120d',
  },
  stepText: { fontSize: 9, color: ACCENT, fontFamily: 'monospace' },
  sliderRail: {
    flex: 1, height: 6,
    backgroundColor: '#11120d', borderRadius: 3,
    borderWidth: 1, borderColor: 'rgba(255,200,50,0.2)',
    overflow: 'hidden',
  },
  sliderFill: {
    height: '100%', backgroundColor: ACCENT, borderRadius: 3,
  },
  sliderGlow: {
    position: 'absolute', top: 0, left: 0, height: '100%',
    backgroundColor: ACCENT, borderRadius: 3,
  },
  presetRow: { flexDirection: 'row', gap: 8, width: '100%' },
  presetBtn: {
    flex: 1, paddingVertical: 8,
    borderWidth: 1, borderColor: 'rgba(255,200,50,0.2)',
    borderRadius: 2, backgroundColor: '#11120d',
    alignItems: 'center',
  },
  presetBtnActive: { borderColor: ACCENT, backgroundColor: 'rgba(255,200,50,0.08)' },
  presetText: { fontSize: 8, color: COLORS.textSecondary, fontFamily: 'monospace' },
  presetTextActive: { color: ACCENT },
  autoRow: { width: '100%' },
  autoBtn: {
    paddingVertical: 10,
    borderWidth: 1, borderColor: 'rgba(255,200,50,0.2)',
    borderRadius: 2, backgroundColor: '#11120d',
    alignItems: 'center',
  },
  autoBtnActive: { borderColor: ACCENT, backgroundColor: 'rgba(255,200,50,0.08)' },
  autoText: { fontSize: 9, color: COLORS.textSecondary, letterSpacing: 2, fontFamily: 'monospace' },
  autoTextActive: { color: ACCENT },
})
