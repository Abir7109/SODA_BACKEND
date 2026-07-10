import React, { useState, useCallback, useEffect, useRef } from 'react'
import { View, Text, TouchableOpacity, StyleSheet, Animated } from 'react-native'
import { COLORS } from '../../constants/colors'
import socketService from '../../services/SocketService'

const ACCENT = COLORS.nodeColors.capture
const CAPTURE_MODES = ['FULL', 'WINDOW', 'REGION']

export default function ScreenshotScreen({ onBack }) {
  const [loading, setLoading] = useState(false)
  const [countdown, setCountdown] = useState(null)
  const [mode, setMode] = useState('FULL')
  const [captures, setCaptures] = useState([])
  const flashAnim = useRef(new Animated.Value(0)).current
  const pulseAnim = useRef(new Animated.Value(0)).current

  useEffect(() => {
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1, duration: 2500, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 0, duration: 2500, useNativeDriver: true }),
      ])
    )
    pulse.start()
    return () => pulse.stop()
  }, [])

  useEffect(() => {
    if (countdown === null) return
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown((prev) => prev - 1), 800)
      return () => clearTimeout(timer)
    } else {
      setCountdown(null)
      setLoading(true)
      Animated.sequence([
        Animated.timing(flashAnim, { toValue: 1, duration: 100, useNativeDriver: true }),
        Animated.timing(flashAnim, { toValue: 0, duration: 400, useNativeDriver: true }),
      ]).start(() => {
        setLoading(false)
        const ts = new Date().toLocaleTimeString()
        setCaptures((prev) => [`${mode} @ ${ts}`, ...prev].slice(0, 5))
      })
    }
  }, [countdown])

  useEffect(() => {
    const handler = (data) => {
      setCaptures((prev) => [`[${mode}] ${new Date().toLocaleTimeString()}`, ...prev].slice(0, 5))
    }
    socketService.on('screenshot_taken', handler)
    return () => socketService.off('screenshot_taken', handler)
  }, [mode])

  const snap = useCallback(() => {
    if (loading) return
    setCountdown(3)
    socketService.emit('mobile_force_tool', { tool: 'screenshot', args: {} })
  }, [loading])

  const countdownDot = (n) => {
    const dots = []
    for (let i = 0; i < n; i++) dots.push('*')
    return dots.join('')
  }

  return (
    <View style={styles.container}>
      <View style={styles.cornerTL} pointerEvents="none" />
      <View style={styles.cornerTR} pointerEvents="none" />

      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.headerBtn}>
          <Text style={styles.headerBack}>{'<<'} BACK</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>CAPTURE</Text>
        <Text style={styles.headerMode}>{mode}</Text>
      </View>
      <View style={styles.accentLine} />

      <View style={styles.content}>
        {/* Preview area */}
        <View style={styles.previewArea}>
          <View style={styles.previewCornerTL} />
          <View style={styles.previewCornerTR} />
          <View style={styles.previewCornerBL} />
          <View style={styles.previewCornerBR} />
          <Animated.View style={[styles.gridOverlay, { opacity: Animated.add(0.03, Animated.multiply(pulseAnim, 0.03)) }]} pointerEvents="none" />

          {countdown !== null ? (
            <View style={styles.countdownOverlay}>
              <Text style={styles.countdownText}>{countdown}</Text>
              <Text style={styles.countdownHint}>{countdownDot(countdown)}</Text>
            </View>
          ) : loading ? (
            <Animated.View style={[styles.flash, { opacity: flashAnim }]} />
          ) : (
            <View style={styles.placeholder}>
              <View style={styles.cameraIcon}>
                <View style={styles.cameraBody}>
                  <View style={styles.cameraLens} />
                </View>
              </View>
              <Text style={styles.placeholderText}>TAP TO CAPTURE</Text>
              <Text style={styles.placeholderHint}>SCREENSHOT WILL APPEAR ON PC</Text>
            </View>
          )}
        </View>

        {/* Mode selector */}
        <View style={styles.modeRow}>
          {CAPTURE_MODES.map((m) => (
            <TouchableOpacity
              key={m}
              style={[styles.modeBtn, mode === m && styles.modeBtnActive]}
              onPress={() => setMode(m)}
              activeOpacity={0.7}
            >
              <Text style={[styles.modeText, mode === m && styles.modeTextActive]}>{m}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Snap button */}
        <TouchableOpacity
          style={[styles.snapBtn, loading && styles.snapBtnDisabled]}
          onPress={snap}
          disabled={loading || countdown !== null}
          activeOpacity={0.7}
        >
          <Text style={styles.snapText}>
            {countdown !== null ? `CAPTURING IN ${countdown}...` : loading ? 'SNAPPING...' : 'SNAP'}
          </Text>
        </TouchableOpacity>

        {/* Recent captures */}
        {captures.length > 0 && (
          <View style={styles.recentBox}>
            <Text style={styles.recentTitle}>RECENT</Text>
            {captures.map((c, i) => (
              <Text key={i} style={styles.recentItem}>{c}</Text>
            ))}
          </View>
        )}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0d0b0a' },
  cornerTL: {
    position: 'absolute', top: 50, left: 12, width: 10, height: 10,
    borderTopWidth: 1, borderLeftWidth: 1, borderColor: 'rgba(255,180,50,0.3)', zIndex: 10,
  },
  cornerTR: {
    position: 'absolute', top: 50, right: 12, width: 10, height: 10,
    borderTopWidth: 1, borderRightWidth: 1, borderColor: 'rgba(255,180,50,0.3)', zIndex: 10,
  },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 24, paddingTop: 54, paddingBottom: 10,
  },
  headerBtn: { paddingVertical: 4 },
  headerBack: { fontSize: 9, fontWeight: '700', color: COLORS.textDim, letterSpacing: 2, fontFamily: 'monospace' },
  headerTitle: { fontSize: 12, fontWeight: '700', color: ACCENT, letterSpacing: 5, fontFamily: 'monospace' },
  headerMode: { fontSize: 8, color: ACCENT, fontFamily: 'monospace', letterSpacing: 2 },
  accentLine: { height: 1, backgroundColor: ACCENT, marginHorizontal: 20, opacity: 0.4, marginBottom: 4 },
  content: { flex: 1, padding: 16, gap: 12 },
  previewArea: {
    flex: 1, borderRadius: 2, borderWidth: 1, borderColor: 'rgba(255,180,50,0.2)',
    justifyContent: 'center', alignItems: 'center',
    backgroundColor: '#12100d', overflow: 'hidden', position: 'relative',
  },
  previewCornerTL: {
    position: 'absolute', top: 6, left: 6, width: 16, height: 16,
    borderTopWidth: 1, borderLeftWidth: 1, borderColor: 'rgba(255,180,50,0.35)', zIndex: 2,
  },
  previewCornerTR: {
    position: 'absolute', top: 6, right: 6, width: 16, height: 16,
    borderTopWidth: 1, borderRightWidth: 1, borderColor: 'rgba(255,180,50,0.35)', zIndex: 2,
  },
  previewCornerBL: {
    position: 'absolute', bottom: 6, left: 6, width: 16, height: 16,
    borderBottomWidth: 1, borderLeftWidth: 1, borderColor: 'rgba(255,180,50,0.35)', zIndex: 2,
  },
  previewCornerBR: {
    position: 'absolute', bottom: 6, right: 6, width: 16, height: 16,
    borderBottomWidth: 1, borderRightWidth: 1, borderColor: 'rgba(255,180,50,0.35)', zIndex: 2,
  },
  gridOverlay: {
    ...StyleSheet.absoluteFillObject,
    borderWidth: 0,
    backgroundColor: 'transparent',
  },
  countdownOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center', alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.6)', zIndex: 5,
  },
  countdownText: {
    fontSize: 72, fontWeight: '700', color: ACCENT,
    fontFamily: 'monospace', textShadowColor: ACCENT,
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 20,
  },
  countdownHint: { fontSize: 8, color: COLORS.textDim, fontFamily: 'monospace', letterSpacing: 4 },
  flash: {
    ...StyleSheet.absoluteFillObject, backgroundColor: '#fff', zIndex: 3,
  },
  placeholder: { alignItems: 'center', gap: 10 },
  cameraIcon: {
    width: 50, height: 40,
    justifyContent: 'center', alignItems: 'center',
  },
  cameraBody: {
    width: 40, height: 28,
    borderWidth: 1.5, borderColor: COLORS.textDim,
    borderRadius: 3, justifyContent: 'center', alignItems: 'center',
    backgroundColor: 'rgba(255,180,50,0.03)',
  },
  cameraLens: {
    width: 12, height: 12,
    borderWidth: 1.5, borderColor: COLORS.textDim,
    borderRadius: 6,
  },
  placeholderText: { fontSize: 9, color: COLORS.textSecondary, letterSpacing: 3, fontFamily: 'monospace' },
  placeholderHint: { fontSize: 6, color: COLORS.textDim, letterSpacing: 2, fontFamily: 'monospace' },
  modeRow: { flexDirection: 'row', gap: 6 },
  modeBtn: {
    flex: 1, paddingVertical: 8,
    borderWidth: 1, borderColor: 'rgba(255,180,50,0.2)',
    borderRadius: 2, backgroundColor: '#12100d',
    alignItems: 'center',
  },
  modeBtnActive: { borderColor: ACCENT, backgroundColor: 'rgba(255,180,50,0.08)' },
  modeText: { fontSize: 8, color: COLORS.textSecondary, fontFamily: 'monospace', letterSpacing: 2 },
  modeTextActive: { color: ACCENT },
  snapBtn: {
    paddingVertical: 12,
    backgroundColor: ACCENT, borderRadius: 2,
    alignItems: 'center',
  },
  snapBtnDisabled: { opacity: 0.5 },
  snapText: { fontSize: 10, fontWeight: '700', color: '#0d0b0a', letterSpacing: 3, fontFamily: 'monospace' },
  recentBox: {
    borderWidth: 1, borderColor: 'rgba(255,180,50,0.1)',
    borderRadius: 2, padding: 8, backgroundColor: '#12100d',
  },
  recentTitle: { fontSize: 7, color: COLORS.textDim, letterSpacing: 2, fontFamily: 'monospace', marginBottom: 4 },
  recentItem: { fontSize: 7, color: ACCENT, fontFamily: 'monospace', paddingVertical: 1, opacity: 0.7 },
})
