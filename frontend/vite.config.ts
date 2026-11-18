import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  // Pre-bundle deps used only by lazy routes so Vite doesn't re-optimize mid-session
  // (which can load two copies of React until the page reloads).
  optimizeDeps: {
    include: ['@tanstack/react-table', 'recharts', 'motion/react', 'radix-ui', 'cmdk'],
  },
  server: {
    proxy: {
      '/api': {
        target: process.env.API_URL ?? 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
})
