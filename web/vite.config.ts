import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const railwayHost = 'coevo-production.up.railway.app'
const envAllowedHosts = (process.env.ALLOWED_HOSTS || '')
  .split(',')
  .map((h) => h.trim())
  .filter(Boolean)

const allowedHosts = Array.from(new Set([railwayHost, ...envAllowedHosts]))

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  },
  preview: {
    host: '0.0.0.0',
    port: Number(process.env.PORT || 4173),
    strictPort: true,
    allowedHosts
  }
})
