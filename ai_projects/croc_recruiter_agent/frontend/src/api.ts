export type QueryRequest = {
  question: string
  user_id: string
}

export type QueryResponse = {
  answer: string
  cache_hit: boolean
  engine_used: string | null
  sources: string[]
}

export type McpTool = {
  name: string
  description: string
  url: string
  method: string
}

const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) || 'http://127.0.0.1:8000'

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }

  return (await res.json()) as T
}

export async function healthCheck(): Promise<{ status: string }> {
  return requestJson<{ status: string }>('/')
}

export async function queryAgent(payload: QueryRequest): Promise<QueryResponse> {
  return requestJson<QueryResponse>('/query', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function listMcpTools(): Promise<{ tools: McpTool[] }> {
  return requestJson<{ tools: McpTool[] }>('/mcp/tools', { method: 'GET' })
}

export async function callMcpTool(payload: {
  tool_name: string
  input: Record<string, unknown>
}): Promise<{ tool_name: string; output: unknown }> {
  return requestJson<{ tool_name: string; output: unknown }>('/mcp/call', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
