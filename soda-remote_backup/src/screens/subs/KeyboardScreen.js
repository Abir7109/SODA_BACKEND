import React, { useState, useCallback, useRef, useEffect } from 'react'
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Animated, ScrollView } from 'react-native'
import { COLORS } from '../../constants/colors'
import socketService from '../../services/SocketService'

const ACCENT = COLORS.nodeColors.keyboard

const ROW1 = ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P']
const ROW2 = ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L']
const ROW3 = ['Z', 'X', 'C', 'V', 'B', 'N', 'M']

const SPECIAL_KEYS = [
  { label: 'TAB', key: 'TAB' },
  { label: 'CTRL', key: 'CTRL' },
  { label: 'ALT', key: 'ALT' },
  { label: 'SHIFT', key: 'SHIFT' },
  { label: 'SPACE', key: ' ' },
  { label: 'BKSP', key: 'BKSP' },
  { label: 'ENTER', key: 'ENTER' },
  { label: 'ESC', key: 'ESC' },
]

export default function KeyboardScreen({ onBack }) {
  const [text, setText] = useState('')
  const [pressedKey, setPressedKey] = useState('')
  const inputRef = useRef(null)
  const counterAnim = useRef(new Animated.Value(1)).current

  useEffect(() => {
    Animated.sequence([
      Animated.timing(counterAnim, { toValue: 1.2, duration: 150, useNativeDriver: true }),
      Animated.timing(counterAnim, { toValue: 1, duration: 150, useNativeDriver: true }),
    ]).start()
  }, [text.length])

  const handleKey = useCallback((key) => {
    setPressedKey(key)
    setTimeout(() => setPressedKey(''), 150)
    if (key === 'BKSP') {
      setText((prev) => prev.slice(0, -1))
    } else if (key === 'ENTER') {
      setText((prev) => prev + '\n')
    } else {
      setText((prev) => prev + key)
    }
  }, [])

  const sendText = useCallback(() => {
    if (!text.trim()) return
    socketService.emit('mobile_force_tool', {
      tool: 'keyboard_type',
      args: { text: text, interval: 0.02 },
    })
  }, [text])

  const clearText = useCallback(() => setText(''), [])

  const renderKey = (label, keyVal, wide) => (
    <TouchableOpacity
      key={keyVal}
      style={[
        styles.key,
        wide && styles.keyWide,
        pressedKey === keyVal && styles.keyPressed,
      ]}
      onPress={() => handleKey(keyVal)}
      activeOpacity={0.6}
    >
      <Text style={[styles.keyText, pressedKey === keyVal && styles.keyTextPressed]}>
        {label}
      </Text>
    </TouchableOpacity>
  )

  return (
    <View style={styles.container}>
      <View style={styles.cornerTL} pointerEvents="none" />
      <View style={styles.cornerTR} pointerEvents="none" />

      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.headerBtn}>
          <Text style={styles.headerBack}>{'<<'} BACK</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>KEYBOARD</Text>
        <Animated.Text style={[styles.headerCount, { transform: [{ scale: counterAnim }] }]}>
          {text.length}
        </Animated.Text>
      </View>
      <View style={styles.accentLine} />

      <View style={styles.content}>
        <View style={styles.inputBox}>
          <TextInput
            ref={inputRef}
            style={styles.input}
            value={text}
            onChangeText={setText}
            placeholder="type registers here..."
            placeholderTextColor={COLORS.textDim}
            autoCapitalize="none"
            autoCorrect={false}
            multiline
          />
          <TouchableOpacity style={styles.clearBtn} onPress={clearText}>
            <Text style={styles.clearText}>CLR</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.sendRow}>
          <TouchableOpacity style={styles.sendBtn} onPress={sendText} activeOpacity={0.7}>
            <Text style={styles.sendText}>SEND TO PC</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.keyboardArea}>
          {/* QWERTY Row 1 */}
          <View style={styles.keyRow}>{ROW1.map((k) => renderKey(k, k))}</View>
          {/* QWERTY Row 2 */}
          <View style={styles.keyRow}>{ROW2.map((k) => renderKey(k, k))}</View>
          {/* QWERTY Row 3 */}
          <View style={styles.keyRow}>{ROW3.map((k) => renderKey(k, k))}</View>
          {/* Special keys */}
          <View style={styles.keyRow}>
            {renderKey('BKSP', 'BKSP', true)}
            {renderKey('SPACE', ' ', true)}
            {renderKey('ENTER', 'ENTER', true)}
          </View>
          <View style={styles.keyRow}>
            {renderKey('TAB', 'TAB')}
            {renderKey('CTRL', 'CTRL')}
            {renderKey('ALT', 'ALT')}
            {renderKey('SHIFT', 'SHIFT')}
            {renderKey('ESC', 'ESC')}
          </View>
        </View>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a0e0a' },
  cornerTL: {
    position: 'absolute', top: 50, left: 12, width: 10, height: 10,
    borderTopWidth: 1, borderLeftWidth: 1, borderColor: 'rgba(0,255,160,0.3)',
    zIndex: 10,
  },
  cornerTR: {
    position: 'absolute', top: 50, right: 12, width: 10, height: 10,
    borderTopWidth: 1, borderRightWidth: 1, borderColor: 'rgba(0,255,160,0.3)',
    zIndex: 10,
  },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 24, paddingTop: 54, paddingBottom: 10,
  },
  headerBtn: { paddingVertical: 4 },
  headerBack: { fontSize: 9, fontWeight: '700', color: COLORS.textDim, letterSpacing: 2, fontFamily: 'monospace' },
  headerTitle: { fontSize: 12, fontWeight: '700', color: ACCENT, letterSpacing: 5, fontFamily: 'monospace' },
  headerCount: { fontSize: 10, fontWeight: '700', color: ACCENT, fontFamily: 'monospace' },
  accentLine: { height: 1, backgroundColor: ACCENT, marginHorizontal: 20, opacity: 0.4, marginBottom: 4 },
  content: { flex: 1, padding: 8, gap: 6 },
  inputBox: {
    flexDirection: 'row', alignItems: 'stretch',
    borderWidth: 1, borderColor: 'rgba(0,255,160,0.2)',
    backgroundColor: '#0d120d', borderRadius: 2,
    maxHeight: 80, minHeight: 40,
  },
  input: {
    flex: 1, padding: 10, color: COLORS.textPrimary, fontSize: 11,
    fontFamily: 'monospace', textAlignVertical: 'top',
  },
  clearBtn: {
    paddingHorizontal: 10, justifyContent: 'center',
    borderLeftWidth: 1, borderLeftColor: 'rgba(0,255,160,0.15)',
  },
  clearText: { fontSize: 8, color: ACCENT, fontFamily: 'monospace', letterSpacing: 1 },
  sendRow: { flexDirection: 'row' },
  sendBtn: {
    flex: 1, paddingVertical: 10,
    backgroundColor: ACCENT, borderRadius: 2,
    alignItems: 'center',
  },
  sendText: { fontSize: 9, fontWeight: '700', color: '#0a0e0a', letterSpacing: 3, fontFamily: 'monospace' },
  keyboardArea: { flex: 1, justifyContent: 'flex-end', gap: 4, paddingBottom: 4 },
  keyRow: { flexDirection: 'row', gap: 3, justifyContent: 'center' },
  key: {
    width: 28, height: 32,
    justifyContent: 'center', alignItems: 'center',
    borderWidth: 1, borderColor: 'rgba(0,255,160,0.2)',
    backgroundColor: '#0d120d', borderRadius: 2,
  },
  keyWide: { width: 48 },
  keyPressed: { borderColor: ACCENT, backgroundColor: 'rgba(0,255,160,0.1)' },
  keyText: { fontSize: 8, color: COLORS.textSecondary, fontFamily: 'monospace' },
  keyTextPressed: { color: ACCENT },
})
