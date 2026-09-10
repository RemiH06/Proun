import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Local, un solo usuario: el frontend llega al backend por proxy, no
    // por CORS, así que no hay superficie de origen cruzado que configurar.
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
