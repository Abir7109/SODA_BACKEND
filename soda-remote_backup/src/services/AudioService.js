import { Audio } from 'expo-av'

class AudioService {
  constructor() {
    this.recording = null
    this.isRecording = false
    this.onAudioData = null
  }

  async init() {
    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        staysActiveInBackground: true,
        shouldDuckAndroid: true,
        playThroughEarpieceAndroid: false,
      })
    } catch (e) {
      console.warn('Audio init error:', e)
    }
  }

  async startRecording() {
    try {
      const { granted } = await Audio.requestPermissionsAsync()
      if (!granted) {
        throw new Error('Microphone permission denied')
      }

      this.recording = new Audio.Recording()
      await this.recording.prepareToRecordAsync({
        isMeteringEnabled: false,
        android: {
          extension: '.wav',
          outputFormat: Audio.AndroidOutputFormat.PCM_16BIT,
          audioEncoder: Audio.AndroidAudioEncoder.PCM_16BIT,
          sampleRate: 24000,
          numberOfChannels: 1,
          bitRate: 384000,
        },
        ios: {
          extension: '.wav',
          outputFormat: Audio.IOSOutputFormat.LINEARPCM,
          audioQuality: Audio.IOSAudioQuality.MAX,
          sampleRate: 24000,
          numberOfChannels: 1,
          bitRate: 384000,
          linearPCMBitDepth: 16,
          linearPCMIsBigEndian: false,
          linearPCMIsFloat: false,
        },
      })

      await this.recording.startAsync()
      this.isRecording = true
    } catch (e) {
      console.error('Start recording error:', e)
      this.isRecording = false
      throw e
    }
  }

  async stopRecording(stripHeader = true) {
    if (!this.recording) return null

    try {
      await this.recording.stopAndUnloadAsync()
      const uri = this.recording.getURI()
      this.recording = null
      this.isRecording = false

      if (!uri) return null

      const response = await fetch(uri)
      const blob = await response.blob()
      const base64 = await new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => {
          const dataUrl = reader.result
          resolve(dataUrl.split(',')[1])
        }
        reader.onerror = reject
        reader.readAsDataURL(blob)
      })

      let bytes = Uint8Array.from(atob(base64), (c) => c.charCodeAt(0))
      if (stripHeader && bytes.length > 44) {
        bytes = bytes.slice(44)
      }

      let binary = ''
      for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i])
      }
      return btoa(binary)
    } catch (e) {
      console.error('Stop recording error:', e)
      this.recording = null
      this.isRecording = false
      return null
    }
  }

  async startSend() {
    return this.startRecording()
  }

  async stopSend() {
    return this.stopRecording(true)
  }

  async playAudio(base64Data, onEnd) {
    try {
      const sound = new Audio.Sound()
      const uri = `data:audio/wav;base64,${base64Data}`
      await sound.loadAsync({ uri })
      await sound.playAsync()
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.didJustFinish) {
          sound.unloadAsync()
          if (onEnd) onEnd()
        }
      })
    } catch (e) {
      console.warn('Play audio error:', e)
    }
  }
}

const audioService = new AudioService()
export default audioService
