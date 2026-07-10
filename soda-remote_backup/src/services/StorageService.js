import AsyncStorage from '@react-native-async-storage/async-storage'

const KEYS = {
  SERVER_URL: '@soda_server_url',
  SECRET: '@soda_secret',
  TUNNEL_URL: '@soda_tunnel_url',
}

class StorageService {
  async saveConnection(serverUrl, secret) {
    try {
      await AsyncStorage.multiSet([
        [KEYS.SERVER_URL, serverUrl],
        [KEYS.SECRET, secret],
      ])
    } catch (e) {
      console.warn('Save connection error:', e)
    }
  }

  async getConnection() {
    try {
      const values = await AsyncStorage.multiGet([KEYS.SERVER_URL, KEYS.SECRET])
      const url = values[0][1]
      const secret = values[1][1]
      if (url && secret) {
        return { serverUrl: url, secret }
      }
      return null
    } catch (e) {
      console.warn('Get connection error:', e)
      return null
    }
  }

  async clearConnection() {
    try {
      await AsyncStorage.multiRemove([KEYS.SERVER_URL, KEYS.SECRET])
    } catch (e) {
      console.warn('Clear connection error:', e)
    }
  }

  async saveTunnelUrl(url) {
    try {
      await AsyncStorage.setItem(KEYS.TUNNEL_URL, url)
    } catch (e) {
      console.warn('Save tunnel URL error:', e)
    }
  }

  async getTunnelUrl() {
    try {
      return await AsyncStorage.getItem(KEYS.TUNNEL_URL)
    } catch (e) {
      console.warn('Get tunnel URL error:', e)
      return null
    }
  }
}

const storageService = new StorageService()
export default storageService
