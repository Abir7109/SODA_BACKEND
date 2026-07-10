import React from 'react'
import {
  TouchableOpacity,
  Text,
  StyleSheet,
  Dimensions,
} from 'react-native'
import { COLORS } from '../constants/colors'

const { width: SCREEN_WIDTH } = Dimensions.get('window')

export default function OptionNode({ label, color, position, onPress, animatedStyle }) {
  return (
    <TouchableOpacity
      style={[
        styles.node,
        { borderColor: color },
        animatedStyle,
      ]}
      onPress={onPress}
      activeOpacity={0.7}
    >
      <Text style={[styles.label, { color }]}>{label}</Text>
    </TouchableOpacity>
  )
}

const styles = StyleSheet.create({
  node: {
    position: 'absolute',
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: 'rgba(4, 8, 11, 0.9)',
    borderWidth: 1,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#00fbfb',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 5,
  },
  label: {
    fontSize: 8,
    fontWeight: '700',
    letterSpacing: 2,
    textAlign: 'center',
  },
})
