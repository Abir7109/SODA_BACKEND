import React, { useRef, useCallback, useState, useEffect } from 'react'
import { View, Text, TouchableOpacity, StyleSheet, PanResponder, Animated } from 'react-native'
import { COLORS } from '../../constants/colors'
import socketService from '../../services/SocketService'

const ACCENT = COLORS.nodeColors.mouse

export default function TouchpadScreen({ onBack }) {
  const [pos, setPos] = useState({ x: 50, y: 50 })
  const [clickState, setClickState] = useState('')
  const padRef = useRef(null)
  const pulseAnim = useRef(new Animated.Value(0)).current

  useEffect(() => {
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 0.5, duration: 2000, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 0, duration: 2000, useNativeDriver: true }),
      ])
    )
    pulse.start()
    return () => pulse.stop()
  }, [])

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: (evt) => {
        const { locationX, locationY } = evt.nativeEvent
        const p = { x: Math.round(locationX), y: Math.round(locationY) }
        setPos(p)
      },
      onPanResponderMove: (evt) => {
        const { locationX, locationY } = evt.nativeEvent
        const p = { x: Math.round(locationX), y: Math.round(locationY) }
        setPos(p)
        socketService.emit('mobile_force_tool', {
          tool: 'mouse_move',
          args: { x: p.x * 3, y: p.y * 2, duration: 0.05 },
        })
      },
    })
  ).current

  const fireClick = (type) => {
    setClickState(type)
    setTimeout(() => setClickState(''), 200)
    socketService.emit('mobile_force_tool', {
      tool: 'mouse_click',
      args: { x: screenX, y: screenY, button: type.toLowerCase(), clicks: 1 },
    })
  }

  const screenX = pos.x
  const screenY = pos.y

  return (
    <View style={styles.container}>
      <View style={styles.cornerTL} pointerEvents="none" />
      <View style={styles.cornerTR} pointerEvents="none" />

      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.headerBtn}>
          <Text style={styles.headerBack}>{'<<'} BACK</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>MOUSE</Text>
        <Text style={styles.headerCoords}>{screenX},{screenY}</Text>
      </View>
      <View style={styles.accentLine} />

      <View style={styles.padWrapper}>
        <View style={styles.touchpad} {...panResponder.panHandlers}>
          <Animated.View style={[styles.gridOverlay, { opacity: Animated.add(0.06, Animated.multiply(pulseAnim, 0.04)) }]} pointerEvents="none" />
          <View style={styles.crosshairH} />
          <View style={styles.crosshairV} />
          <View style={[styles.cursor, { left: screenX, top: screenY }]}>
            <View style={styles.cursorInner} />
          </View>
          <View style={styles.padCornerTL} />
          <View style={styles.padCornerTR} />
          <View style={styles.padCornerBL} />
          <View style={styles.padCornerBR} />
        </View>
      </View>

      {/* Click state indicator */}
      {clickState !== '' && (
        <View style={styles.clickFlash}>
          <Text style={styles.clickFlashText}>{clickState}</Text>
        </View>
      )}

      <View style={styles.bottomBar}>
        <TouchableOpacity
          style={[styles.clickBtn, clickState === 'LEFT' && styles.clickBtnActive]}
          onPress={() => fireClick('LEFT')}
          activeOpacity={0.6}
        >
          <Text style={[styles.clickText, clickState === 'LEFT' && styles.clickTextActive]}>L CLICK</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.clickBtn, styles.middleBtn]}
          onPress={() => fireClick('MID')}
          activeOpacity={0.6}
        >
          <Text style={[styles.clickText, styles.middleText, clickState === 'MID' && styles.clickTextActive]}>M</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.clickBtn, clickState === 'RIGHT' && styles.clickBtnActive]}
          onPress={() => fireClick('RIGHT')}
          activeOpacity={0.6}
        >
          <Text style={[styles.clickText, clickState === 'RIGHT' && styles.clickTextActive]}>R CLICK</Text>
        </TouchableOpacity>
      </View>
      <View style={styles.scrollHint}>
        <Text style={styles.scrollHintText}>DRAG TO MOVE • TWO-FINGER TO SCROLL</Text>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a0d0e' },
  cornerTL: {
    position: 'absolute', top: 50, left: 12, width: 10, height: 10,
    borderTopWidth: 1, borderLeftWidth: 1, borderColor: 'rgba(0,200,255,0.3)',
    zIndex: 10,
  },
  cornerTR: {
    position: 'absolute', top: 50, right: 12, width: 10, height: 10,
    borderTopWidth: 1, borderRightWidth: 1, borderColor: 'rgba(0,200,255,0.3)',
    zIndex: 10,
  },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 24, paddingTop: 54, paddingBottom: 10,
  },
  headerBtn: { paddingVertical: 4 },
  headerBack: { fontSize: 9, fontWeight: '700', color: COLORS.textDim, letterSpacing: 2, fontFamily: 'monospace' },
  headerTitle: { fontSize: 12, fontWeight: '700', color: ACCENT, letterSpacing: 5, fontFamily: 'monospace' },
  headerCoords: { fontSize: 8, color: ACCENT, fontFamily: 'monospace', opacity: 0.6 },
  accentLine: { height: 1, backgroundColor: ACCENT, marginHorizontal: 20, opacity: 0.4, marginBottom: 4 },
  padWrapper: { flex: 1, margin: 8 },
  touchpad: {
    flex: 1, borderRadius: 2, borderWidth: 1, borderColor: 'rgba(0,200,255,0.2)',
    justifyContent: 'center', alignItems: 'center',
    backgroundColor: '#0d1112', overflow: 'hidden', position: 'relative',
  },
  gridOverlay: {
    ...StyleSheet.absoluteFillObject,
    borderWidth: 0,
    backgroundColor: 'transparent',
    backgroundImage: undefined,
  },
  crosshairH: {
    position: 'absolute', width: '100%', height: 1,
    backgroundColor: 'rgba(0,200,255,0.04)',
  },
  crosshairV: {
    position: 'absolute', height: '100%', width: 1,
    backgroundColor: 'rgba(0,200,255,0.04)',
  },
  cursor: {
    position: 'absolute', width: 14, height: 14,
    marginLeft: -7, marginTop: -7,
    justifyContent: 'center', alignItems: 'center',
  },
  cursorInner: {
    width: 6, height: 6,
    borderWidth: 1.5, borderColor: ACCENT,
    backgroundColor: 'rgba(0,200,255,0.1)',
    shadowColor: ACCENT,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 6,
    elevation: 4,
  },
  padCornerTL: {
    position: 'absolute', top: 6, left: 6, width: 14, height: 14,
    borderTopWidth: 1, borderLeftWidth: 1, borderColor: 'rgba(0,200,255,0.3)',
  },
  padCornerTR: {
    position: 'absolute', top: 6, right: 6, width: 14, height: 14,
    borderTopWidth: 1, borderRightWidth: 1, borderColor: 'rgba(0,200,255,0.3)',
  },
  padCornerBL: {
    position: 'absolute', bottom: 6, left: 6, width: 14, height: 14,
    borderBottomWidth: 1, borderLeftWidth: 1, borderColor: 'rgba(0,200,255,0.3)',
  },
  padCornerBR: {
    position: 'absolute', bottom: 6, right: 6, width: 14, height: 14,
    borderBottomWidth: 1, borderRightWidth: 1, borderColor: 'rgba(0,200,255,0.3)',
  },
  clickFlash: {
    position: 'absolute', top: '40%', left: '30%', right: '30%',
    backgroundColor: 'rgba(0,200,255,0.1)',
    borderWidth: 1, borderColor: ACCENT,
    padding: 8, alignItems: 'center', zIndex: 20,
  },
  clickFlashText: { fontSize: 10, color: ACCENT, fontFamily: 'monospace', letterSpacing: 2 },
  bottomBar: {
    flexDirection: 'row', justifyContent: 'center',
    paddingVertical: 10, paddingHorizontal: 20, gap: 10,
  },
  clickBtn: {
    flex: 1, paddingVertical: 12, borderRadius: 2,
    borderWidth: 1, borderColor: 'rgba(0,200,255,0.25)',
    backgroundColor: '#0d1112', alignItems: 'center',
  },
  clickBtnActive: { borderColor: ACCENT, backgroundColor: 'rgba(0,200,255,0.08)' },
  middleBtn: { flex: 0.4 },
  clickText: { fontSize: 8, fontWeight: '700', color: COLORS.textSecondary, letterSpacing: 2, fontFamily: 'monospace' },
  clickTextActive: { color: ACCENT },
  middleText: { fontSize: 9 },
  scrollHint: { alignItems: 'center', paddingBottom: 8 },
  scrollHintText: { fontSize: 6, color: COLORS.textDim, letterSpacing: 2, fontFamily: 'monospace', opacity: 0.5 },
})
