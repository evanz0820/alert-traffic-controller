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
const ring = await page.evaluate(() => {
  const css = getComputedStyle(document.activeElement)
  const outline =
    css.outlineStyle !== 'none' &&
    parseFloat(css.outlineWidth) > 0 &&
    !css.outlineColor.includes('0)')
  return outline || (css.boxShadow !== 'none' && css.boxShadow !== '')
})
check(ring, 'focused element shows a visible focus ring')

// Headless Chromium on macOS swallows Meta+K; the handler accepts Ctrl+K too.
await page.keyboard.press('Control+k')
await page.getByPlaceholder('Search customers or pages').fill('Abigail')
await page.keyboard.press('Enter')
await page.waitForURL(/customers\?id=/)
await page.getByRole('dialog').waitFor()
await page.waitForTimeout(600) // let the sheet finish opening before dismissing it
check(
  await page.getByRole('dialog').getByText('Abigail').first().isVisible(),
  'Cmd+K finds a customer and opens their sheet',
)
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
const filtered = page.waitForResponse(
  (r) => r.url().includes('/alerts?') && r.url().includes('outcome=SUPPRESSED'),
)
await page.getByRole('menuitemcheckbox', { name: 'Suppressed' }).click()
await page.keyboard.press('Escape')
await filtered
await page.waitForTimeout(200)
// Column 5 is the outcome badge; reason text may mention "suppressed" in other rows.
const outcomes = await page.locator('tbody tr td:nth-child(5)').allInnerTexts()
const rows = outcomes.length
const badges = outcomes.filter((t) => t.includes('Suppressed')).length
check(rows > 0 && badges === rows, `outcome filter shows only suppressed rows (${badges}/${rows})`)

await page.goto(BASE + '/rules', { waitUntil: 'networkidle' })
await page.getByRole('slider', { name: 'Alerts per day' }).focus()
await page.keyboard.press('ArrowLeft')
const simulated = page.waitForResponse((r) => r.url().includes('/simulate'))
await page.getByRole('button', { name: 'Run simulation' }).first().click()
const sim = await simulated
check(sim.status() === 200, 'Run simulation returns results')
// The panel goes old table -> skeleton -> new table, so poll rather than wait once.
const comparison = page.locator('main aside table thead')
let comparisonVisible = false
for (let i = 0; i < 40 && !comparisonVisible; i++) {
  await page.waitForTimeout(250)
  comparisonVisible = await comparison.isVisible()
}
check(comparisonVisible, 'comparison table shows previous vs current run')

const mobile = await browser.newContext({ viewport: { width: 390, height: 844 } })
const m = await mobile.newPage()
m.on('console', (msg) => msg.type() === 'error' && errors.push(msg.text().slice(0, 160)))
m.on('pageerror', (e) => errors.push(e.message))
await m.goto(BASE + '/', { waitUntil: 'networkidle' })
await m.getByRole('button', { name: 'Open menu' }).click()
await m.getByRole('link', { name: 'Alert Log' }).click()
await m.waitForURL(/\/log/)
const heading = m.getByRole('heading', { name: 'Alert Log' })
await heading.waitFor({ timeout: 5000 }).catch(() => {})
check(await heading.isVisible(), 'mobile menu navigates')

check(
  errors.length === 0,
  `no console errors during interactions${errors.length ? ': ' + errors.join(' | ') : ''}`,
)
await browser.close()
if (failures.length) {
  console.error(`\n${failures.length} QA check(s) failed`)
  process.exit(1)
}
