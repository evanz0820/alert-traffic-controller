// Interaction + accessibility QA. Requires `make dev`.
//   node scripts/qa.mjs
import AxeBuilder from '@axe-core/playwright'
import { chromium } from '@playwright/test'

const BASE = process.env.ATC_WEB_URL ?? 'http://localhost:5173'
const PAGES = ['/', '/tower', '/rules', '/customers', '/customers?id=7', '/log', '/about']
const browser = await chromium.launch()
const failures = []
const check = (ok, label) => {
  console.log(`${ok ? '✓' : '✗'} ${label}`)
  if (!ok) failures.push(label)
}

// Accessibility: WCAG 2.1 A/AA rules on every page, both themes.
for (const theme of ['dark', 'light']) {
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    reducedMotion: 'reduce',
  })
  await ctx.addInitScript((t) => localStorage.setItem('atc-theme', t), theme)
  const page = await ctx.newPage()
  for (const path of PAGES) {
    await page.goto(BASE + path, { waitUntil: 'networkidle' })
    await page.waitForTimeout(700)
    const result = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze()
    const serious = result.violations.filter((v) =>
      ['serious', 'critical'].includes(v.impact ?? ''),
    )
    check(
      serious.length === 0,
      `axe ${theme} ${path}${serious.length ? ': ' + serious.map((v) => `${v.id} (${v.nodes.length}) ${v.nodes[0]?.target}`).join('; ') : ''}`,
    )
  }
  await ctx.close()
}

// Interactions.
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
const page = await ctx.newPage()
const errors = []
page.on('console', (m) => m.type() === 'error' && errors.push(m.text().slice(0, 160)))
page.on('pageerror', (e) => errors.push(e.message))

await page.goto(BASE + '/', { waitUntil: 'networkidle' })
await page.keyboard.press('Tab')
const skip = await page.evaluate(() => document.activeElement?.textContent)
check(skip?.includes('Skip to content'), 'first Tab focuses the skip link')
await page.keyboard.press('Tab')
const outline = await page.evaluate(() => getComputedStyle(document.activeElement).outlineStyle)
check(outline !== 'none', 'focused element shows a visible focus ring')

// Headless Chromium on macOS swallows Meta+K; the handler accepts Ctrl+K too.
await page.keyboard.press('Control+k')
await page.getByPlaceholder('Search customers or pages').fill('Abigail')
await page.keyboard.press('Enter')
await page.waitForURL(/customers\?id=/)
await page.getByRole('dialog').waitFor()
await page.waitForTimeout(600) // let the sheet finish opening before dismissing it
check(true, 'Cmd+K finds a customer and opens their sheet')
await page.keyboard.press('Escape')
await page.waitForTimeout(600)
check(!/id=/.test(page.url()), 'Escape closes the sheet and clears ?id=')

await page
  .getByRole('button', { name: /Switch to light mode/ })
  .first()
  .click()
check(
  !(await page.evaluate(() => document.documentElement.classList.contains('dark'))),
  'theme toggle switches to light',
)
await page
  .getByRole('button', { name: /Switch to dark mode/ })
  .first()
  .click()

await page.goto(BASE + '/log', { waitUntil: 'networkidle' })
await page.getByRole('button', { name: /^Outcome/ }).click()
await page.getByRole('menuitemcheckbox', { name: 'Suppressed' }).click()
await page.keyboard.press('Escape')
await page.waitForTimeout(600)
const badges = await page.locator('tbody tr', { hasText: 'Suppressed' }).count()
const rows = await page.locator('tbody tr').count()
check(rows > 0 && badges === rows, `outcome filter shows only suppressed rows (${badges}/${rows})`)

await page.goto(BASE + '/rules', { waitUntil: 'networkidle' })
await page.getByRole('slider', { name: 'Alerts per day' }).focus()
await page.keyboard.press('ArrowRight')
await page.getByRole('button', { name: 'Run simulation' }).first().click()
const sim = await page.waitForResponse((r) => r.url().includes('/simulate'))
check(sim.status() === 201, 'Run simulation creates a new run')
await page.waitForTimeout(1500)
check(
  (await page.getByText('This run against the one before').count()) === 1,
  'comparison panel renders',
)

const mobile = await browser.newContext({ viewport: { width: 390, height: 844 } })
const m = await mobile.newPage()
m.on('pageerror', (e) => errors.push(e.message))
await m.goto(BASE + '/', { waitUntil: 'networkidle' })
await m.getByRole('button', { name: 'Open menu' }).click()
await m.getByRole('link', { name: 'Alert Log' }).click()
await m.waitForURL(/\/log/)
check(true, 'mobile menu navigates')

check(
  errors.length === 0,
  `no console errors during interactions${errors.length ? ': ' + errors.join(' | ') : ''}`,
)
await browser.close()
if (failures.length) {
  console.error(`\n${failures.length} QA check(s) failed`)
  process.exit(1)
}
