import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // Listen on all addresses for mobile testing on LAN
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8080', // Connect to FastAPI backend
        changeOrigin: true,
        secure: false,
      }
    }
  }
})
