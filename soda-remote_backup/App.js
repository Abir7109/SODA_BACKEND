import React, { useState } from 'react'
import { View, StyleSheet, StatusBar } from 'react-native'
import { GestureHandlerRootView } from 'react-native-gesture-handler'
import MainScreen from './src/screens/MainScreen'
import ConnectionScreen from './src/screens/ConnectionScreen'

export default function App() {
  const [connected, setConnected] = useState(false)

  return (
    <GestureHandlerRootView style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor="#04080B" />
      {connected ? (
        <MainScreen onDisconnect={() => setConnected(false)} />
      ) : (
        <ConnectionScreen onConnected={() => setConnected(true)} />
      )}
    </GestureHandlerRootView>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#04080B' },
})
