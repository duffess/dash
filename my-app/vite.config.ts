import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  server: {
    host: 'localhost',
    port: 3000,
    hmr: {
      host: 'localhost',
      port: 3000,
    },
  },
  preview: {
    host: 'localhost',
    port: 3000,
    strictPort: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
