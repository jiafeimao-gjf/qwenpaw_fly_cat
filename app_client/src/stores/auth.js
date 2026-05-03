import { reactive } from 'vue'

const STORAGE_KEY = 'app_auth'

function loadFromStorage() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored ? JSON.parse(stored) : null
  } catch {
    return null
  }
}

function saveToStorage(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
}

function clearStorage() {
  localStorage.removeItem(STORAGE_KEY)
}

export const auth = reactive({
  accessToken: null,
  refreshToken: null,
  expiresIn: null,
  username: null,
  clientId: 'qwenpaw-client',
  clientSecret: 'change-me-in-production',

  init() {
    const stored = loadFromStorage()
    if (stored) {
      this.accessToken = stored.accessToken
      this.refreshToken = stored.refreshToken
      this.expiresIn = stored.expiresIn
      this.username = stored.username
    }
  },

  setTokens(accessToken, refreshToken, expiresIn, username) {
    this.accessToken = accessToken
    this.refreshToken = refreshToken
    this.expiresIn = expiresIn
    this.username = username
    saveToStorage({ accessToken, refreshToken, expiresIn, username })
  },

  clear() {
    this.accessToken = null
    this.refreshToken = null
    this.expiresIn = null
    this.username = null
    clearStorage()
  },

  isLoggedIn() {
    return !!this.accessToken
  }
})

auth.init()