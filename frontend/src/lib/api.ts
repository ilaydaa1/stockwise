const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

interface ApiResponse<T> {
  data?: T
  error?: string
}

async function request<T>(path: string, options?: RequestInit): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    })
    const data = await response.json()
    if (!response.ok) {
      return { error: data.detail || 'Request failed' }
    }
    return { data }
  } catch {
    return { error: 'Network error' }
  }
}

export async function getHealth(): Promise<ApiResponse<{ status: string }>> {
  return request('/api/health')
}

export async function getReady(): Promise<ApiResponse<{ status: string; database: string }>> {
  return request('/api/ready')
}

export { API_BASE_URL }
