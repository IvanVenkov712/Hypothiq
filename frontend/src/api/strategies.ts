export interface ParameterChoice {
  /** Registry value submitted to the backtesting API. */
  value: string
  label: string
  description: string
}

export interface ParameterDefinition {
  // Bounds and choices describe the form; execution validation belongs to the backend.
  name: string
  label: string
  description: string
  type: 'integer' | 'number' | 'boolean' | 'string'
  default: boolean | number | string | null
  nullable: boolean
  choices: ParameterChoice[] | null
  minimum: number | null
  maximum: number | null
  exclusive_minimum: number | null
  exclusive_maximum: number | null
}

export interface StrategyDefinition {
  /** Exact registry identifier used as strategy.name when requesting a backtest. */
  class_name: string
  name: string
  description: string
  parameters: ParameterDefinition[]
}

/**
 * Fetch catalogue metadata through the same-origin API proxy.
 * The caller owns cancellation; HTTP failures and aborted requests reject.
 */
export async function fetchStrategyCatalog(signal: AbortSignal): Promise<StrategyDefinition[]> {
  const response = await fetch('/api/strategies', {
    signal,
    headers: { Accept: 'application/json' },
  })

  if (!response.ok) {
    throw new Error(`Strategy catalog request failed (${response.status})`)
  }

  return response.json()
}
