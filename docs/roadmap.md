# Roadmap and implementation status

This document separates implemented behavior from planned work. Phases express
development order, with no release dates committed. The current milestone is
the single-asset MVP.

The intended product scope is a platform for researching, sharing, creating, and
testing algorithmic trading strategies. The phases below build toward that
scope; creation and sharing are not yet implemented.

## Implemented

- FastAPI application with health, strategy catalogue, and backtest endpoints.
- Seven predefined strategies registered for execution.
- Strategy and sizer parameter resolution, including inherited defaults and
  named Backtrader indicator parameters.
- Typed catalogue metadata derived from strategy declarations.
- Single-ticker historical downloads through `yfinance` and pandas data feeds.
- Backtrader execution with initial cash, commission, and slippage settings.
- Summary returns, Sharpe ratio, closed trades, and maximum drawdown.
- React catalogue with search, expandable parameter details, loading and empty
  states, and retry after a failed request.
- Home page and shared navigation to the catalogue and backtesting workspace.
- Strategy-driven daily backtest form with ticker, dates, capital, sizing,
  commission, slippage, and aggregate results.
- Backend tests for registry/catalogue contracts, broker execution settings,
  data loading, result mapping, file readers, and RSI edge cases.

## Phase 1: complete the single-asset MVP

The API execution path and browser catalogue are implemented. Remaining work:

- Strengthen date, interval, parameter, data-quality, and warm-up validation;
  return actionable errors for provider and engine failures.
- Validate annualization and timeframe handling for supported intervals.
- Expose equity history and executed trades through the API.
- Display an equity curve and a trade list alongside browser summary metrics.
- Add a Buy & Hold benchmark where useful.
- Add frontend and end-to-end coverage for the complete workflow, and expand
  deterministic strategy behavior tests.

Completion means a user can choose a strategy, configure and run a single-asset
backtest, and inspect metrics and visualizations in the browser. Accounts,
persistence, arbitrary Python uploads, and AI generation remain outside this MVP.

## Phase 2: strategy comparison

Run multiple predefined strategies over the same dataset and execution settings,
with independent strategy parameters. Present metrics side by side and plot
equity curves against a common benchmark.

Completion means users can compare returns, risk, and trading behavior under
consistent testing conditions.

## Phase 3: multi-asset strategies

Support multiple instruments, align their historical data, and execute strategies
with shared cash and portfolio-level positions. Extend sizing/allocation and
risk metrics to the portfolio.

Completion means a single backtest can evaluate a strategy trading multiple
instruments within one portfolio.

## Phase 4: accounts and strategy sharing

Add registration, authentication, profiles, strategy ownership, and persistent
research data. PostgreSQL is the planned database; no database integration exists
yet. Let users submit, publish, discover, and compare custom Python strategies.

Custom code requires an isolated execution environment with resource and access
limits before uploads can be supported. Completion means authenticated users can
manage and share strategies and execute them within that boundary.

## Phase 5: AI-assisted strategy generation

Generate Backtrader-compatible Python from natural-language descriptions, present
the code for review and editing, validate it, and execute it using the same
isolation boundary as custom strategies. The AI provider and integration are
undecided.

Completion means users can describe an idea, review its implementation, backtest
it, and optionally save or publish it.

## Development principles

Keep the UI, HTTP boundary, orchestration, market-data access, and strategy
logic separate. Add infrastructure when a phase requires it. Improve
reproducibility by retaining request and data provenance when saved research is
introduced. Test execution assumptions with deterministic data, including order
timing and costs. Live trading is outside the current roadmap.
