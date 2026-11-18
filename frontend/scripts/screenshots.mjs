// Captures every dashboard page at desktop (1440px) and mobile (390px) widths,
// in dark (default) and light mode, and fails if any page logs a console error
// or scrolls horizontally. Requires `make dev` to be running.
//
//   node scripts/screenshots.mjs [--only overview,tower] [--light] [--out ../docs/screenshots]
import { mkdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { chromium } from '@playwright/test'

const BASE = process.env.ATC_WEB_URL ?? 'http://localhost:5173'
const args = process.argv.slice(2)
const flag = (name) => args.includes(`--${name}`)
const value = (name, fallback) => {
  const i = args.indexOf(`--${name}`)
  return i >= 0 ? args[i + 1] : fallback
}

const PAGES = [
  { name: 'overview', path: '/' },
  { name: 'tower', path: '/tower' },
  { name: 'rules-lab', path: '/rules' },
  { name: 'customers', path: '/customers' },
  { name: 'customer-sheet', path: '/customers?id=7' },
  { name: 'alert-log', path: '/log' },
  { name: 'about', path: '/about' },
]
const VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
]

const only = value('only', '')?.split(',').filter(Boolean)
const out = resolve(value('out', '../docs/screenshots'))
const themes = flag('light') ? ['dark', 'light'] : ['dark']
mkdirSync(out, { recursive: true })

const browser = await chromium.launch()
const problems = []

for (const theme of themes) {
  for (const vp of VIEWPORTS) {
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      deviceScaleFactor: 2,
      reducedMotion: 'reduce',
    })
    await context.addInitScript((t) => localStorage.setItem('atc-theme', t), theme)
    const page = await context.newPage()
    const errors = []
    page.on('console', (msg) => msg.type() === 'error' && errors.push(msg.text()))
    page.on('pageerror', (err) => errors.push(err.message))

    for (const target of PAGES.filter((p) => !only?.length || only.includes(p.name))) {
      errors.length = 0
      await page.goto(`${BASE}${target.path}`, { waitUntil: 'networkidle' })
      await page.waitForTimeout(target.name === 'tower' ? 2500 : 900)
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      )
      const file = `${target.name}-${vp.name}${theme === 'light' ? '-light' : ''}.png`
      await page.screenshot({ path: resolve(out, file), fullPage: true })
      const issues = [...errors]
      if (overflow > 0) issues.push(`horizontal overflow of ${overflow}px`)
      console.log(
        `${issues.length ? '✗' : '✓'} ${file}${issues.length ? ` — ${issues.join(' | ')}` : ''}`,
      )
      if (issues.length) problems.push({ file, issues })
    }
    await context.close()
  }
}

// Live Tower in motion (reduced motion is off here): a three-frame sequence for the README.
if (!only?.length || only.includes('tower')) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
  })
  await context.addInitScript(() => localStorage.setItem('atc-theme', 'dark'))
  const page = await context.newPage()
  await page.goto(`${BASE}/tower`, { waitUntil: 'networkidle' })
  const stage = page.getByRole('region', { name: 'Replay' })
  await page.getByRole('slider', { name: 'Replay speed' }).focus()
  await page.keyboard.press('ArrowRight') // 6 hr/s so the frames span several days
  for (const [i, wait] of [2500, 3500, 4500].entries()) {
    await page.waitForTimeout(wait)
    await stage.screenshot({ path: resolve(out, `tower-frame-${i + 1}.png`) })
    console.log(`✓ tower-frame-${i + 1}.png`)
  }
  await context.close()
}

await browser.close()
if (problems.length) {
  console.error(`\n${problems.length} screenshot(s) had problems.`)
  process.exit(1)
}
