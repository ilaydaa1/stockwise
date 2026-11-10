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


// FastAPI returns `detail` as a string for HTTPException and as an
// array of { msg, loc, ... } objects for 422 validation errors.
// Callers render the error directly, so it must always be a string.
function extractErrorMessage(body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail

  if (typeof detail === 'string' && detail) {
    return detail
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) =>
        typeof item?.msg === 'string'
          ? item.msg.replace(/^Value error, /, '')
          : ''
      )
      .filter(Boolean)

    if (messages.length > 0) {
      return messages.join(' ')
    }
  }

  const fallback = (body as { error?: unknown } | null)?.error

  return typeof fallback === 'string' && fallback
    ? fallback
    : 'Request failed'
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
        error: extractErrorMessage(data),
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
  remember_me: boolean
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
  category_id: string | null
  supplier_id: string | null
  name: string
  sku: string
  purchase_price: string
  sale_price: string
  average_cost: string
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
  category_id?: string | null
  supplier_id?: string | null
}


export interface UpdateProductPayload {
  name?: string
  sku?: string
  purchase_price?: string
  sale_price?: string
  minimum_stock?: number
  category_id?: string | null
  supplier_id?: string | null
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

export type ManualMovementType =
  | 'IN'
  | 'OUT'
  | 'ADJUSTMENT_IN'
  | 'ADJUSTMENT_OUT'


export type MovementType =
  | ManualMovementType
  | 'SALE'
  | 'OPENING'
  | 'RETURN'


export interface StockMovement {
  id: string
  business_id: string
  product_id: string
  movement_type: MovementType
  quantity: number
  stock_before: number
  stock_after: number
  unit_cost: string | null
  sale_id: string | null
  sale_return_id: string | null
  note: string | null
  created_at: string
}


export interface CreateStockMovementPayload {
  product_id: string
  movement_type: ManualMovementType
  quantity: number
  unit_cost?: string
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


/* =========================
   SALES
========================= */

export interface CreateSaleItemPayload {
  product_id: string
  quantity: number
}


export interface CreateSalePayload {
  items: CreateSaleItemPayload[]
}


export interface SaleItem {
  id: string
  product_id: string
  product_name: string
  product_sku: string
  quantity: number
  unit_sale_price: string
  unit_purchase_price: string
  subtotal: string
  cost: string
  gross_profit: string
}


export interface Sale {
  id: string
  business_id: string
  total_amount: string
  total_cost: string
  gross_profit: string
  created_at: string
  items: SaleItem[]
}


export async function createSale(
  data: CreateSalePayload
): Promise<ApiResponse<Sale>> {
  return request('/api/sales', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}


/* =========================
   DASHBOARD
========================= */

export interface DailyPerformance {
  date: string
  sales: string
  gross_profit: string
}


export interface CriticalProduct {
  id: string
  name: string
  sku: string
  stock_quantity: number
  minimum_stock: number
}


export interface DashboardSummary {
  total_sales: string
  refund_total: string
  net_sales: string
  gross_profit: string
  sale_count: number
  gross_profit_margin: string
  critical_stock_count: number
  daily_performance: DailyPerformance[]
  critical_products: CriticalProduct[]
}


export async function getDashboardSummary(): Promise<
  ApiResponse<DashboardSummary>
> {
  return request('/api/dashboard/summary')
}


/* =========================
   ANALYTICS
========================= */

export interface AnalyticsDailyPerformance {
  date: string
  sales: string
  gross_profit: string
  sale_count: number
}


export interface ProductPerformance {
  product_id: string
  product_name: string
  product_sku: string
  quantity_sold: number
  revenue: string
  gross_profit: string
}


export interface SaleHistoryItem {
  product_id: string
  product_name: string
  product_sku: string
  quantity: number
  unit_sale_price: string
  subtotal: string
}


export interface SaleHistory {
  id: string
  created_at: string
  total_quantity: number
  total_amount: string
  gross_profit: string
  items: SaleHistoryItem[]
}


export interface AnalyticsSummary {
  period_days: number
  total_sales: string
  refund_total: string
  net_sales: string
  gross_profit: string
  sale_count: number
  average_order_value: string
  gross_profit_margin: string
  daily_performance: AnalyticsDailyPerformance[]
  product_performance: ProductPerformance[]
  sales_history: SaleHistory[]
}


/* =========================
   PRODUCT ANALYSIS
========================= */

export interface ProductAnalysisMetrics {
  period_days: number
  quantity_sold: number
  revenue: string
  gross_profit: string
  gross_profit_margin: string
  average_daily_sales: string
  current_stock: number
  stock_coverage_days: string | null
  sales_trend_percent: string | null
}


export interface ProductAnalysis {
  product_id: string
  product_name: string
  product_sku: string
  observation_days: number
  minimum_stock: number
  metrics: ProductAnalysisMetrics
}


export interface ProductAnalysisList {
  period_days: number
  products: ProductAnalysis[]
}


export async function getAnalyticsSummary(
  days: number = 30
): Promise<ApiResponse<AnalyticsSummary>> {
  return request(
    `/api/analytics/summary?days=${days}`
  )
}


export async function getProductAnalysis(
  days: number = 30
): Promise<ApiResponse<ProductAnalysisList>> {
  return request(
    `/api/analytics/products?days=${days}`
  )
}


/* =========================
   CATEGORIES AND SUPPLIERS
========================= */

export interface Category {
  id: string
  business_id: string
  name: string
  created_at: string
}


export interface Supplier {
  id: string
  business_id: string
  name: string
  lead_time_days: number
  created_at: string
}


export interface SupplierPayload {
  name: string
  lead_time_days: number
}


export async function getCategories(): Promise<
  ApiResponse<Category[]>
> {
  return request('/api/categories')
}


export async function createCategory(
  data: { name: string }
): Promise<ApiResponse<Category>> {
  return request('/api/categories', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}


export async function getSuppliers(): Promise<
  ApiResponse<Supplier[]>
> {
  return request('/api/suppliers')
}


export async function createSupplier(
  data: SupplierPayload
): Promise<ApiResponse<Supplier>> {
  return request('/api/suppliers', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}


export async function updateSupplier(
  supplierId: string,
  data: Partial<SupplierPayload>
): Promise<ApiResponse<Supplier>> {
  return request(
    `/api/suppliers/${supplierId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(data),
    }
  )
}


/* =========================
   SALES HISTORY AND RETURNS
========================= */

export interface SaleRecordLine {
  id: string
  product_id: string
  product_name: string
  product_sku: string
  quantity: number
  returned_quantity: number
  unit_sale_price: string
  subtotal: string
}


export interface SaleRecord {
  id: string
  created_at: string
  total_amount: string
  total_cost: string
  gross_profit: string
  refund_amount: string
  items: SaleRecordLine[]
}


export interface SalePage {
  total: number
  limit: number
  offset: number
  items: SaleRecord[]
}


export interface SaleReturn {
  id: string
  sale_id: string
  sale_item_id: string
  product_id: string
  quantity: number
  refund_amount: string
  cost_amount: string
  reason: string | null
  created_at: string
}


export interface CreateSaleReturnPayload {
  items: {
    sale_item_id: string
    quantity: number
  }[]
  reason?: string
}


export async function getSales(
  limit: number = 20,
  offset: number = 0
): Promise<ApiResponse<SalePage>> {
  return request(
    `/api/sales?limit=${limit}&offset=${offset}`
  )
}


export async function createSaleReturn(
  saleId: string,
  data: CreateSaleReturnPayload
): Promise<ApiResponse<SaleReturn[]>> {
  return request(
    `/api/sales/${saleId}/returns`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  )
}


export { API_BASE_URL }