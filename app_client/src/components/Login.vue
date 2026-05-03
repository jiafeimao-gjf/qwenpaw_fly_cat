<template>
  <div class="login-container">
    <div class="login-box">
      <h1>QwenPaw App</h1>
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label>Client ID</label>
          <input v-model="clientId" type="text" required autocomplete="off" />
        </div>
        <div class="form-group">
          <label>Client Secret</label>
          <input v-model="clientSecret" type="password" required autocomplete="off" />
        </div>
        <div class="form-group">
          <label>Username</label>
          <input v-model="username" type="text" required autocomplete="username" />
        </div>
        <div class="form-group">
          <label>Password</label>
          <input v-model="password" type="password" required autocomplete="current-password" />
        </div>
        <button type="submit" :disabled="loading">
          {{ loading ? 'Logging in...' : 'Login' }}
        </button>
        <p v-if="error" class="error">{{ error }}</p>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { client } from '../api/client.js'
import { auth } from '../stores/auth.js'

const clientId = ref(auth.clientId)
const clientSecret = ref(auth.clientSecret)
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

const emit = defineEmits(['login-success'])

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    const data = await client.login(clientId.value, clientSecret.value, username.value, password.value)
    auth.clientId = clientId.value
    auth.clientSecret = clientSecret.value
    auth.setTokens(data.access_token, data.refresh_token, data.expires_in, username.value)
    emit('login-success')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  min-height: 100dvh;
  background: #f5f5f5;
  padding: 1rem;
}
.login-box {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  width: 100%;
  max-width: 360px;
}
h1 {
  text-align: center;
  margin-bottom: 1.5rem;
  color: #333;
}
.form-group {
  margin-bottom: 1rem;
}
label {
  display: block;
  margin-bottom: 0.25rem;
  color: #666;
  font-size: 0.875rem;
}
input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  box-sizing: border-box;
  font-size: 16px;
}
button {
  width: 100%;
  padding: 0.875rem;
  background: #4a90e2;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  min-height: 44px;
}
button:disabled {
  background: #ccc;
}
.error {
  color: red;
  margin-top: 0.75rem;
  font-size: 0.875rem;
  text-align: center;
}
</style>