import { test, expect } from '@playwright/test'

test.describe('public site', () => {
  test('home page loads', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/NeuIntern/)
    await expect(page.getByRole('navigation').first()).toBeVisible()
  })

  test('programs are listed from the API with prices', async ({ page }) => {
    const problems = []
    page.on('console', (msg) => msg.type() === 'error' && problems.push(msg.text()))
    await page.goto('/programs')
    const cards = page.locator('main a[href^="/programs/"]')
    await expect(cards.first()).toBeVisible()
    expect(await cards.count()).toBeGreaterThan(5)
    await expect(page.getByText(/\d+ Programs? · 4 Weeks Each/)).toBeVisible()
    await expect(page.locator('main').getByText(/₹\s?\d/).first()).toBeVisible()
    expect(problems.filter((t) => /unique "key" prop/.test(t))).toEqual([]) // React list-key regression
  })

  test('the category filter narrows the list', async ({ page }) => {
    await page.goto('/programs')
    const cards = page.locator('main a[href^="/programs/"]')
    await expect(cards.first()).toBeVisible()
    const all = await cards.count()
    await page.getByRole('button', { name: 'Data & AI' }).click()
    await expect.poll(async () => cards.count()).toBeLessThan(all)
    expect(await cards.count()).toBeGreaterThan(0)
  })

  test('a program page shows its fee and an Enroll button', async ({ page }) => {
    await page.goto('/programs/web-development')
    await expect(page.getByRole('heading', { level: 1, name: 'Web Development' })).toBeVisible()
    await expect(page.getByText(/certificate fee after task completion/)).toBeVisible()
    await expect(page.getByRole('button', { name: /Enroll Now/ }).first()).toBeVisible()
  })

  test('an unknown program is a real 404 page', async ({ page }) => {
    await page.goto('/programs/this-program-does-not-exist')
    await expect(page.getByText('ERROR 404')).toBeVisible()
  })

  test('the contact form sends a message', async ({ page }) => {
    await page.goto('/contact')
    await page.getByLabel('Full name').fill('Smoke Tester')
    await page.getByLabel('Email', { exact: true }).fill('smoke.tester@example.com')
    await page.getByLabel('Subject', { exact: true }).fill('Smoke test message')
    await page.getByLabel('Message', { exact: true }).fill('This message was sent by the automated browser smoke test.')
    await page.getByRole('button', { name: 'Send Message' }).click()
    await expect(page.getByText(/Thanks for reaching out/)).toBeVisible()
  })

  test('the certificate checker reports an unknown certificate', async ({ page }) => {
    await page.goto('/certificate')
    await page.getByRole('textbox').first().fill('NI-0000-NOPE')
    await page.getByRole('button', { name: /verify/i }).first().click()
    await expect(page.getByText(/No certificate found/i)).toBeVisible()
  })
})
