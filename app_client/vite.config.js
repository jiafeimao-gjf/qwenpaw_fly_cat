import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import os from 'os'

function getLanIp() {
  const interfaces = os.networkInterfaces()
  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name]) {
      if (iface.family === 'IPv4' && !iface.internal) {
        return iface.address
      }
    }
  }
  return '0.0.0.0'
}

export default defineConfig({
  plugins: [vue()],
  server: {
    host: process.env.HOST || getLanIp(),
    port: parseInt(process.env.PORT || '3000'),
    proxy: {
      '/api': {
        target: process.env.API_TARGET || 'http://localhost:8080',
        changeOrigin: true
      }
    }
  }
})