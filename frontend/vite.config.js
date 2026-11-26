import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * A production build bakes the API address into the JavaScript. If it is missing, the site
 * would build "successfully" and then every request would silently go to the wrong place
 * (same-origin /api on the static host, which does not exist), or to a developer's localhost.
 * So a production build refuses to run unless it was given a real address.
 *
 * Provide it in frontend/.env.production (not committed) or as an environment variable:
 *   VITE_API_BASE_URL=https://api.neuintern.in/api
 * A same-origin path such as /api is also accepted (for when a proxy serves both).
 */
function assertApiAddress(env) {
  const value = (env.VITE_API_BASE_URL || '').trim()
  const fix =
    'Create frontend/.env.production containing  VITE_API_BASE_URL=https://api.your-domain/api  ' +
    '(or set that environment variable), then run the build again.'

  if (!value) throw new Error(`Production build stopped: VITE_API_BASE_URL is not set, so the site would not know where the API is.\n${fix}`)
  if (/localhost|127\.0\.0\.1|\[::1\]/i.test(value)) {
    throw new Error(`Production build stopped: VITE_API_BASE_URL is "${value}", a local address that visitors cannot reach.\n${fix}`)
  }
  if (!value.startsWith('https://') && !value.startsWith('/')) {
    throw new Error(`Production build stopped: VITE_API_BASE_URL "${value}" must start with https:// (or be a same-origin path like /api).\n${fix}`)
  }
}

// GoDaddy shared hosting: the site lives at the domain root, so assets resolve from "/".
export default defineConfig(({ mode }) => {
  if (mode === 'production') assertApiAddress(loadEnv(mode, process.cwd(), 'VITE_'))

  return {
    plugins: [react()],
    base: '/',
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
  }
})
