import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { runBacktest } from './api/backtests'
import type { BacktestRequest, BacktestResponse } from './api/backtests'
import type { ParameterDefinition, StrategyDefinition } from './api/strategies'
import { useStrategyCatalog } from './hooks/useStrategyCatalog'

type RunState =
  | { status: 'idle' }
  | { status: 'running' }
  | { status: 'error'; message: string }
  | { status: 'success'; result: BacktestResponse; description: string }

function ParameterInput({ parameter }: { parameter: ParameterDefinition }) {
  const id = `parameter-${parameter.name}`
  const numeric = parameter.type === 'integer' || parameter.type === 'number'
  return (
    <div className="form-field">
      <label htmlFor={id}>{parameter.label}</label>
      {parameter.type === 'boolean' ? (
        <select id={id} name={id} defaultValue={String(parameter.default ?? '')}>
          {parameter.nullable && <option value="">None</option>}
          <option value="true">True</option><option value="false">False</option>
        </select>
      ) : (
        <>
          <input
            id={id} name={id} type={numeric ? 'number' : 'text'}
            defaultValue={parameter.default === null ? '' : String(parameter.default)}
            required={!parameter.nullable}
            step={parameter.type === 'integer' ? 1 : 'any'}
            min={parameter.minimum ?? undefined} max={parameter.maximum ?? undefined}
            list={parameter.choices?.length ? `${id}-choices` : undefined}
            aria-describedby={parameter.description || parameter.nullable ? `${id}-hint` : undefined}
          />
          {parameter.choices?.length ? (
            <datalist id={`${id}-choices`}>
              {parameter.choices.map((choice) => <option key={choice} value={choice} />)}
            </datalist>
          ) : null}
        </>
      )}
      {(parameter.description || parameter.nullable) && (
        <small id={`${id}-hint`}>{parameter.description} {parameter.nullable && 'Leave empty to use none.'}</small>
      )}
    </div>
  )
}

function readParameters(strategy: StrategyDefinition, data: FormData): BacktestRequest['strategy']['params'] {
  return Object.fromEntries(strategy.parameters.map((parameter) => {
    const raw = String(data.get(`parameter-${parameter.name}`) ?? '').trim()
    if (!raw && parameter.nullable) return [parameter.name, null]
    if (parameter.type === 'boolean') return [parameter.name, raw === 'true']
    if (parameter.type === 'string') return [parameter.name, raw]
    const value = Number(raw)
    if (!raw || !Number.isFinite(value) || (parameter.type === 'integer' && !Number.isInteger(value))) {
      throw new Error(`${parameter.label} must be a valid ${parameter.type}.`)
    }
    if (parameter.exclusive_minimum !== null && value <= parameter.exclusive_minimum) {
      throw new Error(`${parameter.label} must be greater than ${parameter.exclusive_minimum}.`)
    }
    if (parameter.exclusive_maximum !== null && value >= parameter.exclusive_maximum) {
      throw new Error(`${parameter.label} must be less than ${parameter.exclusive_maximum}.`)
    }
    return [parameter.name, value]
  }))
}

const numberFormat = new Intl.NumberFormat('en', { maximumFractionDigits: 2 })
function format(value: number | null, suffix = '') {
  return value === null || !Number.isFinite(value) ? 'N/A' : `${numberFormat.format(value)}${suffix}`
}

export default function Backtesting() {
  const { catalog, retry } = useStrategyCatalog()
  const [strategyId, setStrategyId] = useState(() => new URLSearchParams(window.location.search).get('strategy') ?? '')
  const [sizer, setSizer] = useState('FixedSize')
  const [slippage, setSlippage] = useState('percent')
  const [run, setRun] = useState<RunState>({ status: 'idle' })
  const controllerRef = useRef<AbortController | null>(null)
  const resultsRef = useRef<HTMLElement | null>(null)
  const strategies = catalog.status === 'success' ? [...catalog.strategies].sort((a, b) => a.name.localeCompare(b.name)) : []
  const strategy = strategies.find((item) => item.class_name === strategyId) ?? strategies[0]

  useEffect(() => () => controllerRef.current?.abort(), [])
  useEffect(() => {
    if (run.status === 'success') resultsRef.current?.focus()
  }, [run.status])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!strategy || run.status === 'running') return
    const data = new FormData(event.currentTarget)
    try {
      const ticker = String(data.get('ticker') ?? '').trim().toUpperCase()
      if (!ticker) throw new Error('Enter a ticker symbol.')
      const start = String(data.get('start'))
      const end = String(data.get('end'))
      if (start >= end) throw new Error('The end date must be after the start date.')
      const cost = Number(data.get('slippage'))
      const size = Number(data.get('size'))
      const request: BacktestRequest = {
        strategy: { name: strategy.class_name, params: readParameters(strategy, data) },
        data_request: { ticker, start: `${start}T00:00:00`, end: `${end}T00:00:00`, interval: '1d' },
        broker: {
          cash: Number(data.get('cash')),
          commission: { commission: Number(data.get('commission')) / 100 },
          ...(slippage === 'percent' ? { slippage_perc: { perc: cost / 100 } } : { slippage_fixed: { fixed: cost } }),
        },
        sizer: sizer === 'FixedSize'
          ? { name: 'FixedSize', params: { stake: size } }
          : { name: 'PercentSizer', params: { percents: size } },
      }
      controllerRef.current?.abort()
      const controller = new AbortController()
      controllerRef.current = controller
      setRun({ status: 'running' })
      const result = await runBacktest(request, controller.signal)
      if (!controller.signal.aborted) {
        setRun({ status: 'success', result, description: `${strategy.name} / ${ticker} / ${start} to ${end} (exclusive) / Daily bars` })
      }
    } catch (error) {
      if (!controllerRef.current?.signal.aborted) {
        setRun({ status: 'error', message: error instanceof Error ? error.message : 'Unable to reach the backtesting service. Please try again.' })
      }
    }
  }

  return (
    <>
      <section className="catalog-intro" aria-labelledby="backtesting-title">
        <div className="intro-copy">
          <p className="eyebrow"><span /> Put your hypothesis to the test</p>
          <h1 id="backtesting-title">Backtesting<span>.</span></h1>
          <p className="intro-description">Configure a strategy. Test it against historical prices.<br className="desktop-break" /> Understand its returns and risk.</p>
        </div>
        <a className="text-link" href="/strategies">Explore the strategy catalog <span aria-hidden="true">↗</span></a>
      </section>

      {catalog.status === 'loading' && <div className="catalog-loading" role="status"><span className="loading-spinner" aria-hidden="true" />Loading strategies…</div>}
      {catalog.status === 'error' && (
        <div className="catalog-message" role="alert">
          <h2>Strategies are unavailable</h2>
          <p>We couldn’t load the strategies needed to configure a backtest.</p>
          <button className="secondary-button" onClick={retry}>Try again</button>
        </div>
      )}
      {catalog.status === 'success' && !strategy && <div className="catalog-message"><h2>No strategies available yet</h2><p>Registered strategies will appear here when available.</p></div>}
      {strategy && (
        <div className="backtest-layout">
          <form className="backtest-form" onSubmit={submit} aria-label="Backtest configuration" aria-busy={run.status === 'running'}>
            <fieldset disabled={run.status === 'running'} className="form-controls">
              <legend className="visually-hidden">Backtest configuration</legend>
              <section className="form-section" aria-labelledby="strategy-heading">
                <h2 id="strategy-heading">Strategy</h2>
                <div className="form-field">
                  <label htmlFor="strategy">Trading strategy</label>
                  <select id="strategy" value={strategy.class_name} onChange={(event) => setStrategyId(event.target.value)} aria-describedby="strategy-description">
                    {strategies.map((item) => <option key={item.class_name} value={item.class_name}>{item.name}</option>)}
                  </select>
                  <small id="strategy-description">{strategy.description}</small>
                </div>
                <div className="form-grid parameter-inputs" key={strategy.class_name}>
                  {strategy.parameters.map((parameter) => <ParameterInput key={parameter.name} parameter={parameter} />)}
                </div>
                {strategy.parameters.length === 0 && <p className="field-note">This strategy has no configurable parameters.</p>}
              </section>

              <section className="form-section" aria-labelledby="data-heading">
                <h2 id="data-heading">Market data</h2>
                <div className="form-grid">
                  <div className="form-field"><label htmlFor="ticker">Ticker symbol</label><input id="ticker" name="ticker" defaultValue="AAPL" placeholder="e.g. AAPL" required maxLength={30} autoCapitalize="characters" /></div>
                  <div className="form-field"><label htmlFor="interval">Bar interval</label><select id="interval" defaultValue="1d"><option value="1d">Daily</option></select></div>
                  <div className="form-field"><label htmlFor="start">Start date</label><input id="start" name="start" type="date" defaultValue="2020-01-01" required /></div>
                  <div className="form-field"><label htmlFor="end">End date (exclusive)</label><input id="end" name="end" type="date" defaultValue="2025-01-01" required /></div>
                </div>
                <p className="field-note">Historical prices are downloaded from Yahoo Finance. Choose a range with enough bars for your strategy’s indicators.</p>
              </section>

              <section className="form-section" aria-labelledby="execution-heading">
                <h2 id="execution-heading">Capital & execution</h2>
                <div className="form-grid">
                  <div className="form-field"><label htmlFor="cash">Initial cash</label><input id="cash" name="cash" type="number" min="0.01" step="0.01" defaultValue="10000" required /></div>
                  <div className="form-field"><label htmlFor="commission">Commission (%)</label><input id="commission" name="commission" type="number" min="0" max="100" step="any" defaultValue="0.1" required /><small>0.1 means 0.1% of each transaction.</small></div>
                  <div className="form-field"><label htmlFor="sizer">Position sizing</label><select id="sizer" value={sizer} onChange={(event) => setSizer(event.target.value)}><option value="FixedSize">Fixed number of units</option><option value="PercentSizer">Percentage of available cash</option></select></div>
                  <div className="form-field" key={sizer}><label htmlFor="size">{sizer === 'FixedSize' ? 'Units per order' : 'Available cash per order (%)'}</label><input id="size" name="size" type="number" min={sizer === 'FixedSize' ? 1 : 0.01} max={sizer === 'FixedSize' ? undefined : 100} step={sizer === 'FixedSize' ? 1 : 'any'} defaultValue={sizer === 'FixedSize' ? 1 : 95} required /></div>
                  <div className="form-field"><label htmlFor="slippage-mode">Slippage model</label><select id="slippage-mode" value={slippage} onChange={(event) => setSlippage(event.target.value)}><option value="percent">Percentage</option><option value="fixed">Fixed price amount</option></select></div>
                  <div className="form-field"><label htmlFor="slippage">{slippage === 'percent' ? 'Slippage (%)' : 'Slippage (price units)'}</label><input id="slippage" name="slippage" type="number" min="0" max={slippage === 'percent' ? 100 : undefined} step="any" defaultValue="0" required /></div>
                </div>
                <p className="field-note">Cash and fixed amounts use the instrument’s quote currency.</p>
              </section>
              <button type="submit" className="primary-button run-button">{run.status === 'running' ? 'Running backtest…' : 'Run backtest'} <span aria-hidden="true">↗</span></button>
            </fieldset>
            {run.status === 'error' && <p className="form-error" role="alert">{run.message}</p>}
            {run.status === 'running' && <p className="field-note" role="status">Downloading prices and running your strategy. This may take a moment.</p>}
          </form>

          <aside className="backtest-guide">
            <p className="eyebrow">A little context</p>
            <h2>From an idea<br />to evidence.</h2>
            <p>Start with the default parameters, then change one setting at a time to understand its effect.</p>
            <p>Your results include returns, maximum drawdown, Sharpe ratio, and completed trades.</p>
            <p className="guide-note">Historical performance does not predict future results. Backtests are research simulations.</p>
          </aside>
        </div>
      )}

      {run.status === 'success' && (
        <section className="backtest-results" aria-labelledby="results-title" ref={resultsRef} tabIndex={-1}>
          <p className="eyebrow"><span /> Backtest complete</p>
          <h2 id="results-title">Results</h2>
          <p className="results-description">{run.description}</p>
          <dl className="metrics-grid">
            {[
              ['Total return', format(run.result.total_return, '%')],
              ['Annualized return', format(run.result.CAGR, '%')],
              ['Maximum drawdown', format(run.result.max_drawdown, '%')],
              ['Sharpe ratio', format(run.result.sharpe)],
              ['Initial cash', format(run.result.start_cash)],
              ['Final portfolio value', format(run.result.end_value)],
              ['Remaining cash', format(run.result.end_cash)],
              ['Closed trades', format(run.result.closed_trades)],
            ].map(([label, value]) => <div className="metric" key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
          </dl>
          <p className="field-note">Final portfolio value includes open positions; closed trades count completed round trips. N/A means the metric could not be calculated.</p>
        </section>
      )}
    </>
  )
}
