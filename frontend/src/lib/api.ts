const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

interface ApiResponse<T> {
  data?: T
  error?: string
  status?: number
}

function getCsrfToken(): string {
  const match = document.cookie.match(/(?:^|;\s*)sw_csrf=([^;]*)/)
  return match ? decodeURIComponent(match[1]) : ''
}

async function request<T>(path: string, options?: RequestInit): Promise<ApiResponse<T>> {
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options?.headers as Record<string, string> || {}),
    }

    if (options?.method && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method.toUpperCase())) {
      const csrfToken = getCsrfToken()
      if (csrfToken) {
        headers['x-csrf-token'] = csrfToken
      }
    }

    const response = await fetch(`${API_BASE_URL}${path}`, {
      credentials: 'include',
      ...options,
      headers,
    })

    const data = await response.json()
    if (!response.ok) {
      return { error: data.detail || 'Request failed', status: response.status }
    }
    return { data, status: response.status }
  } catch {
    return { error: 'Network error' }
  }
}

export interface User {
  id: string
  email: string
  name: string
  created_at: string
}

export interface RegisterPayload {
  name: string
  email: string
  password: string
  password_confirm: string
}

export interface LoginPayload {
  email: string
  password: string
}

export async function getHealth(): Promise<ApiResponse<{ status: string }>> {
  return request('/api/health')
}

export async function getReady(): Promise<ApiResponse<{ status: string; database: string }>> {
  return request('/api/ready')
}

export async function registerUser(data: RegisterPayload): Promise<ApiResponse<{ message: string }>> {
  return request('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function loginUser(data: LoginPayload): Promise<ApiResponse<User>> {
  return request('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function logoutUser(): Promise<ApiResponse<{ message: string }>> {
  return request('/api/auth/logout', {
    method: 'POST',
  })
}

export async function getMe(): Promise<ApiResponse<User>> {
  return request('/api/auth/me')
}

export { API_BASE_URL }
