import { useEffect } from 'react'
import Home from './Home'
import StrategyCatalog from './StrategyCatalog'
import Backtesting from './Backtesting'
import './App.css'

const pages = [
  { path: '/', label: 'Home' },
  { path: '/strategies', label: 'Strategy catalog' },
  { path: '/backtesting', label: 'Backtesting' },
]

function App() {
  const path = window.location.pathname.replace(/\/+$/, '') || '/'
  const page = pages.find((candidate) => candidate.path === path)

  useEffect(() => {
    document.title = `${page?.label ?? 'Page not found'} · Hypothiq`
  }, [page])

  return (
    <>
      <a className="skip-link" href="#main-content">Skip to content</a>
      <header className="site-header">
        <a className="brand" href="/" aria-label="Hypothiq home">
          <span className="brand-mark" aria-hidden="true">h<span>.</span></span>
          Hypothiq
        </a>
        <nav className="site-nav" aria-label="Main navigation">
          {pages.map((item) => (
            <a key={item.path} href={item.path} aria-current={path === item.path ? 'page' : undefined}>{item.label}</a>
          ))}
        </nav>
      </header>

      <main id="main-content" tabIndex={-1}>
        {path === '/' && <Home />}
        {path === '/strategies' && <StrategyCatalog />}
        {path === '/backtesting' && <Backtesting />}
        {!page && (
          <section className="catalog-intro">
            <div>
              <p className="eyebrow">404 / Page not found</p>
              <h1>This page is missing<span>.</span></h1>
              <a className="primary-button" href="/">Return home <span aria-hidden="true">↗</span></a>
            </div>
          </section>
        )}
      </main>

      <footer className="site-footer">
        <span>Hypothiq <span className="footer-divider">/</span> A place to test your ideas.</span>
        <span className="footer-note">Explore. Test. Understand.</span>
      </footer>
    </>
  )
}

export default App
