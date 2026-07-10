import React, { useState, useEffect, useRef } from 'react'
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  StatusBar, KeyboardAvoidingView, Platform, Animated, Easing, Dimensions,
} from 'react-native'
import { COLORS } from '../constants/colors'
import socketService from '../services/SocketService'
import storageService from '../services/StorageService'

const { width, height } = Dimensions.get('window')

const DEFAULT_URL = 'https://sulfonyl-preeruptively-uriah.ngrok-free.dev'
const DEFAULT_SECRET = '42080cb2ddb1314dc047ff9560f796a3dfe7bd96a50d201987c5429762039fcb'

const TUNNEL_URL_KEY = 'tunnel_url'

const STATUS = {
  idle: { label: 'READY', color: COLORS.textDim },
  connecting: { label: 'CONNECTING', color: COLORS.accent },
  authenticating: { label: 'AUTHENTICATING', color: COLORS.accent },
  connected: { label: 'LINKED', color: COLORS.success },
  failed: { label: 'FAILED', color: COLORS.error },
}

export default function ConnectionScreen({ onConnected }) {
  const [serverUrl, setServerUrl] = useState(DEFAULT_URL)
  const [secret, setSecret] = useState(DEFAULT_SECRET)
  const [status, setStatus] = useState('idle')
  const [statusText, setStatusText] = useState('')

  const logoScale = useRef(new Animated.Value(0.6)).current
  const logoGlow = useRef(new Animated.Value(0)).current
  const ringScale = useRef(new Animated.Value(1)).current
  const ringOpacity = useRef(new Animated.Value(0.5)).current
  const contentFade = useRef(new Animated.Value(0)).current
  const statusPulse = useRef(new Animated.Value(1)).current

  useEffect(() => {
    Animated.parallel([
      Animated.spring(logoScale, { toValue: 1, friction: 5, tension: 80, useNativeDriver: true }),
      Animated.timing(logoGlow, { toValue: 1, duration: 800, useNativeDriver: false }),
      Animated.timing(contentFade, { toValue: 1, duration: 600, delay: 300, useNativeDriver: true }),
    ]).start()

    const ringPulse = Animated.loop(
      Animated.sequence([
        Animated.parallel([
          Animated.timing(ringScale, { toValue: 1.6, duration: 2500, easing: Easing.out(Easing.sin), useNativeDriver: true }),
          Animated.timing(ringOpacity, { toValue: 0, duration: 2500, useNativeDriver: true }),
        ]),
        Animated.parallel([
          Animated.timing(ringScale, { toValue: 1, duration: 0, useNativeDriver: true }),
          Animated.timing(ringOpacity, { toValue: 0.5, duration: 0, useNativeDriver: true }),
        ]),
      ])
    )
    ringPulse.start()

    const pulseLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(statusPulse, { toValue: 0.4, duration: 1200, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
        Animated.timing(statusPulse, { toValue: 1, duration: 1200, easing: Easing.inOut(Easing.sin), useNativeDriver: true }),
      ])
    )
    pulseLoop.start()

    const loadSaved = async () => {
      // Always use the hardcoded DEFAULT_URL — saved URLs are ignored
      // (stale saved URLs cause confusion when tunnel provider changes)
      await storageService.clearConnection()
      setServerUrl(DEFAULT_URL)
      setSecret(DEFAULT_SECRET)
      setTimeout(() => autoConnect(DEFAULT_URL, DEFAULT_SECRET), 600)
    }
    loadSaved()

    return () => { ringPulse.stop(); pulseLoop.stop() }
  }, [])

  const autoConnect = async (url, sec) => {
    setStatus('connecting')
    setStatusText('Establishing link...')
    try {
      socketService.connect(url)
      await new Promise((resolve) => {
        let elapsed = 0
        const check = setInterval(() => {
          elapsed += 100
          if (socketService.connected) { clearInterval(check); resolve() }
          if (elapsed >= 8000) { clearInterval(check); resolve() }
        }, 100)
      })

      if (!socketService.connected) {
        setStatus('failed'); setStatusText('Connection timed out'); return
      }

      setStatus('authenticating')
      setStatusText('Authenticating...')
      const result = await socketService.authenticate(sec)
      if (result.success) {
        setStatus('connected'); setStatusText('LINKED')
        // Save tunnel URL for next remote connect
        try {
          const resp = await fetch(url.replace(/\/$/, '') + '/tunnel-url')
          const data = await resp.json()
          if (data.url) await storageService.saveTunnelUrl(data.url)
        } catch {}
        setTimeout(() => onConnected(), 500)
      } else {
        setStatus('failed'); setStatusText(result.error || 'Auth failed')
      }
    } catch (e) {
      setStatus('failed'); setStatusText(e.message || 'Connection error')
    }
  }

  const scanLocalNetwork = async () => {
    setStatus('connecting')
    setStatusText('Scanning local network...')

    // Common subnets to probe
    const subnets = ['192.168.0.', '192.168.1.', '10.0.0.']
    const found = []

    for (const subnet of subnets) {
      const probes = []
      for (let i = 1; i <= 10; i++) {
        const ip = `${subnet}${i}`
        probes.push(
          Promise.race([
            fetch(`http://${ip}:8000/status`).then((r) => r.ok ? ip : null),
            new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 2000)),
          ]).catch(() => null)
        )
      }
      const results = await Promise.all(probes)
      for (const ip of results) {
        if (ip) found.push(ip)
      }
    }
    // Also try known local IP
    try {
      const r = await Promise.race([
        fetch('http://192.168.0.7:8000/status').then((r) => r.ok ? '192.168.0.7' : null),
        new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 1500)),
      ])
      if (r && !found.includes(r)) found.push(r)
    } catch {}

    if (found.length === 0) {
      setStatus('failed')
      setStatusText('No server found on local network')
      return
    }

    // Try first found IP
    const localUrl = `http://${found[0]}:8000`
    setServerUrl(localUrl)
    await storageService.saveConnection(localUrl, secret)
    await autoConnect(localUrl, secret)
  }

  const handleConnect = async () => {
    if (!serverUrl.trim() || !secret.trim()) {
      setStatus('failed'); setStatusText('Fill in both fields'); return
    }
    await storageService.saveConnection(serverUrl.trim(), secret.trim())
    await autoConnect(serverUrl.trim(), secret.trim())
  }

  const s = STATUS[status]
  const isBusy = status === 'connecting' || status === 'authenticating'

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.bg} />

      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.content}>
        {/* Logo Section */}
        <Animated.View style={[styles.logoSection, { opacity: contentFade }]}>
          <View style={styles.logoGlowWrapper}>
            <Animated.View style={[styles.ring, { transform: [{ scale: ringScale }], opacity: ringOpacity }]} />
            <Animated.View style={[styles.logoOuter, { transform: [{ scale: logoScale }] }]}>
              <Animated.View style={[styles.logoInner, { opacity: logoGlow.interpolate({ inputRange: [0, 1], outputRange: [0.3, 1] }) }]}>
                <Text style={styles.logoText}>S</Text>
              </Animated.View>
            </Animated.View>
          </View>
          <Text style={styles.title}>SODA</Text>
          <Text style={styles.subtitle}>REMOTE</Text>
        </Animated.View>

        {/* Status */}
        <Animated.View style={[styles.statusRow, { opacity: contentFade }]}>
          <Animated.View style={[styles.statusDot, {
            backgroundColor: s.color,
            opacity: isBusy ? statusPulse : 1,
          }]} />
          <Text style={[styles.statusLabel, { color: s.color }]}>{statusText || s.label}</Text>
        </Animated.View>

        {/* Inputs */}
        <Animated.View style={{ width: '100%', opacity: contentFade }}>
          <View style={styles.inputGroup}>
            <Text style={styles.inputLabel}>SERVER URL</Text>
            <TextInput
              style={styles.input}
              value={serverUrl}
              onChangeText={setServerUrl}
              placeholder="https://xxxx.trycloudflare.com"
              placeholderTextColor={COLORS.textDim}
              autoCapitalize="none" autoCorrect={false}
              keyboardType="url"
              editable={!isBusy}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.inputLabel}>SECRET KEY</Text>
            <TextInput
              style={styles.input}
              value={secret}
              onChangeText={setSecret}
              placeholder="Enter your MOBILE_SECRET"
              placeholderTextColor={COLORS.textDim}
              secureTextEntry
              autoCapitalize="none" autoCorrect={false}
              editable={!isBusy}
            />
          </View>

          <TouchableOpacity
            style={[styles.connectBtn, isBusy && styles.connectBtnDisabled]}
            onPress={handleConnect}
            disabled={isBusy}
            activeOpacity={0.85}
          >
            <Text style={styles.connectBtnText}>
              {isBusy ? 'CONNECTING...' : status === 'connected' ? 'LINKED' : 'CONNECT TO SODA'}
            </Text>
          </TouchableOpacity>

          {serverUrl || secret ? (
            <TouchableOpacity style={styles.clearBtn} onPress={async () => {
              await storageService.clearConnection()
              setServerUrl(DEFAULT_URL); setSecret(DEFAULT_SECRET); setStatus('idle'); setStatusText('')
              socketService.disconnect()
            }}>
              <Text style={styles.clearBtnText}>CLEAR SAVED CREDENTIALS</Text>
            </TouchableOpacity>
          ) : null}

          {status === 'failed' ? (
            <TouchableOpacity style={styles.scanBtn} onPress={scanLocalNetwork} activeOpacity={0.85}>
              <Text style={styles.scanBtnText}>SCAN LOCAL NETWORK</Text>
            </TouchableOpacity>
          ) : null}
        </Animated.View>

        <Animated.View style={{ opacity: contentFade }}>
          <Text style={styles.footer}>SODA REMOTE v1.0</Text>
        </Animated.View>
      </KeyboardAvoidingView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  content: {
    flex: 1, justifyContent: 'center', alignItems: 'center',
    paddingHorizontal: 32, paddingBottom: 40,
  },
  logoSection: { alignItems: 'center', marginBottom: 36 },
  logoGlowWrapper: {
    width: 120, height: 120, justifyContent: 'center', alignItems: 'center',
  },
  ring: {
    position: 'absolute', width: 120, height: 120, borderRadius: 60,
    borderWidth: 1, borderColor: COLORS.accent,
  },
  logoOuter: {
    width: 88, height: 88, borderRadius: 44,
    backgroundColor: COLORS.bgSecondary,
    justifyContent: 'center', alignItems: 'center',
    borderWidth: 1, borderColor: COLORS.accentBorder,
  },
  logoInner: {
    width: 80, height: 80, borderRadius: 40,
    backgroundColor: COLORS.accentGlow,
    justifyContent: 'center', alignItems: 'center',
  },
  logoText: {
    fontSize: 40, fontWeight: '700', color: COLORS.accent,
    letterSpacing: 6,
  },
  title: {
    fontSize: 28, fontWeight: '700', color: COLORS.textPrimary,
    letterSpacing: 10, marginTop: 16,
  },
  subtitle: {
    fontSize: 10, fontWeight: '600', color: COLORS.textDim,
    letterSpacing: 12, marginTop: 6,
  },
  statusRow: {
    flexDirection: 'row', alignItems: 'center', marginBottom: 32,
    gap: 8, height: 20,
  },
  statusDot: {
    width: 5, height: 5, borderRadius: 2.5,
  },
  statusLabel: {
    fontSize: 9, fontWeight: '700', letterSpacing: 3, fontFamily: 'monospace',
  },
  inputGroup: { width: '100%', marginBottom: 14 },
  inputLabel: {
    fontSize: 8, fontWeight: '700', color: COLORS.textDim,
    letterSpacing: 3, marginBottom: 6,
  },
  input: {
    width: '100%', height: 44,
    backgroundColor: COLORS.bgSecondary,
    borderRadius: 4, borderWidth: 1, borderColor: COLORS.accentBorder,
    paddingHorizontal: 14, color: COLORS.textPrimary,
    fontSize: 12, fontFamily: 'monospace',
  },
  connectBtn: {
    width: '100%', height: 48,
    backgroundColor: COLORS.accent, borderRadius: 4,
    justifyContent: 'center', alignItems: 'center',
    marginTop: 8,
  },
  connectBtnDisabled: { opacity: 0.5 },
  connectBtnText: {
    fontSize: 11, fontWeight: '700', color: COLORS.bg, letterSpacing: 4,
  },
  clearBtn: { marginTop: 16, alignSelf: 'center' },
  clearBtnText: {
    fontSize: 8, fontWeight: '600', color: COLORS.textDim, letterSpacing: 2,
  },
  scanBtn: {
    width: '100%', height: 44, marginTop: 12,
    borderWidth: 1, borderColor: COLORS.accent, borderRadius: 4,
    justifyContent: 'center', alignItems: 'center',
    backgroundColor: 'transparent',
  },
  scanBtnText: {
    fontSize: 10, fontWeight: '700', color: COLORS.accent, letterSpacing: 3,
  },
  footer: {
    fontSize: 7, fontWeight: '600', color: COLORS.textDim,
    letterSpacing: 3, marginTop: 40,
  },
})
