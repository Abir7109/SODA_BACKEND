import React, { useState, useRef, useCallback, useEffect } from 'react'
import { View, Text, TextInput, TouchableOpacity, FlatList, StyleSheet, KeyboardAvoidingView, Platform, Animated } from 'react-native'
import { COLORS } from '../../constants/colors'
import socketService from '../../services/SocketService'

const ACCENT = COLORS.nodeColors.terminal

export default function TerminalScreen({ onBack }) {
  const [command, setCommand] = useState('')
  const [history, setHistory] = useState([])
  const [cmdIndex, setCmdIndex] = useState(-1)
  const cmdLog = useRef([])
  const listRef = useRef(null)
  const cursorOpacity = useRef(new Animated.Value(1)).current

  useEffect(() => {
    const blink = Animated.loop(
      Animated.sequence([
        Animated.timing(cursorOpacity, { toValue: 0, duration: 500, useNativeDriver: true }),
        Animated.timing(cursorOpacity, { toValue: 1, duration: 500, useNativeDriver: true }),
      ])
    )
    blink.start()
    return () => blink.stop()
  }, [])

  useEffect(() => {
    setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 50)
  }, [history])

  useEffect(() => {
    const handler = (data) => {
      setHistory((prev) => [...prev, { type: 'output', text: data.output || '[no output]', ts: new Date().toLocaleTimeString() }])
    }
    socketService.on('command_output', handler)
    return () => socketService.off('command_output', handler)
  }, [])

  const execute = useCallback(() => {
    const cmd = command.trim()
    if (!cmd) return
    const ts = new Date().toLocaleTimeString()
    setHistory((prev) => [...prev, { type: 'input', text: `$ ${cmd}`, ts }])
    socketService.emit('mobile_force_tool', {
      tool: 'terminal_execute',
      args: { command: cmd, timeout: 15 },
    })
    cmdLog.current.push(cmd)
    setCmdIndex(-1)
    setCommand('')
  }, [command])

  const navigateHistory = useCallback((dir) => {
    if (cmdLog.current.length === 0) return
    const maxIdx = cmdLog.current.length - 1
    let newIdx
    if (dir === 'up') {
      newIdx = cmdIndex >= maxIdx ? maxIdx : cmdIndex + 1
    } else {
      newIdx = cmdIndex <= 0 ? -1 : cmdIndex - 1
    }
    setCmdIndex(newIdx)
    setCommand(newIdx >= 0 ? cmdLog.current[maxIdx - newIdx] : '')
  }, [cmdIndex])

  const renderItem = useCallback(({ item }) => (
    <View style={item.type === 'input' ? styles.lineInput : styles.lineOutput}>
      <Text style={[styles.lineText, item.type === 'input' ? styles.inputText : styles.outputText]}>
        {item.text}
      </Text>
      <Text style={styles.lineTs}>{item.ts}</Text>
    </View>
  ), [])

  return (
    <View style={styles.container}>
      <View style={styles.cornerTL} pointerEvents="none" />
      <View style={styles.cornerTR} pointerEvents="none" />
      <View style={styles.cornerBL} pointerEvents="none" />
      <View style={styles.cornerBR} pointerEvents="none" />
      <View style={styles.gridLines} pointerEvents="none" />

      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.headerBtn}>
          <Text style={styles.headerBack}>{'<<'} BACK</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>TERMINAL</Text>
        <View style={styles.statusBar}>
          <View style={styles.statusDot} />
          <Text style={styles.statusText}>IDLE</Text>
        </View>
      </View>
      <View style={styles.accentLine} />

      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <View style={styles.outputBox}>
          {history.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyPrompt}>
                SODA@REMOTE:~$
                <Animated.Text style={[styles.cursor, { opacity: cursorOpacity }]}>_</Animated.Text>
              </Text>
              <Text style={styles.emptyHint}>type a command then press RUN</Text>
              <View style={styles.helpRow}>
                <Text style={styles.helpKey}>UP</Text>
                <Text style={styles.helpText}>prev command</Text>
                <Text style={styles.helpKey}>DOWN</Text>
                <Text style={styles.helpText}>next command</Text>
              </View>
            </View>
          ) : (
            <FlatList
              ref={listRef}
              data={history}
              keyExtractor={(_, i) => String(i)}
              renderItem={renderItem}
              contentContainerStyle={styles.list}
              showsVerticalScrollIndicator={false}
            />
          )}
        </View>

        <View style={styles.inputRow}>
          <Text style={styles.prompt}>$</Text>
          <TextInput
            style={styles.input}
            value={command}
            onChangeText={setCommand}
            onSubmitEditing={execute}
            placeholder="enter command..."
            placeholderTextColor={COLORS.textDim}
            autoCapitalize="none"
            autoCorrect={false}
            returnKeyType="send"
          />
          <TouchableOpacity onPress={() => navigateHistory('up')} style={styles.navBtn}>
            <Text style={styles.navBtnText}>^</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => navigateHistory('down')} style={styles.navBtn}>
            <Text style={styles.navBtnText}>v</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={execute} style={styles.runBtn} activeOpacity={0.7}>
            <Text style={styles.runText}>RUN</Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a0e0a' },
  gridLines: {
    ...StyleSheet.absoluteFillObject,
    opacity: 0.04,
    borderWidth: 0,
    backgroundColor: 'transparent',
    backgroundImage: undefined,
  },
  cornerTL: {
    position: 'absolute', top: 50, left: 12, width: 10, height: 10,
    borderTopWidth: 1, borderLeftWidth: 1, borderColor: 'rgba(0,255,100,0.3)',
    zIndex: 10,
  },
  cornerTR: {
    position: 'absolute', top: 50, right: 12, width: 10, height: 10,
    borderTopWidth: 1, borderRightWidth: 1, borderColor: 'rgba(0,255,100,0.3)',
    zIndex: 10,
  },
  cornerBL: {
    position: 'absolute', bottom: 60, left: 12, width: 10, height: 10,
    borderBottomWidth: 1, borderLeftWidth: 1, borderColor: 'rgba(0,255,100,0.3)',
    zIndex: 10,
  },
  cornerBR: {
    position: 'absolute', bottom: 60, right: 12, width: 10, height: 10,
    borderBottomWidth: 1, borderRightWidth: 1, borderColor: 'rgba(0,255,100,0.3)',
    zIndex: 10,
  },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 24, paddingTop: 54, paddingBottom: 10,
  },
  headerBtn: { paddingVertical: 4 },
  headerBack: { fontSize: 9, fontWeight: '700', color: COLORS.textDim, letterSpacing: 2, fontFamily: 'monospace' },
  headerTitle: { fontSize: 12, fontWeight: '700', color: ACCENT, letterSpacing: 5, fontFamily: 'monospace' },
  statusBar: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  statusDot: { width: 5, height: 5, borderRadius: 3, backgroundColor: ACCENT },
  statusText: { fontSize: 7, color: COLORS.textDim, letterSpacing: 2, fontFamily: 'monospace' },
  accentLine: { height: 1, backgroundColor: ACCENT, marginHorizontal: 20, opacity: 0.5, marginBottom: 4 },
  outputBox: { flex: 1, margin: 8, borderRadius: 2, borderWidth: 1, borderColor: 'rgba(0,255,100,0.15)', backgroundColor: '#0d120d', overflow: 'hidden' },
  emptyState: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
  emptyPrompt: { fontSize: 12, color: ACCENT, fontFamily: 'monospace' },
  emptyHint: { fontSize: 8, color: COLORS.textDim, letterSpacing: 2, fontFamily: 'monospace', marginTop: 12 },
  helpRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 8 },
  helpKey: { fontSize: 7, color: COLORS.textSecondary, fontFamily: 'monospace', borderWidth: 1, borderColor: COLORS.accentBorder, paddingHorizontal: 4, paddingVertical: 1 },
  helpText: { fontSize: 7, color: COLORS.textDim, fontFamily: 'monospace' },
  cursor: { fontSize: 12, color: ACCENT, fontFamily: 'monospace' },
  list: { padding: 12 },
  lineInput: { flexDirection: 'row', alignItems: 'flex-start', paddingVertical: 2 },
  lineOutput: { flexDirection: 'row', alignItems: 'flex-start', paddingVertical: 2, paddingLeft: 12 },
  lineText: { fontFamily: 'monospace', fontSize: 9, lineHeight: 16, flex: 1 },
  inputText: { color: ACCENT },
  outputText: { color: COLORS.textSecondary },
  lineTs: { fontSize: 7, color: 'rgba(0,255,100,0.25)', fontFamily: 'monospace', marginLeft: 8 },
  inputRow: {
    flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: 12, paddingVertical: 8, gap: 4,
    borderTopWidth: 1, borderTopColor: 'rgba(0,255,100,0.15)',
  },
  prompt: { fontFamily: 'monospace', fontSize: 11, color: ACCENT, marginRight: 6 },
  input: { flex: 1, height: 34, color: COLORS.textPrimary, fontSize: 10, fontFamily: 'monospace', paddingVertical: 0 },
  navBtn: {
    width: 28, height: 28, justifyContent: 'center', alignItems: 'center',
    borderWidth: 1, borderColor: 'rgba(0,255,100,0.2)', borderRadius: 2,
  },
  navBtnText: { fontSize: 9, color: ACCENT, fontFamily: 'monospace' },
  runBtn: {
    paddingVertical: 6, paddingHorizontal: 16, borderRadius: 2,
    backgroundColor: ACCENT,
  },
  runText: { fontSize: 9, fontWeight: '700', color: '#0a0e0a', letterSpacing: 1, fontFamily: 'monospace' },
})
