export interface BacktestRequest {
  strategy: { name: string; params: Record<string, string | number | boolean | null> }
  data_request: { ticker: string; start: string; end: string; interval: '1d' }
  broker: {
    cash: number
    commission: { commission: number }
    slippage_perc?: { perc: number }
    slippage_fixed?: { fixed: number }
  }
  sizer: { name: 'FixedSize' | 'PercentSizer'; params: { stake: number } | { percents: number } }
}

export interface BacktestResponse {
  start_cash: number
  end_cash: number
  end_value: number
  total_return: number
  CAGR: number
  sharpe: number | null
  closed_trades: number
  max_drawdown: number
}

export async function runBacktest(request: BacktestRequest, signal: AbortSignal): Promise<BacktestResponse> {
  const response = await fetch('/api/backtests/run-backtest', {
    method: 'POST',
    signal,
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body?.detail
    if (typeof detail === 'string') throw new Error(detail)
    if (Array.isArray(detail)) {
      throw new Error(detail.map((item) => `${item.loc?.slice(1).join('.') || 'Request'}: ${item.msg}`).join('; '))
    }
    throw new Error(`The backtest could not be completed (${response.status}). Please try again.`)
  }

  return response.json()
}
