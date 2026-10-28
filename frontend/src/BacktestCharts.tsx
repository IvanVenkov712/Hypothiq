import { useEffect, useId, useRef, useState } from 'react'
import type { PointerEvent } from 'react'
import type { BacktestHistoryPoint } from './api/backtests'

const valueFormat = new Intl.NumberFormat('en', { maximumFractionDigits: 2 })
const axisFormat = new Intl.NumberFormat('en', { notation: 'compact', maximumSignificantDigits: 4 })

interface ChartProps {
  history: BacktestHistoryPoint[]
  startCash: number
  metric: 'equity' | 'drawdown'
  selectedIndex: number
  onSelect: (index: number) => void
}

function HistoryChart({ history, startCash, metric, selectedIndex, onSelect }: ChartProps) {
  const titleId = useId()
  const descriptionId = useId()
  const svgRef = useRef<SVGSVGElement>(null)
  const [width, setWidth] = useState(800)
  const drawdown = metric === 'drawdown'
  const title = drawdown ? 'Drawdown' : 'Portfolio equity'
  const selected = history[selectedIndex]
  const height = drawdown ? 200 : 280
  const left = 68
  const right = width - 20
  const top = 16
  const bottom = height - 36

  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    observer.observe(svgRef.current!)
    return () => observer.disconnect()
  }, [])

  let minimum = drawdown ? 0 : startCash
  let maximum = drawdown ? 0 : startCash
  for (const point of history) {
    minimum = Math.min(minimum, point[metric])
    maximum = Math.max(maximum, point[metric])
  }
  if (drawdown) {
    maximum = maximum === 0 ? 1 : maximum * 1.1
  } else {
    const padding = (maximum - minimum || Math.max(Math.abs(startCash) * 0.05, 1)) * 0.1
    minimum -= padding
    maximum += padding
  }

  const x = (index: number) => history.length === 1
    ? (left + right) / 2
    : left + index / (history.length - 1) * (right - left)
  const y = (value: number) => drawdown
    ? top + value / maximum * (bottom - top)
    : top + (maximum - value) / (maximum - minimum) * (bottom - top)
  const line = history.map((point, index) => `${index === 0 ? 'M' : 'L'} ${x(index)} ${y(point[metric])}`).join(' ')
  const areaBaseline = drawdown ? top : bottom
  const area = `${line} L ${x(history.length - 1)} ${areaBaseline} L ${x(0)} ${areaBaseline} Z`
  const dateTicks = [...new Set(width >= 560
    ? [0, Math.floor((history.length - 1) / 2), history.length - 1]
    : [0, history.length - 1])]
  const suffix = drawdown ? '%' : ''

  function selectBar(event: PointerEvent<SVGSVGElement>) {
    const bounds = event.currentTarget.getBoundingClientRect()
    const pointerX = (event.clientX - bounds.left) / bounds.width * width
    const index = Math.round((pointerX - left) / (right - left) * (history.length - 1))
    onSelect(Math.max(0, Math.min(history.length - 1, index)))
  }

  return (
    <section className={`history-chart ${drawdown ? 'history-chart-drawdown' : ''}`} aria-label={title}>
      <div className="chart-heading">
        <div>
          <h3>{title}</h3>
          <p>{drawdown ? 'Decline from the running equity peak (%)' : 'Portfolio value in the instrument’s quote currency'}</p>
        </div>
        <div className="chart-value">
          <strong>{valueFormat.format(selected[metric])}{suffix}</strong>
          <span>{selected.time.slice(0, 10)}</span>
        </div>
      </div>
      <svg
        ref={svgRef} className="history-chart-svg" viewBox={`0 0 ${width} ${height}`}
        style={{ height }} role="img" aria-labelledby={titleId} aria-describedby={descriptionId}
        onPointerMove={selectBar}
        onPointerDown={(event) => {
          // Capture also lets touch users drag through bars without leaving the plot.
          event.currentTarget.setPointerCapture(event.pointerId)
          selectBar(event)
        }}
      >
        <title id={titleId}>{title}</title>
        <desc id={descriptionId}>
          {history.length} daily bars, from {history[0].time.slice(0, 10)} to {history[history.length - 1].time.slice(0, 10)}.
          {drawdown ? ' Drawdown is a positive percentage plotted downward from zero.' : ` Initial cash: ${valueFormat.format(startCash)}.`}
          {' Use the trading day slider below to inspect exact values.'}
        </desc>
        {[0, 1, 2, 3, 4].map((tick) => {
          const value = drawdown ? maximum * tick / 4 : maximum - (maximum - minimum) * tick / 4
          return (
            <g key={tick} className="chart-grid">
              <line x1={left} x2={right} y1={y(value)} y2={y(value)} />
              <text x={left - 10} y={y(value)} textAnchor="end" dominantBaseline="middle">{(drawdown ? valueFormat : axisFormat).format(value)}{suffix}</text>
            </g>
          )
        })}
        <path className="chart-area" d={area} />
        {!drawdown && <line className="chart-baseline" x1={left} x2={right} y1={y(startCash)} y2={y(startCash)} />}
        <path className="chart-line" d={line} />
        <line className="chart-cursor" x1={x(selectedIndex)} x2={x(selectedIndex)} y1={top} y2={bottom} />
        <circle className="chart-point" cx={x(selectedIndex)} cy={y(selected[metric])} r="4" />
        {dateTicks.map((index) => (
          <text
            key={index} className="chart-date" x={x(index)} y={height - 10}
            textAnchor={history.length === 1 ? 'middle' : index === 0 ? 'start' : index === history.length - 1 ? 'end' : 'middle'}
          >{history[index].time.slice(0, 10)}</text>
        ))}
      </svg>
      {!drawdown && (
        <p className="chart-legend"><span />Initial cash: {valueFormat.format(startCash)}</p>
      )}
    </section>
  )
}

export default function BacktestCharts({ history, startCash }: { history: BacktestHistoryPoint[]; startCash: number }) {
  const [selectedIndex, setSelectedIndex] = useState(Math.max(0, history.length - 1))
  const sliderId = useId()

  if (history.length === 0) {
    return <p className="charts-empty" role="status">No daily history is available for this run.</p>
  }

  const index = Math.min(selectedIndex, history.length - 1)
  const selected = history[index]
  const date = selected.time.slice(0, 10)

  return (
    <div className="backtest-charts">
      <HistoryChart history={history} startCash={startCash} metric="equity" selectedIndex={index} onSelect={setSelectedIndex} />
      <HistoryChart history={history} startCash={startCash} metric="drawdown" selectedIndex={index} onSelect={setSelectedIndex} />
      <div className="history-inspector">
        <div className="history-inspector-heading">
          <label htmlFor={sliderId}>Inspect a trading day</label>
          <output htmlFor={sliderId}>{date}</output>
        </div>
        <input
          id={sliderId} type="range" min="0" max={history.length - 1} step="1" value={index}
          disabled={history.length === 1} onChange={(event) => setSelectedIndex(Number(event.target.value))}
          aria-valuetext={`${date}, equity ${valueFormat.format(selected.equity)}, drawdown ${valueFormat.format(selected.drawdown)} percent`}
        />
        <dl className="history-values" aria-live="polite" aria-atomic="true">
          <div><dt>Close price</dt><dd>{valueFormat.format(selected.close)}</dd></div>
          <div><dt>Uninvested cash</dt><dd>{valueFormat.format(selected.cash)}</dd></div>
          <div><dt>Portfolio equity</dt><dd>{valueFormat.format(selected.equity)}</dd></div>
          <div><dt>Drawdown</dt><dd>{valueFormat.format(selected.drawdown)}%</dd></div>
        </dl>
      </div>
      <p className="field-note">End-of-day values, including indicator warm-up. Dates follow trading sessions; weekends and missing sessions have no points. Initial cash is shown as a reference line.</p>
    </div>
  )
}
