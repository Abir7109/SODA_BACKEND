import React, { useRef, useEffect } from 'react'
import { View, Text, FlatList, StyleSheet } from 'react-native'
import { COLORS } from '../constants/colors'

export default function TranscriptionFeed({ entries }) {
  const listRef = useRef(null)

  useEffect(() => {
    if (entries.length > 0) {
      setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 50)
    }
  }, [entries.length])

  const renderItem = ({ item }) => {
    const isUser = item.sender === 'User'
    return (
      <View style={[styles.entry, isUser ? styles.entryUser : styles.entrySoda]}>
        <Text style={[styles.sender, { color: isUser ? COLORS.accent : COLORS.textSecondary }]}>
          {isUser ? 'YOU' : 'SODA'}
        </Text>
        <Text style={[styles.text, { color: isUser ? COLORS.accent : COLORS.textPrimary }]}>
          {item.text}
        </Text>
      </View>
    )
  }

  if (entries.length === 0) {
    return (
      <View style={styles.emptyContainer}>
        {[0, 1, 2].map((i) => (
          <View key={i} style={[styles.emptyLine, { width: `${60 + i * 20}%` }]} />
        ))}
        <Text style={styles.emptyText}>HOLD THE ORB TO SPEAK</Text>
      </View>
    )
  }

  return (
    <FlatList
      ref={listRef}
      data={entries}
      renderItem={renderItem}
      keyExtractor={(_, i) => String(i)}
      contentContainerStyle={styles.list}
      showsVerticalScrollIndicator={false}
      maxToRenderPerBatch={10}
    />
  )
}

const styles = StyleSheet.create({
  list: {
    paddingHorizontal: 20,
    paddingBottom: 4,
  },
  entry: {
    marginBottom: 5,
    maxWidth: '88%',
  },
  entryUser: {
    alignSelf: 'flex-end',
    alignItems: 'flex-end',
  },
  entrySoda: {
    alignSelf: 'flex-start',
    alignItems: 'flex-start',
  },
  sender: {
    fontSize: 7, fontWeight: '700', letterSpacing: 2,
    marginBottom: 1,
  },
  text: {
    fontSize: 11, lineHeight: 16,
    fontFamily: 'monospace',
  },
  emptyContainer: {
    flex: 1, justifyContent: 'center',
    alignItems: 'center', paddingHorizontal: 40, gap: 6,
  },
  emptyLine: {
    height: 1, backgroundColor: COLORS.accentBorder,
    borderRadius: 0.5,
  },
  emptyText: {
    fontSize: 7, fontWeight: '600', color: COLORS.textDim,
    letterSpacing: 3, marginTop: 12,
  },
})
