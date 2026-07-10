import React, { useState, useEffect, useRef } from 'react'
import { View, Text, TouchableOpacity, StyleSheet, Animated } from 'react-native'
import { COLORS } from '../../constants/colors'
import socketService from '../../services/SocketService'

const ACCENT = COLORS.nodeColors.volume

const VU_BARS = 12

export default function VolumeScreen({ onBack }) {
  const [level, setLevel] = useState(65)
  const [muted, setMuted] = useState(false)
  const [peak, setPeak] = useState(0)
  const barAnims = useRef(VU_BARS.map(() => new Animated.Value(0))).current
  const pulseAnim = useRef(new Animated.Value(0)).current

  useEffect(() => {
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1, duration: 1500, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 0, duration: 1500, useNativeDriver: true }),
      ])
    )
    pulse.start()
    return () => pulse.stop()
  }, [])

  useEffect(() => {
    const displayLevel = muted ? 0 : level
    barAnims.forEach((anim, i) => {
      const threshold = ((i + 1) / VU_BARS) * 100
      const target = displayLevel >= threshold ? 1 : displayLevel / threshold
      Animated.timing(anim, {
        toValue: target,
        duration: 150,
        useNativeDriver: true,
      }).start()
    })
    if (displayLevel > peak) setPeak(displayLevel)
    else setPeak((p) => Math.max(0, p - 0.5))
  }, [level, muted])

  const adjust = (delta) => {
    setLevel((prev) => {
      const newLevel = Math.max(0, Math.min(100, prev + delta))
      socketService.emit('mobile_force_tool', {
        tool: 'control_system',
        args: { action: 'volume_set', value: newLevel },
      })
      return newLevel
    })
  }

  const barColors = ['#0a3a2a', '#0e4a35', '#0e4a35', '#125a3f', '#156a48', '#187a51', '#1b8a5a', '#1e9a63', '#30aa70', '#60ba80', '#90ca90', ACCENT]

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
        <Text style={styles.headerTitle}>VOLUME</Text>
        <Text style={styles.headerValue}>{muted ? '--' : level}%</Text>
      </View>
      <View style={styles.accentLine} />

      <View style={styles.content}>
        {/* VU Meter */}
        <View style={styles.vuContainer}>
          <View style={styles.vuBox}>
            {barAnims.map((anim, i) => (
              <Animated.View
                key={i}
                style={[
                  styles.vuBar,
                  {
                    backgroundColor: barColors[i],
                    opacity: anim.interpolate({
                      inputRange: [0, 1],
                      outputRange: [0.15, 0.9],
                    }),
                    transform: [
                      {
                        scaleY: anim.interpolate({
                          inputRange: [0, 1],
                          outputRange: [0.1, 1],
                        }),
                      },
                    ],
                  },
                ]}
              />
            ))}
            {/* Peak indicator */}
            <View style={[styles.peakLine, { bottom: `${peak}%` }]} />
          </View>
          <View style={styles.vuLabels}>
            <Text style={styles.vuLabel}>+6</Text>
            <Text style={styles.vuLabel}>0</Text>
            <Text style={styles.vuLabel}>-12</Text>
            <Text style={styles.vuLabel}>-24</Text>
            <Text style={styles.vuLabel}>-48</Text>
          </View>
        </View>

        {/* Slider */}
        <View style={styles.sliderSection}>
          <TouchableOpacity onPress={() => adjust(-10)} style={styles.stepBtn}>
            <Text style={styles.stepText}>-10</Text>
          </TouchableOpacity>
          <View style={styles.sliderRail}>
            <View style={[styles.sliderFill, { width: `${muted ? 0 : level}%` }]} />
            <Animated.View
              style={[
                styles.sliderGlow,
                { width: `${muted ? 0 : level}%`, opacity: Animated.add(0.1, Animated.multiply(pulseAnim, 0.15)) },
              ]}
            />
          </View>
          <TouchableOpacity onPress={() => adjust(10)} style={styles.stepBtn}>
            <Text style={styles.stepText}>+10</Text>
          </TouchableOpacity>
        </View>

        {/* Controls */}
        <View style={styles.controlRow}>
          <TouchableOpacity
            style={[styles.controlBtn, muted && styles.controlBtnActive]}
            onPress={() => {
              setMuted((prev) => !prev)
              socketService.emit('mobile_force_tool', {
                tool: 'control_system',
                args: { action: 'mute', value: '' },
              })
            }}
            activeOpacity={0.7}
          >
            <Text style={[styles.controlText, muted && styles.controlTextActive]}>
              {muted ? 'UNMUTE' : 'MUTE'}
            </Text>
          </TouchableOpacity>
        </View>

        {/* Device selector */}
        <View style={styles.deviceRow}>
          <Text style={styles.deviceLabel}>OUTPUT</Text>
          <View style={styles.deviceOption}>
            <Text style={styles.deviceText}>SPEAKERS</Text>
            <Text style={styles.deviceDot}>{'>'}</Text>
          </View>
        </View>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a0e0d' },
  cornerTL: {
    position: 'absolute', top: 50, left: 12, width: 10, height: 10,
    borderTopWidth: 1, borderLeftWidth: 1, borderColor: 'rgba(0,255,136,0.3)', zIndex: 10,
  },
  cornerTR: {
    position: 'absolute', top: 50, right: 12, width: 10, height: 10,
    borderTopWidth: 1, borderRightWidth: 1, borderColor: 'rgba(0,255,136,0.3)', zIndex: 10,
  },
  cornerBL: {
    position: 'absolute', bottom: 60, left: 12, width: 10, height: 10,
    borderBottomWidth: 1, borderLeftWidth: 1, borderColor: 'rgba(0,255,136,0.3)', zIndex: 10,
  },
  cornerBR: {
    position: 'absolute', bottom: 60, right: 12, width: 10, height: 10,
    borderBottomWidth: 1, borderRightWidth: 1, borderColor: 'rgba(0,255,136,0.3)', zIndex: 10,
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
  content: { flex: 1, padding: 16, gap: 16 },
  vuContainer: { flexDirection: 'row', flex: 1, gap: 8 },
  vuBox: {
    flex: 1, flexDirection: 'row', alignItems: 'flex-end', gap: 3,
    borderWidth: 1, borderColor: 'rgba(0,255,136,0.15)',
    backgroundColor: '#0d120d', padding: 8, position: 'relative',
  },
  vuBar: {
    flex: 1, height: '100%', borderRadius: 1,
    maxHeight: '100%',
  },
  peakLine: {
    position: 'absolute', left: 0, right: 0, height: 1,
    backgroundColor: ACCENT, opacity: 0.5,
  },
  vuLabels: { justifyContent: 'space-between', paddingVertical: 8 },
  vuLabel: { fontSize: 6, color: COLORS.textDim, fontFamily: 'monospace' },
  sliderSection: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
  },
  stepBtn: {
    paddingVertical: 6, paddingHorizontal: 12,
    borderWidth: 1, borderColor: 'rgba(0,255,136,0.2)',
    borderRadius: 2, backgroundColor: '#0d120d',
  },
  stepText: { fontSize: 9, color: ACCENT, fontFamily: 'monospace' },
  sliderRail: {
    flex: 1, height: 6,
    backgroundColor: '#0d120d', borderRadius: 3,
    borderWidth: 1, borderColor: 'rgba(0,255,136,0.2)',
    overflow: 'hidden',
  },
  sliderFill: {
    height: '100%', backgroundColor: ACCENT, borderRadius: 3,
  },
  sliderGlow: {
    position: 'absolute', top: 0, left: 0, height: '100%',
    backgroundColor: ACCENT, borderRadius: 3,
  },
  controlRow: { flexDirection: 'row', justifyContent: 'center' },
  controlBtn: {
    paddingVertical: 10, paddingHorizontal: 40,
    borderWidth: 1, borderColor: 'rgba(0,255,136,0.2)',
    borderRadius: 2, backgroundColor: '#0d120d',
  },
  controlBtnActive: { borderColor: ACCENT, backgroundColor: 'rgba(0,255,136,0.08)' },
  controlText: { fontSize: 9, color: COLORS.textSecondary, letterSpacing: 2, fontFamily: 'monospace' },
  controlTextActive: { color: ACCENT },
  deviceRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 12, paddingVertical: 8,
    borderWidth: 1, borderColor: 'rgba(0,255,136,0.1)',
    borderRadius: 2, backgroundColor: '#0d120d',
  },
  deviceLabel: { fontSize: 7, color: COLORS.textDim, letterSpacing: 2, fontFamily: 'monospace' },
  deviceOption: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  deviceText: { fontSize: 8, color: ACCENT, fontFamily: 'monospace', letterSpacing: 1 },
  deviceDot: { fontSize: 8, color: COLORS.textDim, fontFamily: 'monospace' },
})
