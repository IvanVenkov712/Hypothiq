export interface ParameterDefinition {
  name: string
  label: string
  description: string
  type: 'integer' | 'number' | 'boolean' | 'string'
  default: boolean | number | string | null
  nullable: boolean
  choices: string[] | null
  minimum: number | null
  maximum: number | null
  exclusive_minimum: number | null
  exclusive_maximum: number | null
}

export interface StrategyDefinition {
  class_name: string
  name: string
  description: string
  parameters: ParameterDefinition[]
}

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
