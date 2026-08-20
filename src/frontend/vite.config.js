import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    // Proxy API calls tới backend ASP.NET Core
    proxy: {
      '/api': {
        target: 'http://localhost:5134',
        changeOrigin: true,
      },
    },
  },
})
