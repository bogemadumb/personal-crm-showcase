import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// Дев-сервер ходит в локальный FastAPI; SPA обращается к серверу только через /api.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: { '/api': { target: process.env.API_URL ?? 'http://127.0.0.1:8000', changeOrigin: false } },
  },
  build: { sourcemap: 'hidden', chunkSizeWarningLimit: 800 },
})
