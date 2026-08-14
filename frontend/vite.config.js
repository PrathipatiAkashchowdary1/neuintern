import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// GoDaddy shared hosting: relative base so assets resolve from any subfolder
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('framer-motion')) return 'motion'
            if (id.includes('swiper')) return 'swiper'
            if (id.includes('react-router-dom') || id.includes('/react/') || id.includes('/react-dom/')) {
              return 'vendor'
            }
          }
        },
      },
    },
  },
})
