import React, { useState, useCallback, useEffect } from 'react'
import { View, Text, TouchableOpacity, StyleSheet, FlatList } from 'react-native'
import { COLORS } from '../../constants/colors'
import socketService from '../../services/SocketService'

const ACCENT = COLORS.nodeColors.files

export default function FileBrowserScreen({ onBack }) {
  const [path, setPath] = useState('')
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [viewMode, setViewMode] = useState('list')

  const loadDir = useCallback((dirPath) => {
    setLoading(true)
    socketService.emit('mobile_force_tool', {
      tool: 'list_files',
      args: { path: dirPath || '/', sort: 'name' },
    })
  }, [])

  useEffect(() => {
    const handler = (data) => {
      setLoading(false)
      if (data && data.items) {
        setItems(data.items.map((f) => ({
          name: f.name || f,
          type: f.type === 'folder' || f.type === 'dir' ? 'dir' : 'file',
          size: typeof f.size === 'number' ? `${(f.size / 1024).toFixed(1)} KB` : (f.size || ''),
        })))
      }
    }
    socketService.on('file_list', handler)
    return () => socketService.off('file_list', handler)
  }, [])

  useEffect(() => {
    loadDir('')
  }, [loadDir])

  useEffect(() => {
    loadDir(path)
  }, [path, loadDir])

  const navigateTo = useCallback((dirName) => {
    setPath((prev) => (prev ? `${prev}/${dirName}` : dirName))
  }, [])

  const navigateUp = useCallback(() => {
    setPath((prev) => {
      const parts = prev.split('/').filter(Boolean)
      return parts.length > 1 ? parts.slice(0, -1).join('/') : ''
    })
  }, [])

  const pathParts = path ? path.split('/').filter(Boolean) : []

  const renderItem = useCallback(({ item }) => (
    <TouchableOpacity
      style={styles.item}
      onPress={() => item.type === 'dir' ? navigateTo(item.name) : null}
      activeOpacity={0.7}
    >
      <Text style={[styles.itemIcon, item.type === 'dir' ? styles.dirIcon : styles.fileIcon]}>
        {item.type === 'dir' ? '[-]' : '[f]'}
      </Text>
      <Text style={[styles.itemName, item.type === 'dir' && styles.dirName]}>
        {item.name}
      </Text>
      {item.size ? (
        <Text style={styles.itemSize}>{item.size}</Text>
      ) : null}
      {item.type === 'dir' ? (
        <Text style={styles.itemArrow}>{'>'}</Text>
      ) : null}
    </TouchableOpacity>
  ), [navigateTo])

  return (
    <View style={styles.container}>
      <View style={styles.cornerTL} pointerEvents="none" />
      <View style={styles.cornerTR} pointerEvents="none" />

      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.headerBtn}>
          <Text style={styles.headerBack}>{'<<'} BACK</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>FILES</Text>
        <View style={styles.viewToggle}>
          <TouchableOpacity onPress={() => setViewMode('list')}>
            <Text style={[styles.viewIcon, viewMode === 'list' && styles.viewIconActive]}>[#]</Text>
          </TouchableOpacity>
        </View>
      </View>
      <View style={styles.accentLine} />

      <View style={styles.pathBar}>
        <TouchableOpacity onPress={navigateUp} style={styles.pathUp}>
          <Text style={styles.pathUpText}>{'<<'}</Text>
        </TouchableOpacity>
        <View style={styles.pathCrumbs}>
          <Text style={[styles.pathSeg, pathParts.length === 0 && styles.pathSegActive]}>/</Text>
          {pathParts.map((segment, i) => (
            <React.Fragment key={i}>
              <Text style={styles.pathSep}>/</Text>
              <Text style={[styles.pathSeg, i === pathParts.length - 1 && styles.pathSegActive]}>
                {segment}
              </Text>
            </React.Fragment>
          ))}
        </View>
      </View>

      <View style={styles.listBox}>
        {pathParts.length > 0 && (
          <TouchableOpacity style={styles.item} onPress={navigateUp}>
            <Text style={[styles.itemIcon, styles.dirIcon]}>[..]</Text>
            <Text style={[styles.itemName, styles.dirName]}>parent directory</Text>
          </TouchableOpacity>
        )}
        <FlatList
          data={items}
          keyExtractor={(item) => item.name}
          renderItem={renderItem}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.listStyle}
        />
      </View>

      <View style={styles.statusBar}>
        <Text style={styles.statusText}>
          {loading
            ? 'LOADING...'
            : `${items.filter((i) => i.type === 'dir').length} dirs  ${items.filter((i) => i.type === 'file').length} files`
          }
        </Text>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a0d0e' },
  cornerTL: {
    position: 'absolute', top: 50, left: 12, width: 10, height: 10,
    borderTopWidth: 1, borderLeftWidth: 1, borderColor: 'rgba(0,150,255,0.3)', zIndex: 10,
  },
  cornerTR: {
    position: 'absolute', top: 50, right: 12, width: 10, height: 10,
    borderTopWidth: 1, borderRightWidth: 1, borderColor: 'rgba(0,150,255,0.3)', zIndex: 10,
  },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 24, paddingTop: 54, paddingBottom: 10,
  },
  headerBtn: { paddingVertical: 4 },
  headerBack: { fontSize: 9, fontWeight: '700', color: COLORS.textDim, letterSpacing: 2, fontFamily: 'monospace' },
  headerTitle: { fontSize: 12, fontWeight: '700', color: ACCENT, letterSpacing: 5, fontFamily: 'monospace' },
  viewToggle: { flexDirection: 'row', gap: 4 },
  viewIcon: { fontSize: 10, color: COLORS.textDim, fontFamily: 'monospace' },
  viewIconActive: { color: ACCENT },
  accentLine: { height: 1, backgroundColor: ACCENT, marginHorizontal: 20, opacity: 0.4, marginBottom: 4 },
  pathBar: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    marginHorizontal: 12, marginBottom: 4,
    paddingHorizontal: 10, paddingVertical: 8,
    borderWidth: 1, borderColor: 'rgba(0,150,255,0.12)',
    backgroundColor: '#0d1112', borderRadius: 2,
  },
  pathUp: {
    paddingRight: 8, borderRightWidth: 1,
    borderRightColor: 'rgba(0,150,255,0.15)',
  },
  pathUpText: { fontSize: 9, color: ACCENT, fontFamily: 'monospace' },
  pathCrumbs: { flexDirection: 'row', alignItems: 'center', flex: 1, flexWrap: 'wrap' },
  pathSep: { fontSize: 9, color: COLORS.textDim, fontFamily: 'monospace', marginHorizontal: 1 },
  pathSeg: { fontSize: 9, color: COLORS.textSecondary, fontFamily: 'monospace' },
  pathSegActive: { color: ACCENT, fontWeight: '700' },
  listBox: { flex: 1, margin: 8, borderRadius: 2, borderWidth: 1, borderColor: 'rgba(0,150,255,0.1)', backgroundColor: '#0d1112', overflow: 'hidden' },
  listStyle: { paddingVertical: 4 },
  item: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    paddingVertical: 10, paddingHorizontal: 14,
    borderBottomWidth: 1, borderBottomColor: 'rgba(0,150,255,0.04)',
  },
  itemIcon: { fontSize: 9, fontFamily: 'monospace', width: 20 },
  dirIcon: { color: ACCENT },
  fileIcon: { color: COLORS.textDim },
  itemName: { flex: 1, fontSize: 9, color: COLORS.textPrimary, fontFamily: 'monospace' },
  dirName: { color: COLORS.textSecondary },
  itemSize: { fontSize: 7, color: COLORS.textDim, fontFamily: 'monospace' },
  itemArrow: { fontSize: 8, color: ACCENT, fontFamily: 'monospace', opacity: 0.5 },
  statusBar: {
    flexDirection: 'row', justifyContent: 'center',
    paddingVertical: 6, marginHorizontal: 12, marginBottom: 4,
    borderTopWidth: 1, borderTopColor: 'rgba(0,150,255,0.08)',
  },
  statusText: { fontSize: 7, color: COLORS.textDim, fontFamily: 'monospace', letterSpacing: 1 },
})
