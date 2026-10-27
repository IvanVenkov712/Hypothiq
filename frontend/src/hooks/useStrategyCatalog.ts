import { useEffect, useState } from 'react'
import { fetchStrategyCatalog } from '../api/strategies'
import type { StrategyDefinition } from '../api/strategies'

type CatalogState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'success'; strategies: StrategyDefinition[] }

export function useStrategyCatalog() {
  const [catalog, setCatalog] = useState<CatalogState>({ status: 'loading' })
  const [version, setVersion] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    fetchStrategyCatalog(controller.signal)
      .then((strategies) => {
        if (!controller.signal.aborted) setCatalog({ status: 'success', strategies })
      })
      .catch(() => {
        if (!controller.signal.aborted) setCatalog({ status: 'error' })
      })
    return () => controller.abort()
  }, [version])

  function retry() {
    setCatalog({ status: 'loading' })
    setVersion((current) => current + 1)
  }

  return { catalog, retry }
}
