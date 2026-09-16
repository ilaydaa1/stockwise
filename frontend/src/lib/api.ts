const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'


interface ApiResponse<T> {
  data?: T
  error?: string
  status?: number
}


function getCsrfToken(): string {
  const match = document.cookie.match(
    /(?:^|;\s*)sw_csrf=([^;]*)/
  )

  return match
    ? decodeURIComponent(match[1])
    : ''
}


async function request<T>(
  path: string,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(
        options?.headers as Record<string, string> || {}
      ),
    }

    if (
      options?.method &&
      ['POST', 'PUT', 'PATCH', 'DELETE'].includes(
        options.method.toUpperCase()
      )
    ) {
      const csrfToken = getCsrfToken()

      if (csrfToken) {
        headers['x-csrf-token'] = csrfToken
      }
    }

    const response = await fetch(
      `${API_BASE_URL}${path}`,
      {
        credentials: 'include',
        ...options,
        headers,
      }
    )

    if (response.status === 204) {
      return {
        status: response.status,
      }
    }

    const data = await response.json()

    if (!response.ok) {
      return {
        error: data.detail || 'Request failed',
        status: response.status,
      }
    }

    return {
      data,
      status: response.status,
    }
  } catch {
    return {
      error: 'Network error',
    }
  }
}


/* =========================
   USER
========================= */

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


export async function getHealth(): Promise<
  ApiResponse<{ status: string }>
> {
  return request('/api/health')
}


export async function getReady(): Promise<
  ApiResponse<{
    status: string
    database: string
  }>
> {
  return request('/api/ready')
}


export async function registerUser(
  data: RegisterPayload
): Promise<ApiResponse<{ message: string }>> {
  return request('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}


export async function loginUser(
  data: LoginPayload
): Promise<ApiResponse<User>> {
  return request('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}


export async function logoutUser(): Promise<
  ApiResponse<{ message: string }>
> {
  return request('/api/auth/logout', {
    method: 'POST',
  })
}


export async function getMe(): Promise<
  ApiResponse<User>
> {
  return request('/api/auth/me')
}


/* =========================
   BUSINESS
========================= */

export interface Business {
  id: string
  owner_id: string
  name: string
  currency: string
  timezone: string
  created_at: string
  updated_at: string
}


export interface CreateBusinessPayload {
  name: string
  currency?: string
  timezone?: string
}


export async function createBusiness(
  data: CreateBusinessPayload
): Promise<ApiResponse<Business>> {
  return request('/api/businesses', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}


export async function getMyBusiness(): Promise<
  ApiResponse<Business>
> {
  return request('/api/businesses/me')
}


/* =========================
   PRODUCTS
========================= */

export interface Product {
  id: string
  business_id: string
  name: string
  sku: string
  purchase_price: string
  sale_price: string
  stock_quantity: number
  minimum_stock: number
  is_active: boolean
  created_at: string
  updated_at: string
}


export interface CreateProductPayload {
  name: string
  sku: string
  purchase_price: string
  sale_price: string
  stock_quantity?: number
  minimum_stock?: number
}


export interface UpdateProductPayload {
  name?: string
  sku?: string
  purchase_price?: string
  sale_price?: string
  minimum_stock?: number
}


export async function getProducts(): Promise<
  ApiResponse<Product[]>
> {
  return request('/api/products')
}


export async function getProduct(
  productId: string
): Promise<ApiResponse<Product>> {
  return request(
    `/api/products/${productId}`
  )
}


export async function createProduct(
  data: CreateProductPayload
): Promise<ApiResponse<Product>> {
  return request('/api/products', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}


export async function updateProduct(
  productId: string,
  data: UpdateProductPayload
): Promise<ApiResponse<Product>> {
  return request(
    `/api/products/${productId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(data),
    }
  )
}


export async function deleteProduct(
  productId: string
): Promise<ApiResponse<void>> {
  return request(
    `/api/products/${productId}`,
    {
      method: 'DELETE',
    }
  )
}


/* =========================
   STOCK MOVEMENTS
========================= */

export type MovementType =
  | 'IN'
  | 'OUT'
  | 'ADJUSTMENT_IN'
  | 'ADJUSTMENT_OUT'


export interface StockMovement {
  id: string
  business_id: string
  product_id: string
  movement_type: MovementType
  quantity: number
  stock_before: number
  stock_after: number
  note: string | null
  created_at: string
}


export interface CreateStockMovementPayload {
  product_id: string
  movement_type: MovementType
  quantity: number
  note?: string
}


export async function getStockMovements(
  productId?: string
): Promise<ApiResponse<StockMovement[]>> {
  const query = productId
    ? `?product_id=${encodeURIComponent(productId)}`
    : ''

  return request(
    `/api/stock-movements${query}`
  )
}


export async function createStockMovement(
  data: CreateStockMovementPayload
): Promise<ApiResponse<StockMovement>> {
  return request('/api/stock-movements', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}


export { API_BASE_URL }