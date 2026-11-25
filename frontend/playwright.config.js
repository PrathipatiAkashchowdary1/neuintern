import { defineConfig, devices } from '@playwright/test'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

/**
 * Browser smoke tests. `npm run e2e` starts its OWN backend and frontend on separate ports
 * (8010 / 5180) with a throwaway database, so it never touches your dev servers or data.
 *
 * Locally on Windows it drives the Microsoft Edge that is already installed (no browser
 * download). Elsewhere, and in CI, install Chromium once with `npx playwright install chromium`.
 * Override with PW_CHANNEL (for example PW_CHANNEL=chrome), or PW_CHANNEL= to use bundled Chromium.
 */

const here = path.dirname(fileURLToPath(import.meta.url))
const BACKEND_PORT = 8010
const FRONTEND_PORT = 5180
const API = `http://localhost:${BACKEND_PORT}`
const SITE = `http://localhost:${FRONTEND_PORT}`

// One fresh database per run. Set on first load so test workers (which reload this file) agree.
process.env.E2E_RUN_ID ??= String(Date.now())
const runId = process.env.E2E_RUN_ID
const dbFile = path.join(os.tmpdir(), `neuintern-e2e-${runId}.db`).replace(/\\/g, '/')
const uploadDir = path.join(os.tmpdir(), `neuintern-e2e-uploads-${runId}`)

const channel = process.env.PW_CHANNEL ?? (process.platform === 'win32' && !process.env.CI ? 'msedge' : undefined)

export default defineConfig({
  testDir: './e2e',
  // The flows share one database and build on seeded data, so run them one at a time.
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : [['list']],
  use: {
    baseURL: SITE,
    channel: channel || undefined,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    viewport: { width: 1280, height: 800 },
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], channel: channel || undefined } }],
  webServer: [
    {
      // Apply migrations to the fresh database, then serve the API.
      command: `${process.env.E2E_PYTHON || 'python'} -m alembic upgrade head && ${process.env.E2E_PYTHON || 'python'} -m uvicorn app.main:app --port ${BACKEND_PORT}`,
      cwd: path.join(here, '..', 'backend'),
      url: `${API}/api/health`,
      timeout: 120_000,
      reuseExistingServer: false,
      env: {
        ENVIRONMENT: 'development', // keeps the seeded dev admin and the on-screen dev OTP
        DATABASE_URL: `sqlite:///${dbFile}`,
        UPLOAD_DIR: uploadDir,
        JWT_SECRET: 'e2e-only-secret-not-for-production',
        CORS_ORIGIN: SITE,
        // Nothing external is ever contacted: mail is printed to the log, payments are off.
        SMTP_HOST: '',
        SMTP_USER: '',
        SMTP_PASSWORD: '',
        RAZORPAY_KEY_ID: '',
        RAZORPAY_KEY_SECRET: '',
        RAZORPAY_WEBHOOK_SECRET: '',
        REMINDERS_ENABLED: 'false',
        RATE_LIMIT_ENABLED: 'false', // the tests make many sign-up/login requests from one address
        API_PUBLIC_URL: '',
        PYTHONUNBUFFERED: '1',
      },
    },
    {
      command: `npx vite --port ${FRONTEND_PORT} --strictPort`,
      cwd: here,
      url: SITE,
      timeout: 120_000,
      reuseExistingServer: false,
      env: { VITE_API_BASE_URL: `${API}/api` },
    },
  ],
})
