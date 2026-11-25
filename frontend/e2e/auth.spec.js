import { test, expect } from '@playwright/test'
import { PASSWORD, createStudent, loginUi, uniqueEmail } from './helpers'

test.describe('sign up, log in, log out', () => {
  test('a new student can register with an emailed code and lands on the dashboard', async ({ page }) => {
    const email = uniqueEmail('signup')
    await page.goto('/register')

    await page.getByLabel('Email', { exact: true }).fill(email)
    await page.getByRole('button', { name: /Send Verification Code/ }).click()

    // Mail is not configured in the test environment, so the code is shown (and pre-filled) on screen.
    await expect(page.getByText(/your code is/)).toBeVisible()
    await page.getByRole('button', { name: /Verify Email/ }).click()

    await page.getByLabel('Full name').fill('Signup Tester')
    await page.getByLabel('Phone number').fill('9876543210')
    await page.getByLabel('Degree').selectOption('B.Tech')
    await page.getByLabel('Branch / Stream').fill('Computer Science')
    await page.getByLabel('Current year').selectOption('3rd Year')
    await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
    await page.getByRole('button', { name: /Create Account/ }).click()

    await expect(page).toHaveURL(/\/dashboard/)
    await expect(page.getByRole('heading', { name: /Welcome, Signup/ })).toBeVisible()
    await expect(page.getByText(email)).toBeVisible()
  })

  test('a password shorter than 8 characters is rejected on the form', async ({ page }) => {
    const registerCalls = []
    page.on('request', (req) => req.url().endsWith('/auth/register') && registerCalls.push(req.url()))
    await page.goto('/register')
    await page.getByLabel('Email', { exact: true }).fill(uniqueEmail('short'))
    await page.getByRole('button', { name: /Send Verification Code/ }).click()
    await page.getByRole('button', { name: /Verify Email/ }).click()
    await page.getByLabel('Full name').fill('Short Pass')
    await page.getByLabel('Phone number').fill('9876543210')
    await page.getByLabel('Degree').selectOption('B.Tech')
    await page.getByLabel('Branch / Stream').fill('CSE')
    await page.getByLabel('Current year').selectOption('3rd Year')
    await page.getByLabel('Password', { exact: true }).fill('abc1234') // 7 characters
    await page.getByRole('button', { name: /Create Account/ }).click()
    await expect(page.getByText('Password must be at least 8 characters')).toBeVisible()
    await expect(page).toHaveURL(/\/register/)
    // The FORM stops it: the server's identical message would otherwise hide a form that says 6.
    expect(registerCalls).toEqual([])
  })

  test('log in, stay logged in across a reload, then log out', async ({ page, request }) => {
    const student = await createStudent(request)
    await loginUi(page, student)
    await expect(page).toHaveURL(/\/dashboard/)

    await page.reload()
    await expect(page).toHaveURL(/\/dashboard/) // the httpOnly cookie session survives
    expect(await page.evaluate(() => document.cookie)).not.toContain('neuintern_session') // scripts cannot read it
    expect(await page.evaluate(() => Object.keys(localStorage).filter((k) => /token/i.test(k)))).toEqual([])

    await page.getByRole('button', { name: 'Logout' }).first().click()
    await expect(page).toHaveURL(/\/login|\/$/)
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/login/) // really logged out
  })

  test('a wrong password shows an error', async ({ page, request }) => {
    const student = await createStudent(request)
    await loginUi(page, { email: student.email, password: 'definitely-wrong' })
    await expect(page.getByText('Invalid email or password')).toBeVisible()
    await expect(page).toHaveURL(/\/login/)
  })

  test('five wrong passwords lock the account for a while', async ({ page, request }) => {
    const student = await createStudent(request)
    for (let i = 0; i < 5; i++) await request.post('http://localhost:8010/api/auth/login', { data: { email: student.email, password: `wrong-${i}` } })
    await loginUi(page, student) // even the RIGHT password is refused while locked
    await expect(page.getByText(/Too many failed attempts/)).toBeVisible()
  })

  test('a forgotten password can be reset, and the old one stops working', async ({ page, request }) => {
    const student = await createStudent(request)
    const newPassword = 'BrandNewPass!77'

    await page.goto('/forgot-password')
    await page.getByLabel('Email', { exact: true }).fill(student.email)
    await page.getByRole('button', { name: /Send Reset Code/ }).click()
    await expect(page.getByText(/your code is/)).toBeVisible()
    await page.getByLabel('New password', { exact: true }).fill(newPassword)
    await page.getByLabel('Confirm new password').fill(newPassword)
    await page.getByRole('button', { name: /Reset Password/ }).click()
    await expect(page).toHaveURL(/\/login/)

    await loginUi(page, { email: student.email, password: student.password })
    await expect(page.getByText('Invalid email or password')).toBeVisible()
    await loginUi(page, { email: student.email, password: newPassword })
    await expect(page).toHaveURL(/\/dashboard/)
  })
})

test.describe('access control', () => {
  test('anonymous visitors are sent to the login page', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/login/)
    await page.goto('/admin')
    await expect(page).toHaveURL(/\/login/)
  })

  test('a student cannot open the admin area', async ({ page, request }) => {
    await loginUi(page, await createStudent(request))
    await expect(page).toHaveURL(/\/dashboard/)
    await page.goto('/admin/programs')
    await expect(page).toHaveURL(/\/dashboard/)
  })
})
