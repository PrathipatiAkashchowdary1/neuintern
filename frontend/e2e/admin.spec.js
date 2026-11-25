import { test, expect } from '@playwright/test'
import { API, PNG_1X1, loginAsAdmin } from './helpers'

test.describe('admin portal', () => {
  test('every admin page opens', async ({ page }) => {
    await loginAsAdmin(page)
    const pages = [
      ['/admin', 'Dashboard'],
      ['/admin/students', 'Students'],
      ['/admin/programs', 'Courses'],
      ['/admin/payments', 'Payments'],
      ['/admin/invoice-settings', 'Invoice details'],
      ['/admin/messages', 'Contact Messages'],
      ['/admin/emails', 'Emails'],
    ]
    for (const [path, heading] of pages) {
      await page.goto(path)
      await expect(page.getByRole('heading', { level: 1, name: heading })).toBeVisible()
    }
  })

  test('add a program with an image, change its fee, then deactivate it', async ({ page }) => {
    const title = `E2E Program ${Date.now()}`
    const category = 'E2E Category'
    await loginAsAdmin(page)
    await page.goto('/admin/programs')

    // --- add it ---
    await page.getByRole('button', { name: 'Add Program' }).click()
    const dialog = page.getByRole('dialog')
    await dialog.getByLabel('Title', { exact: true }).fill(title)
    await expect(dialog.getByLabel(/Slug/)).toHaveValue(/^e2e-program-\d+$/) // suggested from the title
    await dialog.getByLabel('Category').fill(category)
    await dialog.getByLabel(/Certificate fee/).fill('321')
    await dialog.getByLabel('Tagline').fill('Created by the browser smoke test.')
    await dialog.getByLabel('Skills').fill('Playwright\nSmoke testing\n')
    await dialog.getByRole('button', { name: 'Add week' }).click()
    await dialog.getByLabel('Title', { exact: true }).last().fill('Week one')
    await dialog.getByLabel('Topics').fill('First topic\nSecond topic')

    // Upload an image through the real file input; the editor shows its stored URL.
    await dialog.getByLabel('Upload program image').setInputFiles({ name: 'banner.png', mimeType: 'image/png', buffer: PNG_1X1 })
    await expect(dialog.getByLabel('Or paste an image link')).toHaveValue(/\/uploads\/[0-9a-f]{32}\.png$/)

    await dialog.getByRole('button', { name: 'Create Program' }).click()
    await expect(dialog).toBeHidden()
    const row = page.getByRole('row', { name: new RegExp(title) })
    await expect(row).toContainText('₹321')
    await expect(row).toContainText(category)

    // --- the public site shows it, with its image, fee, skills and curriculum ---
    await page.goto(`/programs?category=${encodeURIComponent(category)}`)
    const card = page.locator('main a[href^="/programs/e2e-program-"]').first()
    await expect(card).toBeVisible()
    await expect(page.getByRole('button', { name: category })).toBeVisible() // the new category is a filter chip
    await expect(page.locator('main').getByText('₹321')).toBeVisible()
    const image = page.locator('main img[src*="/uploads/"]').first()
    await expect(image).toBeVisible()
    await expect.poll(() => image.evaluate((el) => el.naturalWidth)).toBeGreaterThan(0) // actually loaded

    await card.click()
    await expect(page.getByRole('heading', { level: 1, name: title })).toBeVisible()
    await expect(page.getByText('Playwright').first()).toBeVisible()
    await expect(page.getByText('Week one')).toBeVisible()
    await expect(page.getByText('First topic')).toBeVisible()

    // --- change the fee: the public page follows immediately ---
    await page.goto('/admin/programs')
    await page.getByRole('button', { name: `Edit ${title}` }).click()
    await page.getByRole('dialog').getByLabel(/Certificate fee/).fill('333')
    await page.getByRole('dialog').getByRole('button', { name: 'Save Changes' }).click()
    await expect(page.getByRole('row', { name: new RegExp(title) })).toContainText('₹333')
    await page.goto(`/programs?category=${encodeURIComponent(category)}`)
    await expect(page.locator('main').getByText('₹333')).toBeVisible()

    // --- deactivate: it disappears from the public catalog ---
    await page.goto('/admin/programs')
    await page.getByRole('button', { name: `Deactivate ${title}` }).click()
    await expect(page.getByRole('row', { name: new RegExp(title) })).toContainText('Inactive')
    await page.goto('/programs')
    await expect(page.getByText(title)).toHaveCount(0)
  })

  test('invoice details can be previewed and saved', async ({ page }) => {
    await loginAsAdmin(page)
    await page.goto('/admin/invoice-settings')
    const company = page.getByLabel('Company name')
    await expect(company).not.toHaveValue('')
    await company.fill('E2E Company Pvt. Ltd.')

    await page.getByRole('button', { name: 'Preview PDF' }).click()
    await expect(page.getByTitle('Invoice preview')).toBeVisible()

    await page.getByRole('button', { name: 'Save changes' }).click()
    await expect(page.getByText(/Saved\. New invoices will use these details/)).toBeVisible()
    await page.reload()
    await expect(page.getByLabel('Company name')).toHaveValue('E2E Company Pvt. Ltd.')

    // A character the PDF font cannot draw is refused on the form.
    await page.getByLabel('Company name').fill('हिन्दी कंपनी')
    await page.getByRole('button', { name: 'Save changes' }).click()
    await expect(page.getByText(/Only English\/Western characters/)).toBeVisible()
  })

  test('a contact message shows up under Messages and in the email queue', async ({ page, request }) => {
    const subject = `E2E message ${Date.now()}`
    const sent = await request.post(`${API}/contact`, {
      data: { name: 'Queue Tester', email: 'queue.tester@example.com', subject, message: 'Checking the admin Messages page and the email queue.' },
    })
    expect(sent.status()).toBe(201)

    await loginAsAdmin(page)
    await page.goto('/admin/messages')
    await expect(page.getByText(subject).first()).toBeVisible()

    await page.goto('/admin/emails')
    await expect(page.getByText(/New contact form message: E2E message/).first()).toBeVisible()
    await expect(page.getByText('Sent').first()).toBeVisible() // mail is "sent" (printed) in the test environment
  })
})
