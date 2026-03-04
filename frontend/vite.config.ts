import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    exclude: ['pdfjs-dist'],
  },
  worker: {
    format: 'es',
  },
  resolve: {
    alias: {
      // Убеждаемся, что pdfjs-dist правильно резолвится
    },
  },
  server: {
    fs: {
      // Разрешаем доступ к node_modules для worker
      allow: ['..'],
    },
  },
})

