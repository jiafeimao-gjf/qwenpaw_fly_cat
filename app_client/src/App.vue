<template>
  <Login v-if="!auth.isLoggedIn()" @login-success="onLogin" />
  <ChatRoom v-else />
</template>

<script setup>
import { auth } from './stores/auth.js'
import Login from './components/Login.vue'
import ChatRoom from './components/ChatRoom.vue'

function onLogin() {
  // State is reactive, Vue will re-render
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  -webkit-tap-highlight-color: transparent;
}
html, body {
  width: 100%;
  height: 100%;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  touch-action: manipulation;
}
#app {
  width: 100%;
  height: 100%;
}
</style>