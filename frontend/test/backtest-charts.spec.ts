import { expect, test } from '@playwright/test'
import type { Locator, Page } from '@playwright/test'
import type { BacktestResponse } from '../src/api/backtests'

const result: BacktestResponse = {
  start_cash: 1000,
  end_cash: 800,
  end_value: 1020,
  total_return: 2,
  CAGR: 5,
  sharpe: null,
  closed_trades: 0,
  max_drawdown: 30 / 1050 * 100,
  history: [
    { time: '2024-01-04T00:00:00', close: 100, cash: 1000, equity: 1000, drawdown: 0 },
    { time: '2024-01-05T00:00:00', close: 90, cash: 800, equity: 980, drawdown: 2 },
    { time: '2024-01-08T00:00:00', close: 125, cash: 800, equity: 1050, drawdown: 0 },
    { time: '2024-01-09T00:00:00', close: 110, cash: 800, equity: 1020, drawdown: 30 / 1050 * 100 },
  ],
}

async function showResults(page: Page, response: BacktestResponse = result) {
  await page.route('**/api/strategies', (route) => route.fulfill({ json: [{
    class_name: 'BuyAndHold', name: 'Buy and hold', description: 'Buy once and hold.', parameters: [],
  }] }))
  await page.route('**/api/backtests/run-backtest', (route) => route.fulfill({ json: response }))
  await page.goto('/backtesting')
  await page.getByRole('button', { name: 'Run backtest' }).click()
  await expect(page.getByText('Backtest complete')).toBeVisible()
}

async function expectVisiblePlot(chart: Locator) {
  await expect(chart).toBeVisible()
  const geometry = await chart.evaluate((svg) => {
    const circle = svg.querySelector('circle')!
    const bounds = svg.getBoundingClientRect()
    const point = circle.getBoundingClientRect()
    return {
      pathsAreFinite: [...svg.querySelectorAll('path')].every((path) => !/NaN|Infinity/.test(path.getAttribute('d')!)),
      pointIsVisible: point.left >= bounds.left && point.right <= bounds.right
        && point.top >= bounds.top && point.bottom <= bounds.bottom,
    }
  })
  expect(geometry).toEqual({ pathsAreFinite: true, pointIsVisible: true })
}

test('shows equity, percentage drawdown, and the initial cash reference', async ({ page }) => {
  await showResults(page)

  await expectVisiblePlot(page.getByRole('img', { name: 'Portfolio equity', exact: true }))
  await expectVisiblePlot(page.getByRole('img', { name: 'Drawdown', exact: true }))
  await expect(page.getByText('Initial cash: 1,000', { exact: true })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Portfolio equity', exact: true }).locator('.chart-value strong')).toHaveText('1,020')
  await expect(page.getByRole('region', { name: 'Drawdown', exact: true }).locator('.chart-value strong')).toHaveText('2.86%')
  await expect(page.getByRole('slider')).toHaveAttribute('max', '3')
  await expect(page.getByRole('slider')).toHaveValue('3')
  await page.locator('.backtest-results').screenshot({ path: test.info().outputPath('desktop-results.png') })
})

test('keyboard inspection synchronizes charts and preserves daily labels across weekends and timezones', async ({ page }) => {
  await showResults(page)
  const slider = page.getByRole('slider', { name: 'Inspect a trading day' })
  await slider.focus()
  await slider.press('Home')
  await expect(page.locator('.history-inspector output')).toHaveText('2024-01-04')
  await expect(page.locator('.history-values dd')).toHaveText(['100', '1,000', '1,000', '0%'])
  await slider.press('ArrowRight')
  await expect(page.locator('.chart-value span')).toHaveText(['2024-01-05', '2024-01-05'])
  await expect(page.locator('.history-values dd')).toHaveText(['90', '800', '980', '2%'])
  await expect(slider).toHaveAttribute('aria-valuetext', '2024-01-05, equity 980, drawdown 2 percent')
  await slider.press('ArrowRight')
  await expect(page.locator('.history-inspector output')).toHaveText('2024-01-08')
  await expect(page.locator('.chart-value strong')).toHaveText(['1,050', '0%'])
})

test('pointer inspection selects a shared day from either chart', async ({ page }) => {
  await showResults(page)
  const equity = page.getByRole('img', { name: 'Portfolio equity', exact: true })
  await equity.scrollIntoViewIfNeeded()
  let bounds = (await equity.boundingBox())!
  await page.mouse.move(bounds.x + 69, bounds.y + 50)
  await expect(page.getByRole('slider')).toHaveValue('0')
  await expect(page.locator('.chart-value span')).toHaveText(['2024-01-04', '2024-01-04'])

  const drawdown = page.getByRole('img', { name: 'Drawdown', exact: true })
  await drawdown.scrollIntoViewIfNeeded()
  bounds = (await drawdown.boundingBox())!
  await page.mouse.move(bounds.x + bounds.width - 21, bounds.y + 50)
  await expect(page.getByRole('slider')).toHaveValue('3')
  await expect(page.locator('.chart-value span')).toHaveText(['2024-01-09', '2024-01-09'])
})

test('flat no-trade histories and a single bar remain visible', async ({ page }) => {
  const flat = {
    ...result, end_cash: 1000, end_value: 1000, total_return: 0, CAGR: 0, max_drawdown: 0,
    history: result.history.map((point) => ({ ...point, cash: 1000, equity: 1000, drawdown: 0 })),
  }
  await showResults(page, flat)
  for (const chart of await page.getByRole('img').all()) await expectVisiblePlot(chart)
  await expect(page.locator('.chart-value strong')).toHaveText(['1,000', '0%'])

  await page.route('**/api/backtests/run-backtest', (route) => route.fulfill({ json: { ...flat, history: flat.history.slice(0, 1) } }))
  await page.getByRole('button', { name: 'Run backtest' }).click()
  await expect(page.getByRole('slider')).toBeDisabled()
  await expect(page.locator('.history-inspector output')).toHaveText('2024-01-04')
  for (const chart of await page.getByRole('img').all()) await expectVisiblePlot(chart)
})

test('empty history leaves summary metrics available', async ({ page }) => {
  await showResults(page, { ...result, history: [] })
  await expect(page.getByRole('status')).toHaveText('No daily history is available for this run.')
  await expect(page.getByRole('img', { name: 'Portfolio equity', exact: true })).toHaveCount(0)
  await expect(page.getByText('Final portfolio value', { exact: true })).toBeVisible()
})

test('negative equity and drawdown above 100 percent are not clipped', async ({ page }) => {
  const history = result.history.map((point, index) => index === 2
    ? { ...point, equity: -500, drawdown: 150 }
    : index === 3 ? { ...point, drawdown: 0 } : point)
  await showResults(page, { ...result, max_drawdown: 150, history })
  await page.getByRole('slider').focus()
  await page.getByRole('slider').press('ArrowLeft')
  await expect(page.locator('.chart-value strong')).toHaveText(['-500', '150%'])
  for (const chart of await page.getByRole('img').all()) await expectVisiblePlot(chart)
})

test('a failed rerun removes previous charts and a later success uses the new baseline', async ({ page }) => {
  await showResults(page)
  await page.route('**/api/backtests/run-backtest', (route) => route.fulfill({ status: 400, json: { detail: 'There are no records' } }))
  await page.getByRole('button', { name: 'Run backtest' }).click()
  await expect(page.getByRole('alert')).toHaveText('There are no records')
  await expect(page.getByRole('img', { name: 'Portfolio equity', exact: true })).toHaveCount(0)

  const next: BacktestResponse = {
    ...result, start_cash: 2000, end_cash: 1800, end_value: 1980,
    total_return: -1, CAGR: -2, max_drawdown: 1,
    history: [
      { ...result.history[0], cash: 2000, equity: 2000 },
      { ...result.history[1], cash: 1800, equity: 1980, drawdown: 1 },
    ],
  }
  await page.route('**/api/backtests/run-backtest', (route) => route.fulfill({ json: next }))
  await page.getByRole('button', { name: 'Run backtest' }).click()
  await expect(page.getByText('Initial cash: 2,000', { exact: true })).toBeVisible()
  await expect(page.getByRole('slider')).toHaveValue('1')
  await expect(page.locator('.chart-value strong')).toHaveText(['1,980', '1%'])
})

test.describe('on a narrow touchscreen', () => {
  test.use({ viewport: { width: 360, height: 800 }, hasTouch: true })

  test('charts fit the viewport and a tap selects a day', async ({ page }) => {
    await showResults(page)
    const chart = page.getByRole('img', { name: 'Portfolio equity', exact: true })
    await chart.scrollIntoViewIfNeeded()
    await expectVisiblePlot(chart)
    const bounds = (await chart.boundingBox())!
    await page.touchscreen.tap(bounds.x + 69, bounds.y + 50)
    await expect(page.getByRole('slider')).toHaveValue('0')
    await expect(page.locator('.history-inspector output')).toHaveText('2024-01-04')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await expect(page.getByRole('link', { name: 'Skip to content' })).not.toBeInViewport()
    await page.locator('.backtest-results').screenshot({ path: test.info().outputPath('mobile-results.png') })
  })
})
