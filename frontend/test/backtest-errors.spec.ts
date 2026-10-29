import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.route('**/api/strategies', (route) => route.fulfill({ json: [{
    class_name: 'BuyAndHold', name: 'Buy and hold', description: 'Buy once and hold.', parameters: [],
  }] }))
})

for (const failure of [
  { status: 400, detail: 'MACrossOver requires at least 51 daily bars to finish warm-up; received 20. Choose an earlier start date or reduce the strategy lookback periods.' },
  { status: 502, detail: 'Could not download daily prices for AAPL. The market-data provider may be unavailable; please retry shortly.' },
]) {
  test(`shows an actionable ${failure.status} error and allows a successful retry`, async ({ page }) => {
    await page.route('**/api/backtests/run-backtest', (route) => route.fulfill({
      status: failure.status, json: { detail: failure.detail },
    }))
    await page.goto('/backtesting')
    await page.getByRole('button', { name: 'Run backtest' }).click()
    await expect(page.getByRole('alert')).toHaveText(failure.detail)
    await expect(page.getByRole('button', { name: 'Run backtest' })).toBeEnabled()

    await page.route('**/api/backtests/run-backtest', (route) => route.fulfill({ json: {
      start_cash: 10000, end_cash: 10000, end_value: 10000, total_return: 0,
      CAGR: 0, sharpe: null, closed_trades: 0, max_drawdown: 0, history: [],
    } }))
    await page.getByLabel('Start date', { exact: true }).fill('2019-01-01')
    await page.getByRole('button', { name: 'Run backtest' }).click()
    await expect(page.getByText('Backtest complete')).toBeVisible()
    await expect(page.getByRole('alert')).toHaveCount(0)
  })
}

test('shows field locations from a backend validation response', async ({ page }) => {
  await page.route('**/api/backtests/run-backtest', (route) => route.fulfill({
    status: 422, json: { detail: [{
      type: 'greater_than', loc: ['body', 'broker', 'cash'], msg: 'Input should be greater than 0',
    }] },
  }))
  await page.goto('/backtesting')
  await page.getByRole('button', { name: 'Run backtest' }).click()
  await expect(page.getByRole('alert')).toHaveText('broker.cash: Input should be greater than 0')
})

test('rejects unordered dates before making a backtest request', async ({ page }) => {
  let submissions = 0
  await page.route('**/api/backtests/run-backtest', (route) => {
    submissions += 1
    return route.fulfill({ status: 500 })
  })
  await page.goto('/backtesting')
  await page.getByLabel('Start date', { exact: true }).fill('2025-01-01')
  await page.getByLabel('End date (exclusive)', { exact: true }).fill('2024-01-01')
  await page.getByRole('button', { name: 'Run backtest' }).click()
  await expect(page.getByRole('alert')).toHaveText('The end date must be after the start date.')
  expect(submissions).toBe(0)
})
