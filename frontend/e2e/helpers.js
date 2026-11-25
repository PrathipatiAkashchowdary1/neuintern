import { expect } from '@playwright/test'

export const API = 'http://localhost:8010/api'
export const ADMIN = { email: 'info@neuintern.in', password: 'Admin@123' } // the seeded dev admin (README)
export const PASSWORD = 'Str0ngPass!99'

let counter = 0
export const uniqueEmail = (prefix = 'e2e') => `${prefix}.${Date.now()}.${++counter}@example.com`

/** Creates a verified student account through the API (fast), returning its credentials. */
export async function createStudent(request, { email = uniqueEmail('student'), password = PASSWORD, name = 'E2E Student' } = {}) {
  const sent = await request.post(`${API}/auth/send-otp`, { data: { email, purpose: 'register' } })
  expect(sent.ok()).toBeTruthy()
  const { devOtp } = await sent.json() // present because mail is not configured in the test environment
  const verified = await request.post(`${API}/auth/verify-otp`, { data: { email, otp: devOtp, purpose: 'register' } })
  expect(verified.ok()).toBeTruthy()
  const created = await request.post(`${API}/auth/register`, {
    data: { fullName: name, email, phone: '9876543210', degree: 'B.Tech', branch: 'CSE', currentYear: '3rd Year', password },
  })
  expect(created.status()).toBe(201)
  return { email, password, name }
}

export async function loginUi(page, { email, password }) {
  await page.goto('/login')
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByRole('button', { name: /^Log In/ }).click()
}

export async function loginAsAdmin(page) {
  await loginUi(page, ADMIN)
  await expect(page).toHaveURL(/\/admin/)
}

// A tiny valid PNG (1x1) for image-upload tests.
export const PNG_1X1 = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  'base64'
)
