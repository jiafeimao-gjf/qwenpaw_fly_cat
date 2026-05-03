<template>
  <div class="chat-room">
    <header class="chat-header">
      <button class="menu-btn" @click="toggleSidebar" v-if="isMobile">☰</button>
      <span>QwenPaw Chat</span>
      <button @click="handleLogout">Logout</button>
    </header>
    <div class="main-content">
      <aside class="sessions-sidebar" :class="{ open: sidebarOpen }">
        <div class="session-header">
          <span class="session-title">Sessions</span>
          <button class="close-btn" @click="sidebarOpen = false" v-if="isMobile">×</button>
        </div>
        <div
          v-for="session in sessions"
          :key="session.session_id"
          class="session-item"
          :class="{ active: currentSession === session.session_id }"
          @click="selectSession(session.session_id)"
        >
          <div class="session-preview">{{ session.last_message || '(empty)' }}</div>
          <div class="session-time">{{ formatTime(session.last_timestamp) }}</div>
        </div>
      </aside>
      <div class="sidebar-overlay" v-if="sidebarOpen && isMobile" @click="sidebarOpen = false"></div>
      <div class="chat-area">
        <div class="messages" ref="messagesEl">
          <MessageBubble
            v-for="(msg, idx) in messages"
            :key="idx"
            :content="msg.content"
            :is-user="msg.isUser"
            :timestamp="msg.timestamp"
          />
          <div v-if="messages.length === 0" class="empty-hint">
            No messages yet. Start a conversation!
          </div>
        </div>
        <form class="input-area" @submit.prevent="handleSend">
          <input v-model="inputText" type="text" placeholder="Type your message..." :disabled="sending" />
          <button type="submit" :disabled="sending || !inputText.trim()">
            {{ sending ? '...' : 'Send' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import MessageBubble from './MessageBubble.vue'
import { client } from '../api/client.js'
import { auth } from '../stores/auth.js'

const messages = ref([])
const sessions = ref([])
const currentSession = ref(null)
const inputText = ref('')
const sending = ref(false)
const loading = ref(false)
const messagesEl = ref(null)
const sidebarOpen = ref(false)
let pollInterval = null
const pendingMessages = new Map()

const isMobile = computed(() => window.innerWidth <= 768)

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  })
}

async function loadHistory() {
  loading.value = true
  try {
    const data = await client.getHistory(auth.accessToken, currentSession.value)
    messages.value = data.messages.map(m => ({
      content: m.text,
      isUser: m.is_user,
      timestamp: m.timestamp,
    }))
    scrollToBottom()
  } catch (e) {
    console.error('Load history failed:', e)
  } finally {
    loading.value = false
  }
}

async function loadSessions() {
  try {
    const data = await client.getSessions(auth.accessToken)
    sessions.value = data.sessions
  } catch (e) {
    console.error('Load sessions failed:', e)
  }
}

async function selectSession(sessionId) {
  currentSession.value = sessionId
  sidebarOpen.value = false
  await loadHistory()
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || sending.value) return
  sending.value = true
  inputText.value = ''
  const userMsg = { content: text, isUser: true, timestamp: Date.now() / 1000 }
  messages.value.push(userMsg)
  scrollToBottom()
  try {
    const result = await client.submitMessage(text, auth.accessToken, currentSession.value)
    pendingMessages.set(result.message_id, { isUser: false, content: '' })
    if (!currentSession.value) {
      await loadSessions()
    }
    startPolling()
  } catch (e) {
    messages.value.push({ content: 'Error: ' + e.message, isUser: false, timestamp: Date.now() / 1000 })
  } finally {
    sending.value = false
    scrollToBottom()
  }
}

async function pollResponses() {
  if (pendingMessages.size === 0) return
  for (const [messageId, msgData] of pendingMessages) {
    try {
      const result = await client.getResponse(messageId, auth.accessToken)
      if (result.response !== null) {
        msgData.content = result.response
        pendingMessages.delete(messageId)
        const msgIndex = messages.value.findIndex(m => !m.isUser && !m.content)
        if (msgIndex >= 0) {
          messages.value[msgIndex] = { ...msgData, timestamp: Date.now() / 1000 }
        } else {
          messages.value.push({ ...msgData, timestamp: Date.now() / 1000 })
        }
        scrollToBottom()
      }
    } catch (e) {
      console.error('Poll error:', e)
    }
  }
  if (pendingMessages.size === 0) {
    stopPolling()
  }
}

function startPolling() {
  if (pollInterval) return
  pollInterval = setInterval(pollResponses, 5000)
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  return new Date(timestamp * 1000).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function handleLogout() {
  stopPolling()
  auth.clear()
}

onMounted(async () => {
  await loadSessions()
  await loadHistory()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.chat-room {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  background: #f9f9f9;
}
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: #4a90e2;
  color: white;
  font-weight: bold;
  min-height: 44px;
}
.menu-btn {
  background: none;
  border: none;
  color: white;
  font-size: 1.5rem;
  padding: 0.25rem;
  margin-right: 0.5rem;
}
.chat-header button {
  padding: 0.4rem 0.75rem;
  background: rgba(255,255,255,0.2);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
}
.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
  position: relative;
}
.sessions-sidebar {
  width: 200px;
  background: #f0f0f0;
  border-right: 1px solid #ddd;
  overflow-y: auto;
  padding: 0.5rem;
  flex-shrink: 0;
}
.session-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.session-title {
  font-size: 0.75rem;
  color: #666;
  padding: 0.5rem 0.25rem;
  font-weight: bold;
}
.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #666;
  padding: 0 0.5rem;
}
.session-item {
  padding: 0.75rem 0.5rem;
  cursor: pointer;
  border-radius: 4px;
  margin-bottom: 0.25rem;
}
.session-item:hover {
  background: #e0e0e0;
}
.session-item.active {
  background: #4a90e2;
  color: white;
}
.session-preview {
  font-size: 0.875rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.session-time {
  font-size: 0.625rem;
  opacity: 0.7;
  margin-top: 0.25rem;
}
.sidebar-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.3);
  z-index: 10;
}
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  -webkit-overflow-scrolling: touch;
}
.empty-hint {
  text-align: center;
  color: #999;
  margin-top: 2rem;
}
.input-area {
  display: flex;
  padding: 0.75rem;
  background: white;
  border-top: 1px solid #eee;
}
.input-area input {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  margin-right: 0.5rem;
  font-size: 16px;
  min-height: 44px;
}
.input-area button {
  padding: 0.75rem 1.25rem;
  background: #4a90e2;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.875rem;
  min-height: 44px;
}
.input-area button:disabled {
  background: #ccc;
}
@media (max-width: 768px) {
  .sessions-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: 75%;
    max-width: 280px;
    z-index: 20;
    transform: translateX(-100%);
    transition: transform 0.2s ease;
  }
  .sessions-sidebar.open {
    transform: translateX(0);
  }
  .session-item {
    padding: 1rem 0.75rem;
  }
  .input-area input {
    font-size: 16px;
  }
  .messages {
    padding: 0.75rem;
  }
}
</style>