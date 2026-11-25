import { test, expect } from '@playwright/test'
import { createStudent, loginUi } from './helpers'

test.describe('student journey', () => {
  test('enroll, submit the task, reach the payment step, manage devices', async ({ page, request }) => {
    const student = await createStudent(request)
    await loginUi(page, student)
    await expect(page).toHaveURL(/\/dashboard/)

    // 1. Enroll (free) in the first program offered.
    await expect(page.getByText(/not enrolled in a program yet/i)).toBeVisible()
    await page.getByRole('button', { name: 'Enroll Now' }).first().click()
    await expect(page.getByText(/Internship Offer Letter/)).toBeVisible()

    // 2. Submit the task links.
    await page.locator('#githubLink').fill('https://github.com/example/e2e-project')
    await page.locator('#linkedinLink').fill('https://www.linkedin.com/in/e2e-student')
    await page.getByRole('button', { name: 'Submit Task' }).click()

    // 3. Payment step shows the admin-set fee (150 by default).
    const pay = page.getByRole('button', { name: /Pay ₹150/ })
    await expect(pay).toBeVisible()

    // Razorpay is deliberately not configured here, so checkout reports that instead of opening.
    await pay.click()
    await expect(page.getByText(/Payments are not configured/i)).toBeVisible()

    // 4. The devices panel lists this login.
    await expect(page.getByRole('heading', { name: 'Your devices' })).toBeVisible()
    await expect(page.getByText('This device')).toBeVisible()

    // 5. "Log out of all devices" really ends the session.
    await page.getByRole('button', { name: 'Log out of all devices' }).click()
    await page.getByRole('button', { name: 'Yes, log out everywhere' }).click()
    await expect(page).toHaveURL(/\/login/)
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/login/)
  })

  test('a second device can be logged out from the first', async ({ page, browser, request }) => {
    const student = await createStudent(request)

    // "Phone": a separate browser context with its own cookies and a phone user agent.
    const phoneContext = await browser.newContext({
      userAgent:
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
    })
    const phone = await phoneContext.newPage()
    await loginUi(phone, student)
    await expect(phone).toHaveURL(/\/dashboard/)

    // "Laptop": the main page.
    await loginUi(page, student)
    await expect(page).toHaveURL(/\/dashboard/)
    await expect(page.getByText('Safari on iOS')).toBeVisible()

    await page.getByRole('button', { name: 'Log out Safari on iOS' }).click()
    await expect(page.getByText('Safari on iOS')).toHaveCount(0)
    await expect(page).toHaveURL(/\/dashboard/) // this device is unaffected

    // The phone is now logged out for real.
    await phone.goto('/dashboard')
    await expect(phone).toHaveURL(/\/login/)
    await phoneContext.close()
  })
})
