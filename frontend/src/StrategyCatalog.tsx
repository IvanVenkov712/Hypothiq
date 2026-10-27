import { useState } from 'react'
import { useStrategyCatalog } from './hooks/useStrategyCatalog'
import type { ParameterDefinition, StrategyDefinition } from './api/strategies'

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M7 17 17 7M7 7h10v10" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  )
}

function ParameterTable({ parameters }: { parameters: ParameterDefinition[] }) {
  if (parameters.length === 0) {
    return <p className="no-parameters">This strategy has no configurable parameters.</p>
  }

  return (
    <div className="parameter-table-scroll" tabIndex={0} aria-label="Strategy parameters">
      <table>
        <caption className="visually-hidden">Parameters and their default values</caption>
        <thead>
          <tr><th scope="col">Parameter</th><th scope="col">Default</th><th scope="col">Details</th></tr>
        </thead>
        <tbody>
          {parameters.map((parameter) => {
            const bounds = [
              parameter.minimum !== null ? `≥ ${parameter.minimum}` : null,
              parameter.maximum !== null ? `≤ ${parameter.maximum}` : null,
              parameter.exclusive_minimum !== null ? `> ${parameter.exclusive_minimum}` : null,
              parameter.exclusive_maximum !== null ? `< ${parameter.exclusive_maximum}` : null,
            ].filter((bound) => bound !== null)

            return (
              <tr key={parameter.name}>
                <th scope="row">
                  <span className="parameter-label">{parameter.label}</span>
                  <span className="parameter-type">{parameter.type}</span>
                </th>
                <td><code>{parameter.default === null ? 'null' : String(parameter.default)}</code></td>
                <td className="parameter-details">
                  {bounds.length > 0 && <p className="parameter-bounds">{bounds.join(' and ')}</p>}
                  {parameter.nullable && <p>Accepts null</p>}
                  {parameter.description && <p>{parameter.description}</p>}
                  {parameter.choices && parameter.choices.length > 0 && (
                    <p>Suggested values: <span className="parameter-choices">{parameter.choices.join(', ')}</span></p>
                  )}
                  {bounds.length === 0 && !parameter.nullable && !parameter.description && !parameter.choices?.length && (
                    <span aria-label="No additional details">—</span>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function StrategyCard({ strategy }: { strategy: StrategyDefinition }) {
  const count = strategy.parameters.length

  return (
    <details className="strategy-card">
      <summary>
        <div className="card-heading">
          <span className="card-arrow"><ArrowIcon /></span>
        </div>
        <h2>{strategy.name}</h2>
        <p className="strategy-description">{strategy.description}</p>
        <div className="card-footer">
          <span className="parameter-count">{count} {count === 1 ? 'parameter' : 'parameters'}</span>
          <span className="details-label">
            <span className="when-closed">View details</span>
            <span className="when-open">Hide details</span>
            <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="m4 6 4 4 4-4" stroke="currentColor" strokeWidth="1.5" />
            </svg>
          </span>
        </div>
      </summary>
      <div className="strategy-details">
        <ParameterTable parameters={strategy.parameters} />
        <a className="secondary-button catalog-backtest-link" href={`/backtesting?strategy=${encodeURIComponent(strategy.class_name)}`}>Backtest this strategy <span aria-hidden="true">↗</span></a>
      </div>
    </details>
  )
}

export default function StrategyCatalog() {
  const { catalog, retry } = useStrategyCatalog()
  const [query, setQuery] = useState('')

  const strategies = catalog.status === 'success' ? catalog.strategies : []
  const search = query.trim().toLowerCase()
  const filtered = strategies.filter((strategy) => [
    strategy.name,
    strategy.class_name,
    strategy.description,
    ...strategy.parameters.flatMap((parameter) => [parameter.name, parameter.label]),
  ].some((value) => value.toLowerCase().includes(search)))
    .sort((a, b) => a.name.localeCompare(b.name))

  return (
    <>
      <section className="catalog-intro" aria-labelledby="catalog-title">
        <div className="intro-copy">
          <p className="eyebrow"><span /> The research library</p>
          <h1 id="catalog-title">Strategy catalog<span>.</span></h1>
          <p className="intro-description">
            Explore the strategies. Understand the parameters.<br className="desktop-break" />
            Find a starting point for your next hypothesis.
          </p>
        </div>
        <div className="intro-note">
          <span className="note-symbol" aria-hidden="true">↗</span>
          <p>Every strategy starts<br />with a hypothesis.</p>
        </div>
      </section>

      <section className="catalog-section" aria-label="Available strategies" aria-busy={catalog.status === 'loading'}>
        <div className="catalog-toolbar">
          <div className="catalog-heading">
            <h2>All strategies</h2>
            {catalog.status === 'success' && <span className="total-count">{strategies.length}</span>}
          </div>
          <div className="search-field">
            <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <circle cx="8.5" cy="8.5" r="5.5" stroke="currentColor" strokeWidth="1.5" />
              <path d="m13 13 4 4" stroke="currentColor" strokeWidth="1.5" />
            </svg>
            <label className="visually-hidden" htmlFor="strategy-search">Search strategies</label>
            <input
              id="strategy-search"
              type="search"
              placeholder="Search strategies or parameters…"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              disabled={catalog.status !== 'success' || strategies.length === 0}
            />
          </div>
        </div>

        {catalog.status === 'loading' && (
          <div className="catalog-loading" role="status">
            <span className="loading-spinner" aria-hidden="true" />Loading strategies…
          </div>
        )}

        {catalog.status === 'error' && (
          <div className="catalog-message" role="alert">
            <span className="message-symbol" aria-hidden="true">!</span>
            <h3>The catalog is unavailable</h3>
            <p>We couldn’t load the strategies. Please try again in a moment.</p>
            <button className="secondary-button" onClick={retry}>Try again <span aria-hidden="true">↗</span></button>
          </div>
        )}

        {catalog.status === 'success' && (
          <>
            <p className="results-caption" role="status">
              {search ? `${filtered.length} of ${strategies.length} strategies` : 'Explore a strategy to see its parameters and default values.'}
            </p>
            {filtered.length > 0 ? (
              <div className="strategy-grid">
                {filtered.map((strategy) => (
                  <StrategyCard key={strategy.class_name} strategy={strategy} />
                ))}
              </div>
            ) : (
              <div className="catalog-message">
                <span className="message-symbol" aria-hidden="true">∅</span>
                <h3>{strategies.length === 0 ? 'No strategies available yet' : 'No matching strategies'}</h3>
                <p>{strategies.length === 0 ? 'Registered strategies will appear here when available.' : 'Try another name, description, or parameter.'}</p>
                {strategies.length > 0 && <button className="secondary-button" onClick={() => setQuery('')}>Clear search <span aria-hidden="true">↗</span></button>}
              </div>
            )}
          </>
        )}
      </section>
    </>
  )
}
