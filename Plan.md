# Hypothiq — Project Development Plan

## 1. Project Overview

**Hypothiq** is a web-based platform for developing, backtesting, comparing, and sharing algorithmic trading strategies.

The platform uses **Backtrader** as its backtesting engine and provides an accessible web interface for configuring strategies, executing backtests, and analyzing their performance.

Development will follow an incremental approach, starting with a minimal viable product (MVP) and gradually introducing more advanced capabilities.

## 2. Technology Stack

| Component | Technology |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend | Python, FastAPI |
| Backtesting Engine | Backtrader |
| Historical Market Data | Yahoo Finance (yfinance) |
| Database | PostgreSQL (planned for later stages) |
| AI Integration | To be determined |

The frontend and backend will communicate through a REST API using JSON.

## 3. Development Roadmap

### Phase 1 — Minimum Viable Product (MVP)

**Objective:** Build a functional web application that allows users to configure and execute single-asset backtests using predefined trading strategies.

#### Functional Requirements

**1. Strategy Selection**
- Display a list of available predefined trading strategies.
- Allow users to select a strategy by name.
- Retrieve the selected strategy's configurable parameters from the backend.

**2. Backtest Configuration**
- Configure strategy-specific parameters.
- Select a financial instrument using its ticker symbol.
- Specify the historical data period.
- Configure initial capital and relevant execution settings, such as commission and slippage.
- Validate configuration values before execution.

**3. Historical Market Data**
- Retrieve historical OHLCV data from Yahoo Finance using `yfinance`.
- Validate the availability and integrity of the retrieved data.
- Handle missing data, invalid ticker symbols, and external data source errors.

**4. Backtest Execution**
- Execute the selected strategy using Backtrader.
- Apply the specified strategy and backtest configuration.
- Collect performance metrics and execution results.
- Handle execution failures and return meaningful error messages.

**5. Results Visualization**
- Display total return, annualized return, Sharpe ratio, and maximum drawdown.
- Visualize the portfolio equity curve.
- Display executed trades.
- Optionally include a Buy & Hold benchmark for performance evaluation.

#### MVP Completion Criteria

The MVP is considered complete when a user can select a predefined strategy, configure its parameters, execute a backtest using Yahoo Finance data, and inspect the resulting performance metrics and visualizations through the web interface.

User authentication, persistent backtest storage, custom strategy uploads, and AI functionality are excluded from the MVP.

---

### Phase 2 — Strategy Comparison

**Objective:** Allow users to compare the performance of multiple trading strategies under consistent testing conditions.

#### Functional Requirements
- Select multiple predefined strategies for comparison.
- Configure parameters independently for each strategy.
- Execute backtests using the same historical dataset and testing conditions.
- Compare performance metrics in a unified interface.
- Display multiple equity curves on a shared chart.
- Include a common benchmark where appropriate.

#### Completion Criteria

Users can evaluate multiple strategies side by side and identify differences in performance, risk, and trading behavior.

---

### Phase 3 — Multi-Asset Strategies

**Objective:** Extend the platform to support backtesting strategies that operate on multiple financial instruments.

#### Functional Requirements
- Select multiple financial instruments for a single backtest.
- Retrieve and align historical data across instruments.
- Execute multi-asset strategies using Backtrader.
- Track portfolio-level cash, positions, and equity.
- Support configurable position sizing and allocation rules.
- Calculate portfolio-level performance and risk metrics.

#### Completion Criteria

Users can configure, execute, and evaluate trading strategies operating on multiple financial instruments within a shared portfolio.

---

### Phase 4 — User Accounts and Strategy Sharing

**Objective:** Transform Hypothiq into a community-oriented platform where users can develop, execute, compare, and publish their own trading strategies.

#### Functional Requirements

**1. User Management**
- User registration and authentication.
- User profiles.
- Ownership and management of published strategies.

**2. Custom Strategies**
- Allow users to submit trading strategies written in Python.
- Validate strategy submissions.
- Execute user-provided strategies in isolated environments.
- Apply resource limits and appropriate security restrictions.

**3. Strategy Publishing**
- Publish strategies with descriptions and configurable parameters.
- Browse strategies published by other users.
- Run backtests using published strategies.
- Compare custom and predefined strategies.

**4. Persistence**
- Store user accounts and strategy metadata.
- Persist published strategy definitions and associated information.
- Optionally maintain backtest history and saved configurations.

#### Completion Criteria

Authenticated users can create, test, publish, discover, and compare custom Python trading strategies without compromising the security of the platform.

---

### Phase 5 — AI-Assisted Strategy Generation

**Objective:** Allow users to generate trading strategy implementations from natural-language descriptions.

#### Functional Requirements
- Accept a textual description of a trading strategy.
- Generate Python strategy code compatible with Backtrader.
- Present the generated code for user review and modification.
- Validate the generated implementation.
- Execute generated strategies within the same isolated environment used for custom strategies.
- Allow users to test, compare, save, and publish generated strategies.

#### Completion Criteria

Users can describe a trading strategy in natural language, obtain a corresponding Python implementation, review its code, execute a backtest, and optionally publish the strategy.

---

## 4. Architectural Principles

The following principles will guide development across all phases.

**Separation of Concerns**

The frontend, API layer, application logic, market data retrieval, and backtesting execution should have clearly defined responsibilities.

**Incremental Development**

Each development phase should build upon the previous one without requiring unnecessary infrastructure or speculative abstractions.

**Extensibility**

The architecture should support additional strategies, market data providers, and backtest configurations without extensive modifications to existing components.

**Reproducibility**

Backtest results should retain sufficient configuration and data-related metadata to make experiments reproducible whenever possible.

**Correctness**

The platform should avoid look-ahead bias and ensure consistent handling of orders, commissions, slippage, historical data, and performance metrics.

**Security**

Execution of arbitrary user-provided Python code must be isolated from the main application and protected by appropriate resource and access restrictions.

**Testability**

Core backend components should be independently testable, with automated tests covering expected behavior, invalid inputs, and relevant edge cases.

## 5. Scope Management

To maintain a manageable development process, features will be implemented only when required by the current development phase.

In particular:

- The MVP will focus exclusively on predefined, single-asset strategies.
- Strategy comparison will precede multi-asset functionality.
- User accounts and persistent storage will be introduced when required by strategy publishing and user-specific features.
- Arbitrary Python code execution will require a dedicated security architecture.
- AI-assisted generation will build upon the existing custom strategy execution infrastructure.

## 6. Long-Term Vision

Hypothiq aims to evolve from a simple backtesting application into an extensible research platform for algorithmic trading strategies.

Its long-term value will lie in providing a unified environment where users can experiment with trading ideas, evaluate their performance, compare alternative approaches, and share implementations with others.

**The primary focus is software engineering and strategy research, rather than live trading or automated execution of real financial transactions.**