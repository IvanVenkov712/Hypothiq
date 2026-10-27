export default function Home() {
  return (
    <>
      <section className="catalog-intro home-intro" aria-labelledby="home-title">
        <div className="intro-copy">
          <p className="eyebrow"><span /> Your strategy research workspace</p>
          <h1 id="home-title">Start with an idea.<br />Put it to the test<span>.</span></h1>
          <p className="intro-description">
            Hypothiq helps you research algorithmic trading strategies and test
            them against historical market data. Explore predefined strategies,
            adjust their parameters, and see how they would have performed.
          </p>
          <a className="primary-button" href="/backtesting">Create a backtest <span aria-hidden="true">↗</span></a>
        </div>
        <div className="intro-note">
          <span className="note-symbol" aria-hidden="true">↗</span>
          <p>Every strategy starts<br />with a hypothesis.</p>
        </div>
      </section>
      <section className="home-links" aria-label="Explore Hypothiq">
        <a className="destination-card" href="/strategies">
          <span className="eyebrow">Explore</span>
          <h2>Strategy catalog <span aria-hidden="true">↗</span></h2>
          <p>Find a starting point. Browse trading strategies and understand their rules, parameters, and default values.</p>
          <span className="destination-label">Browse strategies <span aria-hidden="true">→</span></span>
        </a>
        <a className="destination-card" href="/backtesting">
          <span className="eyebrow">Experiment</span>
          <h2>Backtesting <span aria-hidden="true">↗</span></h2>
          <p>Choose a strategy, ticker, and date range. Set your trading costs and inspect returns, risk, and closed trades.</p>
          <span className="destination-label">Run a backtest <span aria-hidden="true">→</span></span>
        </a>
      </section>
    </>
  )
}
