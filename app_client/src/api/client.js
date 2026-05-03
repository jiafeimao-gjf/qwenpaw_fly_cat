const API_BASE = '/api'

export const client = {
  async login(clientId, clientSecret, username, password) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ client_id: clientId, client_secret: clientSecret, username, password })
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Login failed')
    }
    return res.json()
  },

  async refresh(clientId, clientSecret, refreshToken) {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ client_id: clientId, client_secret: clientSecret, refresh_token: refreshToken })
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Refresh failed')
    }
    return res.json()
  },

  async submitMessage(text, accessToken, sessionId = null) {
    const res = await fetch(`${API_BASE}/messages/submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({ text, session_id: sessionId })
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Submit failed')
    }
    return res.json()
  },

  async getResponse(messageId, accessToken) {
    const res = await fetch(`${API_BASE}/messages/response/${messageId}`, {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Get response failed')
    }
    return res.json()
  },

  async getHistory(accessToken, sessionId = null, limit = 50) {
    let url = `${API_BASE}/messages/history?limit=${limit}`
    if (sessionId) url += `&session_id=${encodeURIComponent(sessionId)}`
    const res = await fetch(url, {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Get history failed')
    }
    return res.json()
  },

  async getSessions(accessToken) {
    const res = await fetch(`${API_BASE}/messages/sessions`, {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Get sessions failed')
    }
    return res.json()
  }
}