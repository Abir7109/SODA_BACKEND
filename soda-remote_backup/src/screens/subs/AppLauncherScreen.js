import React, { useState, useMemo, useCallback, useRef } from 'react'
import { View, Text, TextInput, TouchableOpacity, StyleSheet, FlatList, Animated } from 'react-native'
import { COLORS } from '../../constants/colors'
import socketService from '../../services/SocketService'

const ACCENT = COLORS.nodeColors.apps

const APPS = [
  { name: 'Chrome', icon: '[]', category: 'browser' },
  { name: 'Firefox', icon: '{}', category: 'browser' },
  { name: 'VS Code', icon: '</>', category: 'dev' },
  { name: 'Terminal', icon: '>_', category: 'dev' },
  { name: 'Files', icon: '[#]', category: 'system' },
  { name: 'Spotify', icon: '( )', category: 'media' },
  { name: 'Discord', icon: '{ }', category: 'social' },
  { name: 'Slack', icon: '#()', category: 'social' },
  { name: 'Photos', icon: '[o]', category: 'media' },
  { name: 'Settings', icon: '(*)', category: 'system' },
  { name: 'Calculator', icon: '[+]', category: 'utility' },
  { name: 'Calendar', icon: '[d]', category: 'utility' },
]

const CATEGORIES = ['all', 'dev', 'browser', 'media', 'social', 'system', 'utility']

const RECENT_APPS = ['VS Code', 'Terminal', 'Chrome']

function AppCard({ app, isRecent, isFocused, onPress }) {
  const scaleAnim = useRef(new Animated.Value(1)).current

  const handlePressIn = () => {
    Animated.spring(scaleAnim, { toValue: 0.93, useNativeDriver: true }).start()
  }
  const handlePressOut = () => {
    Animated.spring(scaleAnim, { toValue: 1, useNativeDriver: true }).start()
  }

  const launch = useCallback(() => {
    socketService.emit('mobile_force_tool', {
      tool: 'open_app',
      args: { app_name: app.name },
    })
  }, [app.name])

  return (
    <Animated.View style={{ transform: [{ scale: scaleAnim }] }}>
      <TouchableOpacity
        style={[styles.appCard, isRecent && styles.appCardRecent]}
        onPress={launch}
        onPressIn={handlePressIn}
        onPressOut={handlePressOut}
        activeOpacity={0.8}
      >
        <Text style={styles.appIcon}>{app.icon}</Text>
        <Text style={styles.appName}>{app.name}</Text>
        <Text style={styles.appCategory}>{app.category}</Text>
      </TouchableOpacity>
    </Animated.View>
  )
}

export default function AppLauncherScreen({ onBack }) {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('all')

  const filtered = useMemo(() => {
    let result = APPS
    if (category !== 'all') {
      result = result.filter((a) => a.category === category)
    }
    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter((a) => a.name.toLowerCase().includes(q))
    }
    return result
  }, [search, category])

  const recentApps = useMemo(() => {
    return APPS.filter((a) => RECENT_APPS.includes(a.name))
  }, [])

  return (
    <View style={styles.container}>
      <View style={styles.cornerTL} pointerEvents="none" />
      <View style={styles.cornerTR} pointerEvents="none" />

      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.headerBtn}>
          <Text style={styles.headerBack}>{'<<'} BACK</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>APPLICATIONS</Text>
        <Text style={styles.headerCount}>{filtered.length}</Text>
      </View>
      <View style={styles.accentLine} />

      <View style={styles.searchBar}>
        <Text style={styles.searchIcon}>{'>'}</Text>
        <TextInput
          style={styles.searchInput}
          value={search}
          onChangeText={setSearch}
          placeholder="search apps..."
          placeholderTextColor={COLORS.textDim}
          autoCapitalize="none"
          autoCorrect={false}
        />
        {search !== '' && (
          <TouchableOpacity onPress={() => setSearch('')}>
            <Text style={styles.searchClear}>X</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* Category filter */}
      <View style={styles.catRow}>
        {CATEGORIES.map((c) => (
          <TouchableOpacity
            key={c}
            style={[styles.catBtn, category === c && styles.catBtnActive]}
            onPress={() => setCategory(c)}
            activeOpacity={0.7}
          >
            <Text style={[styles.catText, category === c && styles.catTextActive]}>
              {c.toUpperCase()}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <FlatList
        style={styles.list}
        data={filtered}
        keyExtractor={(item) => item.name}
        numColumns={3}
        columnWrapperStyle={styles.gridRow}
        showsVerticalScrollIndicator={false}
        ListHeaderComponent={() =>
          search === '' && category === 'all' ? (
            <View style={styles.recentSection}>
              <Text style={styles.sectionTitle}>RECENT</Text>
              <View style={styles.recentRow}>
                {recentApps.map((app) => (
                  <AppCard key={app.name} app={app} isRecent />
                ))}
              </View>
              <Text style={styles.sectionTitle}>ALL APPS</Text>
            </View>
          ) : null
        }
        renderItem={({ item }) => <AppCard app={item} />}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0d0a0e' },
  cornerTL: {
    position: 'absolute', top: 50, left: 12, width: 10, height: 10,
    borderTopWidth: 1, borderLeftWidth: 1, borderColor: 'rgba(180,80,255,0.3)', zIndex: 10,
  },
  cornerTR: {
    position: 'absolute', top: 50, right: 12, width: 10, height: 10,
    borderTopWidth: 1, borderRightWidth: 1, borderColor: 'rgba(180,80,255,0.3)', zIndex: 10,
  },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 24, paddingTop: 54, paddingBottom: 10,
  },
  headerBtn: { paddingVertical: 4 },
  headerBack: { fontSize: 9, fontWeight: '700', color: COLORS.textDim, letterSpacing: 2, fontFamily: 'monospace' },
  headerTitle: { fontSize: 12, fontWeight: '700', color: ACCENT, letterSpacing: 5, fontFamily: 'monospace' },
  headerCount: { fontSize: 9, color: ACCENT, fontFamily: 'monospace' },
  accentLine: { height: 1, backgroundColor: ACCENT, marginHorizontal: 20, opacity: 0.4, marginBottom: 4 },
  searchBar: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    marginHorizontal: 12, marginBottom: 8,
    paddingHorizontal: 12, height: 36,
    borderWidth: 1, borderColor: 'rgba(180,80,255,0.2)',
    borderRadius: 2, backgroundColor: '#11100d',
  },
  searchIcon: { fontSize: 10, color: ACCENT, fontFamily: 'monospace' },
  searchInput: { flex: 1, color: COLORS.textPrimary, fontSize: 10, fontFamily: 'monospace', padding: 0 },
  searchClear: { fontSize: 9, color: COLORS.textDim, fontFamily: 'monospace' },
  catRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 4, paddingHorizontal: 12, marginBottom: 8 },
  catBtn: {
    paddingVertical: 4, paddingHorizontal: 8,
    borderWidth: 1, borderColor: 'rgba(180,80,255,0.15)',
    borderRadius: 2, backgroundColor: '#11100d',
  },
  catBtnActive: { borderColor: ACCENT, backgroundColor: 'rgba(180,80,255,0.08)' },
  catText: { fontSize: 7, color: COLORS.textSecondary, fontFamily: 'monospace', letterSpacing: 1 },
  catTextActive: { color: ACCENT },
  list: { flex: 1, paddingHorizontal: 8 },
  gridRow: { gap: 6, justifyContent: 'flex-start', paddingHorizontal: 2 },
  recentSection: { marginBottom: 8 },
  sectionTitle: {
    fontSize: 8, color: COLORS.textDim, fontFamily: 'monospace',
    letterSpacing: 3, marginBottom: 8, marginTop: 4, paddingLeft: 4,
  },
  recentRow: { flexDirection: 'row', gap: 6, marginBottom: 8 },
  appCard: {
    width: '31%', aspectRatio: 0.9, borderRadius: 2,
    borderWidth: 1, borderColor: 'rgba(180,80,255,0.12)',
    justifyContent: 'center', alignItems: 'center', gap: 4,
    backgroundColor: '#11100d', marginBottom: 6,
  },
  appCardRecent: {
    width: '31%',
    borderColor: 'rgba(180,80,255,0.3)',
    backgroundColor: 'rgba(180,80,255,0.04)',
  },
  appIcon: { fontSize: 14, color: COLORS.textDim, fontFamily: 'monospace' },
  appName: { fontSize: 7, color: COLORS.textSecondary, fontFamily: 'monospace', letterSpacing: 1 },
  appCategory: { fontSize: 5, color: COLORS.textDim, fontFamily: 'monospace', textTransform: 'uppercase' },
})
