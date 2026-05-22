import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0', // <--- AGREGA ESTA LÍNEA
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000', // Tu backend sigue siendo local respecto al servidor Vite
        changeOrigin: true,
        secure: false,
      }
    }
  }
})