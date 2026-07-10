import { io } from 'socket.io-client'

class SocketService {
  constructor() {
    this.socket = null
    this.connected = false
    this.authenticated = false
    this.listeners = {}
  }

  connect(serverUrl) {
    if (this.socket) {
      this.disconnect()
    }

    this.socket = io(serverUrl, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 2000,
      reconnectionDelayMax: 10000,
      timeout: 10000,

    })

    this.socket.on('connect', () => {
      this.connected = true
      this._emit('connection_change', { connected: true })
    })

    this.socket.on('disconnect', () => {
      this.connected = false
      this.authenticated = false
      this._emit('connection_change', { connected: false })
    })

    this.socket.on('connect_error', () => {
      this.connected = false
      this.authenticated = false
      this._emit('connection_change', { connected: false })
    })

    return this.socket
  }

  async authenticate(secret) {
    return new Promise((resolve) => {
      if (!this.socket || !this.socket.connected) {
        resolve({ success: false, error: 'Not connected' })
        return
      }

      const timeout = setTimeout(() => {
        resolve({ success: false, error: 'Auth timeout' })
      }, 5000)

      this.socket.once('auth_status', (data) => {
        clearTimeout(timeout)
        if (data && data.authenticated) {
          this.authenticated = true
          resolve({ success: true, ...data })
        } else {
          resolve({ success: false, error: data?.error || 'Auth failed' })
        }
      })

      this.socket.emit('mobile_auth', { secret })
    })
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = []
    }
    this.listeners[event].push(callback)
    if (this.socket) {
      this.socket.on(event, callback)
    }
  }

  off(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback)
    }
    if (this.socket) {
      this.socket.off(event, callback)
    }
  }

  emit(event, data) {
    if (this.socket) {
      this.socket.emit(event, data)
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.removeAllListeners()
      this.socket.disconnect()
      this.socket = null
    }
    this.connected = false
    this.authenticated = false
    this.listeners = {}
  }

  _emit(event, data) {
    const cbs = this.listeners[event] || []
    for (const cb of cbs) {
      cb(data)
    }
  }
}

const socketService = new SocketService()
export default socketService
