import React, { useState, useRef, useCallback, useEffect } from 'react'
import {
  View, Text, TouchableOpacity, StyleSheet,
  StatusBar, Animated, Dimensions, Platform,
} from 'react-native'
import { COLORS } from '../constants/colors'
import SodaOrb from '../components/SodaOrb'
import DiamondMenu from '../components/DiamondMenu'
import socketService from '../services/SocketService'
import audioService from '../services/AudioService'
import TerminalScreen from './subs/TerminalScreen'
import FileBrowserScreen from './subs/FileBrowserScreen'
import TouchpadScreen from './subs/TouchpadScreen'
import KeyboardScreen from './subs/KeyboardScreen'
import VolumeScreen from './subs/VolumeScreen'
import BrightnessScreen from './subs/BrightnessScreen'
import ScreenshotScreen from './subs/ScreenshotScreen'
import AppLauncherScreen from './subs/AppLauncherScreen'

const { width: SW, height: SH } = Dimensions.get('window')
const TOUCH_SIZE = 140

const STATUS_CFG = {
  idle: { label: 'IDLE', color: COLORS.textDim },
  listening: { label: 'LISTENING', color: COLORS.accent },
  thinking: { label: 'THINKING', color: COLORS.warning },
  speaking: { label: 'SPEAKING', color: COLORS.nodeColors.capture },
}

export default function MainScreen({ onDisconnect }) {
  const [status, setStatus] = useState('idle')
  const [statusText, setStatusText] = useState('')
  const [micLevel, setMicLevel] = useState(0)
  const [diamondVisible, setDiamondVisible] = useState(false)
  const [subScreen, setSubScreen] = useState(null)

  const orbScale = useRef(new Animated.Value(1)).current

  useEffect(() => {
    audioService.init()
    socketService.emit('start_audio')

    const onMicLevel = (data) => {
      setMicLevel(data.level || 0)
    }

    const onSodaAudio = (data) => {
      if (data && data.data) {
        setStatus('speaking')
        audioService.playAudio(data.data, () => {
          setStatus('idle')
          setStatusText('')
        })
      }
    }

    const onSodaTranscription = (data) => {
      if (data && data.text) {
        const prefix = data.sender === 'User' ? 'You: ' : 'SODA: '
        setStatusText(prefix + data.text)
      }
    }

    const onSodaStatus = (data) => {
      if (data && data.msg) {
        setStatusText(data.msg)
      }
    }

    const onSodaError = (data) => {
      if (data && data.msg) {
        setStatusText('ERROR: ' + data.msg)
        setStatus('idle')
      }
    }

    socketService.on('mic_level', onMicLevel)
    socketService.on('soda_audio', onSodaAudio)
    socketService.on('soda_transcription', onSodaTranscription)
    socketService.on('soda_status', onSodaStatus)
    socketService.on('soda_error', onSodaError)

    return () => {
      socketService.off('mic_level', onMicLevel)
      socketService.off('soda_audio', onSodaAudio)
      socketService.off('soda_transcription', onSodaTranscription)
      socketService.off('soda_status', onSodaStatus)
      socketService.off('soda_error', onSodaError)
    }
  }, [])

  const toggleAudio = useCallback(async () => {
    if (status === 'speaking') {
      setStatus('idle')
      setStatusText('')
      return
    }

    if (status === 'thinking') return

    if (status === 'listening') {
      setStatus('thinking')
      setStatusText('Processing...')
      try {
        const pcmBase64 = await audioService.stopSend()
        if (pcmBase64) {
          socketService.emit('mobile_voice_command', { audio: pcmBase64 })
        } else {
          setStatus('idle')
          setStatusText('')
        }
      } catch (e) {
        setStatus('idle')
        setStatusText('')
      }
      return
    }

    if (status === 'idle') {
      setStatus('listening')
      setStatusText('Listening...')
      try {
        await audioService.startSend()
      } catch (e) {
        setStatus('idle')
        setStatusText(e.message === 'Microphone permission denied' ? 'MIC PERMISSION REQUIRED' : 'MIC ERROR')
      }
    }
  }, [status])

  const handleDiamondSelect = useCallback((option) => {
    setDiamondVisible(false)
    setTimeout(() => setSubScreen(option.screen), 200)
  }, [])

  if (subScreen) {
    const Sub = SUB_SCREENS[subScreen]
    if (!Sub) return null
    return (
      <View style={styles.container}>
        <StatusBar barStyle="light-content" backgroundColor={COLORS.bg} />
        <Sub onBack={() => setSubScreen(null)} />
      </View>
    )
  }

  const sc = STATUS_CFG[status] || STATUS_CFG.idle
  const displayStatus = statusText || sc.label
  const isActive = status !== 'idle'

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.bg} />

      <View style={styles.topBar}>
        <View style={styles.statusGroup}>
          <View style={[styles.statusDot, { backgroundColor: sc.color }]} />
          <Text style={[styles.statusLabel, { color: sc.color }]} numberOfLines={1}>{displayStatus}</Text>
        </View>
        <Text style={styles.versionLabel}>v1.0</Text>
      </View>

      <View style={styles.orbArea}>
        <Animated.View style={{ transform: [{ scale: orbScale }] }}>
          <SodaOrb
            micLevel={micLevel}
            isSpeaking={status === 'speaking'}
          />
        </Animated.View>

        <TouchableOpacity
          style={styles.touchTarget}
          activeOpacity={0.8}
          onPress={toggleAudio}
        />
      </View>

      <View style={styles.tapHint}>
        <Text style={styles.tapHintText}>{isActive ? 'TAP TO STOP' : 'TAP TO LISTEN'}</Text>
      </View>

      <View style={styles.bottomBar}>
        <TouchableOpacity
          style={styles.menuBtn}
          onPress={() => setDiamondVisible(true)}
          activeOpacity={0.7}
        >
          <View style={styles.menuIcon}>
            <View style={[styles.menuLine, { width: 16 }]} />
            <View style={[styles.menuLine, { width: 10 }]} />
            <View style={[styles.menuLine, { width: 16 }]} />
          </View>
        </TouchableOpacity>
      </View>

      <DiamondMenu
        visible={diamondVisible}
        onSelect={handleDiamondSelect}
        onDismiss={() => setDiamondVisible(false)}
      />
    </View>
  )
}

const SUB_SCREENS = {
  Terminal: TerminalScreen,
  Files: FileBrowserScreen,
  Touchpad: TouchpadScreen,
  Keyboard: KeyboardScreen,
  Volume: VolumeScreen,
  Brightness: BrightnessScreen,
  Capture: ScreenshotScreen,
  Apps: AppLauncherScreen,
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  topBar: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 20, paddingTop: Platform.OS === 'android' ? 48 : 54,
    paddingBottom: 6, height: 72,
  },
  statusGroup: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  statusDot: { width: 5, height: 5, borderRadius: 2.5 },
  statusLabel: { fontSize: 9, fontWeight: '700', letterSpacing: 3, fontFamily: 'monospace' },
  versionLabel: { fontSize: 8, color: COLORS.textDim, letterSpacing: 2, fontFamily: 'monospace' },
  orbArea: {
    flex: 1, justifyContent: 'center', alignItems: 'center',
    position: 'relative',
  },
  touchTarget: {
    position: 'absolute',
    width: TOUCH_SIZE, height: TOUCH_SIZE,
    borderRadius: TOUCH_SIZE / 2,
    top: '50%', left: '50%',
    marginLeft: -TOUCH_SIZE / 2,
    marginTop: -TOUCH_SIZE / 2,
    zIndex: 10,
  },
  tapHint: {
    position: 'absolute', left: 0, right: 0,
    top: '52%', alignItems: 'center',
  },
  tapHintText: {
    fontSize: 8, fontWeight: '600', color: COLORS.textDim,
    letterSpacing: 3, fontFamily: 'monospace',
  },
  bottomBar: {
    height: 80, justifyContent: 'center', alignItems: 'flex-end',
    paddingRight: 20, paddingBottom: 16,
  },
  menuBtn: {
    width: 44, height: 44, borderRadius: 22,
    backgroundColor: COLORS.bgCard, borderWidth: 1, borderColor: COLORS.accentBorder,
    justifyContent: 'center', alignItems: 'center',
  },
  menuIcon: { alignItems: 'center', gap: 3 },
  menuLine: { height: 1, backgroundColor: COLORS.textSecondary, borderRadius: 0.5 },
})
