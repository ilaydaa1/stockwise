import {
  useEffect,
  useMemo,
  useState,
} from 'react'

import { useBusiness } from '../contexts/BusinessContext'
import {
  AnalyticsSummary,
  ProductAnalysisList,
  getAnalyticsSummary,
  getProductAnalysis,
} from '../lib/api'

import './dashboard.css'

type PeriodDays = 7 | 30 | 90

type StockStatus =
  | 'critical'
  | 'low'
  | 'normal'

function formatCurrency(
  value: string | number,
  currency: string
) {
  const numericValue =
    typeof value === 'number'
      ? value
      : Number(value)

  return new Intl.NumberFormat(
    'tr-TR',
    {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }
  ).format(numericValue)
}

function formatPercent(
  value: number
) {
  return new Intl.NumberFormat(
    'tr-TR',
    {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    }
  ).format(value)
}

function formatDate(
  value: string
) {
  return new Intl.DateTimeFormat(
    'tr-TR',
    {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }
  ).format(
    new Date(`${value}T00:00:00`)
  )
}

function formatShortDate(
  value: string
) {
  return new Intl.DateTimeFormat(
    'tr-TR',
    {
      day: 'numeric',
      month: 'short',
    }
  ).format(
    new Date(`${value}T00:00:00`)
  )
}

function formatDateTime(
  value: string
) {
  return new Intl.DateTimeFormat(
    'tr-TR',
    {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }
  ).format(new Date(value))
}

function Icon({
  name,
}: {
  name:
    | 'trend'
    | 'profit'
    | 'cart'
    | 'box'
    | 'stock'
    | 'history'
    | 'arrow'
    | 'search'
    | 'warning'
    | 'check'
    | 'spark'
}) {
  const paths = {
    trend:
      'M3 17 9 11l4 4 8-9M17 6h4v4',

    profit:
      'M12 2v20M17 5.5c0-1.7-2.2-3-5-3S7 3.8 7 5.5 9.2 8.5 12 8.5s5 1.3 5 3-2.2 3-5 3-5 1.3-5 3 2.2 3 5 3 5-1.3 5-3',

    cart:
      'M3 4h2l2.2 11h10.5L21 7H6M9 19h.01M18 19h.01',

    box:
      'm12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Zm-8 4.5 8 4.5 8-4.5M12 12v9',

    stock:
      'M4 7h16M4 12h16M4 17h10M17 15l2 2 4-4',

    history:
      'M4 6h16M4 12h16M4 18h16M2 6h.01M2 12h.01M2 18h.01',

    arrow:
      'M5 12h14M13 6l6 6-6 6',

    search:
      'm21 21-4.3-4.3M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z',

    warning:
      'M12 3 2.8 20h18.4L12 3Zm0 6v5M12 17h.01',

    check:
      'm5 12 4 4L19 6',

    spark:
      'm12 2 1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2Z',
  }

  return (
    <svg
      viewBox="0 0 24 24"
      width="19"
      height="19"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name]} />
    </svg>
  )
}

function getStockStatus(
  currentStock: number,
  minimumStock: number
): StockStatus {
  if (currentStock <= minimumStock) {
    return 'critical'
  }

  if (
    currentStock <=
    Math.max(minimumStock * 2, minimumStock + 2)
  ) {
    return 'low'
  }

  return 'normal'
}

function getStockLabel(
  status: StockStatus
) {
  if (status === 'critical') {
    return 'Kritik'
  }

  if (status === 'low') {
    return 'Düşük'
  }

  return 'Normal'
}

function getTrendClass(
  value: string | null
) {
  if (value === null) {
    return 'neutral'
  }

  const numericValue = Number(value)

  if (numericValue > 0) {
    return 'positive'
  }

  if (numericValue < 0) {
    return 'negative'
  }

  return 'neutral'
}

function getTrendText(
  value: string | null
) {
  if (value === null) {
    return 'Karşılaştırma yok'
  }

  const numericValue = Number(value)

  if (numericValue > 0) {
    return `+%${formatPercent(numericValue)}`
  }

  if (numericValue < 0) {
    return `-%${formatPercent(Math.abs(numericValue))}`
  }

  return '%0,0'
}

export default function Analytics() {
  const { business } = useBusiness()

  const [period, setPeriod] =
    useState<PeriodDays>(30)

  const [data, setData] =
    useState<AnalyticsSummary | null>(null)

  const [productData, setProductData] =
    useState<ProductAnalysisList | null>(null)

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState('')

  const [productSearch, setProductSearch] =
    useState('')

  const currency =
    business?.currency || 'TRY'

  useEffect(() => {
    let active = true

    const loadAnalytics = async () => {
      setLoading(true)
      setError('')

      const [
        analyticsResponse,
        productResponse,
      ] = await Promise.all([
        getAnalyticsSummary(period),
        getProductAnalysis(period),
      ])

      if (!active) {
        return
      }

      if (
        analyticsResponse.error ||
        !analyticsResponse.data
      ) {
        setError(
          analyticsResponse.error ||
            'Analiz verileri alınamadı.'
        )

        setLoading(false)
        return
      }

      if (
        productResponse.error ||
        !productResponse.data
      ) {
        setError(
          productResponse.error ||
            'Ürün analizleri alınamadı.'
        )

        setLoading(false)
        return
      }

      setData(analyticsResponse.data)
      setProductData(productResponse.data)
      setLoading(false)
    }

    loadAnalytics()

    return () => {
      active = false
    }
  }, [period])

  const filteredProducts =
    useMemo(() => {
      if (!productData) {
        return []
      }

      const query =
        productSearch
          .trim()
          .toLocaleLowerCase('tr-TR')

      if (!query) {
        return productData.products
      }

      return productData.products.filter(
        (product) =>
          product.product_name
            .toLocaleLowerCase('tr-TR')
            .includes(query) ||
          product.product_sku
            .toLocaleLowerCase('tr-TR')
            .includes(query)
      )
    }, [
      productData,
      productSearch,
    ])

  const topSellingProducts =
    useMemo(() => {
      if (!productData) {
        return []
      }

      return [
        ...productData.products,
      ]
        .sort(
          (a, b) =>
            b.metrics.quantity_sold -
            a.metrics.quantity_sold
        )
        .slice(0, 5)
    }, [productData])

  const highestRevenueProducts =
    useMemo(() => {
      if (!productData) {
        return []
      }

      return [
        ...productData.products,
      ]
        .sort(
          (a, b) =>
            Number(b.metrics.revenue) -
            Number(a.metrics.revenue)
        )
        .slice(0, 5)
    }, [productData])

  const highestProfitProducts =
    useMemo(() => {
      if (!productData) {
        return []
      }

      return [
        ...productData.products,
      ]
        .sort(
          (a, b) =>
            Number(b.metrics.gross_profit) -
            Number(a.metrics.gross_profit)
        )
        .slice(0, 5)
    }, [productData])

  const stockAnalysis =
    useMemo(() => {
      if (!productData || !data) {
        return []
      }

      return productData.products
        .map((product) => {
          const minimumStock =
            product.minimum_stock

          const status =
            getStockStatus(
              product.metrics.current_stock,
              minimumStock
            )

          return {
            ...product,
            minimumStock,
            status,
          }
        })
        .sort((a, b) => {
          const statusOrder = {
            critical: 0,
            low: 1,
            normal: 2,
          }

          if (
            statusOrder[a.status] !==
            statusOrder[b.status]
          ) {
            return (
              statusOrder[a.status] -
              statusOrder[b.status]
            )
          }

          const aCoverage =
            a.metrics.stock_coverage_days ===
            null
              ? Infinity
              : Number(
                  a.metrics.stock_coverage_days
                )

          const bCoverage =
            b.metrics.stock_coverage_days ===
            null
              ? Infinity
              : Number(
                  b.metrics.stock_coverage_days
                )

          return aCoverage - bCoverage
        })
    }, [productData, data])

  const criticalProducts =
    useMemo(
      () =>
        stockAnalysis.filter(
          (product) =>
            product.status === 'critical'
        ),
      [stockAnalysis]
    )

  const lowStockProducts =
    useMemo(
      () =>
        stockAnalysis.filter(
          (product) =>
            product.status === 'low'
        ),
      [stockAnalysis]
    )

  const normalStockProducts =
    useMemo(
      () =>
        stockAnalysis.filter(
          (product) =>
            product.status === 'normal'
        ),
      [stockAnalysis]
    )

  const chart = useMemo(() => {
    if (
      !data ||
      data.daily_performance.length === 0
    ) {
      return null
    }

    const values =
      data.daily_performance

    const width = 900
    const height = 310

    const padding = {
      top: 24,
      right: 24,
      bottom: 45,
      left: 64,
    }

    const innerWidth =
      width -
      padding.left -
      padding.right

    const innerHeight =
      height -
      padding.top -
      padding.bottom

    const maxValue = Math.max(
      ...values.flatMap(
        (item) => [
          Number(item.sales),
          Number(item.gross_profit),
        ]
      ),
      1
    )

    const roundedMax =
      Math.ceil(maxValue / 100) *
        100 ||
      100

    const getX = (
      index: number
    ) => {
      if (values.length === 1) {
        return (
          padding.left +
          innerWidth / 2
        )
      }

      return (
        padding.left +
        (index /
          (values.length - 1)) *
          innerWidth
      )
    }

    const getY = (
      value: number
    ) =>
      padding.top +
      innerHeight -
      (value / roundedMax) *
        innerHeight

    const salesPoints =
      values
        .map(
          (item, index) =>
            `${getX(index)},${getY(
              Number(item.sales)
            )}`
        )
        .join(' ')

    const profitPoints =
      values
        .map(
          (item, index) =>
            `${getX(index)},${getY(
              Number(
                item.gross_profit
              )
            )}`
        )
        .join(' ')

    return {
      values,
      width,
      height,
      padding,
      innerWidth,
      innerHeight,
      roundedMax,
      getX,
      getY,
      salesPoints,
      profitPoints,
    }
  }, [data])

  const recentSales =
    useMemo(() => {
      if (!data) {
        return []
      }

      return data.sales_history
        .slice(0, 5)
    }, [data])

  const totalProducts =
    productData?.products.length || 0

  const stockCoverageProducts =
    useMemo(() => {
      if (!productData) {
        return []
      }

      return productData.products
        .filter(
          (product) =>
            product.metrics
              .stock_coverage_days !==
            null
        )
        .sort(
          (a, b) =>
            Number(
              a.metrics
                .stock_coverage_days
            ) -
            Number(
              b.metrics
                .stock_coverage_days
            )
        )
        .slice(0, 5)
    }, [productData])

  if (loading && !data) {
    return (
      <main
        id="sw-main"
        className="sw-main"
      >
        <div className="sw-analytics-state">
          <strong>
            Analizler yükleniyor...
          </strong>

          <span>
            Satış ve ürün verileri
            hazırlanıyor.
          </span>
        </div>
      </main>
    )
  }

  if (error && !data) {
    return (
      <main
        id="sw-main"
        className="sw-main"
      >
        <div className="sw-analytics-state">
          <strong>
            Analiz verileri
            yüklenemedi
          </strong>

          <span>{error}</span>
        </div>
      </main>
    )
  }

  return (
    <main
      id="sw-main"
      className="sw-main sw-analytics"
    >
      <style>
        {`
          .sw-modern-analytics {
            display: flex;
            flex-direction: column;
            gap: 18px;
          }

          .sw-modern-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 20px;
          }

          .sw-modern-header h1 {
            margin: 0;
          }

          .sw-modern-header p {
            margin: 5px 0 0;
            color: #64748b;
          }

          .sw-modern-periods {
            display: inline-flex;
            padding: 4px;
            gap: 3px;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            background: #f8fafc;
          }

          .sw-modern-periods button {
            border: 0;
            background: transparent;
            color: #64748b;
            padding: 7px 12px;
            border-radius: 7px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
          }

          .sw-modern-periods button.is-active {
            background: #fff;
            color: #0f172a;
            box-shadow: 0 1px 3px rgba(15, 23, 42, .10);
          }

          .sw-modern-periods button:disabled {
            opacity: .55;
            cursor: not-allowed;
          }

          .sw-modern-error {
            border: 1px solid #fecaca;
            background: #fff7f7;
            color: #b91c1c;
            padding: 10px 13px;
            border-radius: 9px;
            font-size: 13px;
          }

          .sw-kpi-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
          }

          .sw-kpi-card {
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            background: #fff;
            padding: 16px;
          }

          .sw-kpi-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
          }

          .sw-kpi-label {
            color: #64748b;
            font-size: 12px;
            font-weight: 600;
          }

          .sw-kpi-icon {
            width: 34px;
            height: 34px;
            display: grid;
            place-items: center;
            border-radius: 9px;
            background: #f1f5f9;
            color: #475569;
          }

          .sw-kpi-value {
            display: block;
            margin-top: 10px;
            color: #0f172a;
            font-size: 21px;
            font-weight: 700;
            letter-spacing: -.02em;
          }

          .sw-kpi-sub {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-top: 6px;
            color: #94a3b8;
            font-size: 11px;
          }

          .sw-trend-positive {
            color: #15803d;
            font-weight: 700;
          }

          .sw-trend-negative {
            color: #dc2626;
            font-weight: 700;
          }

          .sw-trend-neutral {
            color: #64748b;
            font-weight: 600;
          }

          .sw-modern-grid {
            display: grid;
            grid-template-columns: minmax(0, 1.65fr) minmax(300px, .85fr);
            gap: 14px;
          }

          .sw-modern-card {
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            background: #fff;
            overflow: hidden;
          }

          .sw-modern-card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 16px;
            padding: 16px 18px;
            border-bottom: 1px solid #f1f5f9;
          }

          .sw-modern-card-header h2 {
            margin: 0;
            font-size: 14px;
            color: #0f172a;
          }

          .sw-modern-card-header p {
            margin: 4px 0 0;
            color: #94a3b8;
            font-size: 11px;
          }

          .sw-modern-legend {
            display: flex;
            gap: 12px;
            color: #64748b;
            font-size: 11px;
            white-space: nowrap;
          }

          .sw-modern-legend span {
            display: inline-flex;
            align-items: center;
            gap: 5px;
          }

          .sw-modern-legend i {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            display: inline-block;
          }

          .sw-modern-legend .sales-dot {
            background: #2563eb;
          }

          .sw-modern-legend .profit-dot {
            background: #16a34a;
          }

          .sw-chart-container {
            padding: 10px 14px 14px;
          }

          .sw-modern-chart {
            width: 100%;
            height: 300px;
            display: block;
          }

          .sw-chart-grid {
            stroke: #eef2f7;
            stroke-width: 1;
          }

          .sw-chart-axis {
            fill: #94a3b8;
            font-size: 10px;
          }

          .sw-chart-sales {
            fill: none;
            stroke: #2563eb;
            stroke-width: 2.5;
            stroke-linejoin: round;
            stroke-linecap: round;
          }

          .sw-chart-profit {
            fill: none;
            stroke: #16a34a;
            stroke-width: 2.5;
            stroke-linejoin: round;
            stroke-linecap: round;
          }

          .sw-chart-sales-dot {
            fill: #fff;
            stroke: #2563eb;
            stroke-width: 2;
          }

          .sw-chart-profit-dot {
            fill: #fff;
            stroke: #16a34a;
            stroke-width: 2;
          }

          .sw-performance-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
          }

          .sw-performance-card {
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            background: #fff;
            overflow: hidden;
          }

          .sw-performance-title {
            padding: 14px 16px;
            border-bottom: 1px solid #f1f5f9;
          }

          .sw-performance-title strong {
            display: block;
            color: #0f172a;
            font-size: 13px;
          }

          .sw-performance-title span {
            display: block;
            margin-top: 3px;
            color: #94a3b8;
            font-size: 10px;
          }

          .sw-performance-list {
            padding: 4px 0;
          }

          .sw-performance-row {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 14px;
            border-bottom: 1px solid #f8fafc;
          }

          .sw-performance-row:last-child {
            border-bottom: 0;
          }

          .sw-rank {
            width: 22px;
            color: #94a3b8;
            font-size: 11px;
            text-align: center;
            flex: 0 0 22px;
          }

          .sw-performance-product {
            min-width: 0;
            flex: 1;
          }

          .sw-performance-product strong {
            display: block;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            color: #334155;
            font-size: 12px;
          }

          .sw-performance-product span {
            display: block;
            margin-top: 2px;
            color: #94a3b8;
            font-size: 10px;
          }

          .sw-performance-value {
            text-align: right;
            color: #0f172a;
            font-size: 11px;
            font-weight: 700;
            white-space: nowrap;
          }

          .sw-performance-trend {
            display: block;
            margin-top: 2px;
            font-size: 10px;
            font-weight: 600;
          }

          .sw-stock-summary {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            padding: 14px 16px;
          }

          .sw-stock-count {
            border: 1px solid #e2e8f0;
            border-radius: 9px;
            padding: 10px;
            background: #fafafa;
          }

          .sw-stock-count strong {
            display: block;
            font-size: 19px;
            color: #0f172a;
          }

          .sw-stock-count span {
            display: block;
            margin-top: 2px;
            color: #64748b;
            font-size: 10px;
          }

          .sw-stock-count.is-critical {
            border-color: #fecaca;
            background: #fff7f7;
          }

          .sw-stock-count.is-critical strong {
            color: #dc2626;
          }

          .sw-stock-count.is-low {
            border-color: #fed7aa;
            background: #fffaf3;
          }

          .sw-stock-count.is-low strong {
            color: #ea580c;
          }

          .sw-stock-count.is-normal strong {
            color: #15803d;
          }

          .sw-stock-list {
            padding: 0 16px 12px;
          }

          .sw-stock-row {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 9px 0;
            border-top: 1px solid #f1f5f9;
          }

          .sw-stock-status {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            flex: 0 0 7px;
          }

          .sw-stock-status.critical {
            background: #dc2626;
          }

          .sw-stock-status.low {
            background: #ea580c;
          }

          .sw-stock-status.normal {
            background: #16a34a;
          }

          .sw-stock-product {
            min-width: 0;
            flex: 1;
          }

          .sw-stock-product strong {
            display: block;
            color: #334155;
            font-size: 11px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }

          .sw-stock-product span {
            display: block;
            margin-top: 2px;
            color: #94a3b8;
            font-size: 9px;
          }

          .sw-stock-value {
            text-align: right;
            white-space: nowrap;
          }

          .sw-stock-value strong {
            display: block;
            color: #0f172a;
            font-size: 11px;
          }

          .sw-stock-value span {
            color: #94a3b8;
            font-size: 9px;
          }

          .sw-stock-more {
            display: block;
            padding: 8px 16px 14px;
            color: #64748b;
            font-size: 10px;
            font-weight: 600;
          }

          .sw-analysis-toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 14px;
            padding: 15px 18px;
            border-bottom: 1px solid #f1f5f9;
          }

          .sw-analysis-toolbar h2 {
            margin: 0;
            color: #0f172a;
            font-size: 14px;
          }

          .sw-analysis-toolbar p {
            margin: 4px 0 0;
            color: #94a3b8;
            font-size: 11px;
          }

          .sw-modern-search {
            position: relative;
            width: 230px;
          }

          .sw-modern-search svg {
            position: absolute;
            left: 9px;
            top: 50%;
            transform: translateY(-50%);
            color: #94a3b8;
          }

          .sw-modern-search input {
            width: 100%;
            height: 34px;
            padding: 0 10px 0 32px;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            outline: none;
            font-size: 11px;
            background: #fff;
            box-sizing: border-box;
          }

          .sw-modern-search input:focus {
            border-color: #cbd5e1;
          }

          .sw-product-table {
            width: 100%;
            border-collapse: collapse;
          }

          .sw-product-table th {
            padding: 9px 16px;
            text-align: left;
            color: #94a3b8;
            background: #fafafa;
            border-bottom: 1px solid #f1f5f9;
            font-size: 10px;
            font-weight: 600;
          }

          .sw-product-table td {
            padding: 11px 16px;
            color: #475569;
            border-bottom: 1px solid #f8fafc;
            font-size: 11px;
          }

          .sw-product-table tbody tr:last-child td {
            border-bottom: 0;
          }

          .sw-product-table td strong {
            color: #334155;
          }

          .sw-product-table .right {
            text-align: right;
          }

          .sw-margin {
            display: inline-flex;
            padding: 3px 7px;
            border-radius: 6px;
            background: #f0fdf4;
            color: #15803d;
            font-size: 10px;
            font-weight: 700;
          }

          .sw-product-trend {
            font-weight: 700;
          }

          .sw-product-trend.positive {
            color: #15803d;
          }

          .sw-product-trend.negative {
            color: #dc2626;
          }

          .sw-product-trend.neutral {
            color: #94a3b8;
          }

          .sw-modern-footer {
            padding: 9px 16px;
            border-top: 1px solid #f1f5f9;
            color: #94a3b8;
            font-size: 10px;
          }

          .sw-recent-list {
            display: flex;
            flex-direction: column;
          }

          .sw-recent-row {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 12px 16px;
            border-bottom: 1px solid #f1f5f9;
          }

          .sw-recent-row:last-child {
            border-bottom: 0;
          }

          .sw-recent-date {
            min-width: 125px;
            color: #64748b;
            font-size: 10px;
          }

          .sw-recent-products {
            min-width: 0;
            flex: 1;
          }

          .sw-recent-products strong {
            display: block;
            color: #334155;
            font-size: 11px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }

          .sw-recent-products span {
            display: block;
            margin-top: 3px;
            color: #94a3b8;
            font-size: 9px;
          }

          .sw-recent-amount {
            text-align: right;
            white-space: nowrap;
          }

          .sw-recent-amount strong {
            display: block;
            color: #0f172a;
            font-size: 11px;
          }

          .sw-recent-amount span {
            display: block;
            margin-top: 2px;
            color: #15803d;
            font-size: 9px;
          }

          .sw-all-link {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            color: #64748b;
            font-size: 10px;
            font-weight: 600;
          }

          .sw-all-link svg {
            width: 13px;
            height: 13px;
          }

          .sw-empty {
            padding: 24px 16px;
            text-align: center;
            color: #94a3b8;
            font-size: 11px;
          }

          .sw-stock-coverage-grid {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 8px;
            padding: 14px 16px;
          }

          .sw-coverage-item {
            border: 1px solid #e2e8f0;
            border-radius: 9px;
            padding: 10px;
            min-width: 0;
          }

          .sw-coverage-item strong {
            display: block;
            color: #334155;
            font-size: 11px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }

          .sw-coverage-item span {
            display: block;
            margin-top: 5px;
            color: #64748b;
            font-size: 10px;
          }

          @media (max-width: 1100px) {
            .sw-kpi-grid {
              grid-template-columns: repeat(2, 1fr);
            }

            .sw-modern-grid {
              grid-template-columns: 1fr;
            }

            .sw-performance-grid {
              grid-template-columns: 1fr;
            }

            .sw-stock-coverage-grid {
              grid-template-columns: repeat(3, 1fr);
            }
          }

          @media (max-width: 700px) {
            .sw-modern-header {
              flex-direction: column;
            }

            .sw-modern-periods {
              width: 100%;
            }

            .sw-modern-periods button {
              flex: 1;
            }

            .sw-kpi-grid {
              grid-template-columns: 1fr 1fr;
            }

            .sw-analysis-toolbar {
              align-items: stretch;
              flex-direction: column;
            }

            .sw-modern-search {
              width: 100%;
            }

            .sw-product-table {
              min-width: 700px;
            }

            .sw-product-table-wrap {
              overflow-x: auto;
            }

            .sw-stock-coverage-grid {
              grid-template-columns: 1fr 1fr;
            }
          }
        `}
      </style>

      <div className="sw-modern-analytics">
        <section className="sw-modern-header">
          <div>
            <h1>Analizler</h1>
            <p>
              İşletmenizin satış, kârlılık,
              ürün ve stok performansını
              inceleyin.
            </p>
          </div>

          <div className="sw-modern-periods">
            {(
              [7, 30, 90] as PeriodDays[]
            ).map((days) => (
              <button
                key={days}
                type="button"
                className={
                  period === days
                    ? 'is-active'
                    : ''
                }
                onClick={() =>
                  setPeriod(days)
                }
                disabled={loading}
              >
                {days} gün
              </button>
            ))}
          </div>
        </section>

        {error && (
          <div className="sw-modern-error">
            {error}
          </div>
        )}

        <section className="sw-kpi-grid">
          <article className="sw-kpi-card">
            <div className="sw-kpi-top">
              <span className="sw-kpi-label">
                Toplam Satış
              </span>

              <span className="sw-kpi-icon">
                <Icon name="cart" />
              </span>
            </div>

            <strong className="sw-kpi-value">
              {formatCurrency(
                data?.total_sales || '0',
                currency
              )}
            </strong>

            <div className="sw-kpi-sub">
              <span>
                {data?.sale_count || 0}{' '}
                satış işlemi
              </span>
            </div>
          </article>

          <article className="sw-kpi-card">
            <div className="sw-kpi-top">
              <span className="sw-kpi-label">
                Brüt Kâr
              </span>

              <span className="sw-kpi-icon">
                <Icon name="profit" />
              </span>
            </div>

            <strong className="sw-kpi-value">
              {formatCurrency(
                data?.gross_profit || '0',
                currency
              )}
            </strong>

            <div className="sw-kpi-sub">
              <span>
                Marj %{data?.gross_profit_margin || '0'}
              </span>
            </div>
          </article>

          <article className="sw-kpi-card">
            <div className="sw-kpi-top">
              <span className="sw-kpi-label">
                Kâr Marjı
              </span>

              <span className="sw-kpi-icon">
                <Icon name="trend" />
              </span>
            </div>

            <strong className="sw-kpi-value">
              %{data?.gross_profit_margin || '0'}
            </strong>

            <div className="sw-kpi-sub">
              <span>
                Seçilen dönemin brüt marjı
              </span>
            </div>
          </article>

          <article className="sw-kpi-card">
            <div className="sw-kpi-top">
              <span className="sw-kpi-label">
                Ortalama Sepet
              </span>

              <span className="sw-kpi-icon">
                <Icon name="box" />
              </span>
            </div>

            <strong className="sw-kpi-value">
              {formatCurrency(
                data?.average_order_value ||
                  '0',
                currency
              )}
            </strong>

            <div className="sw-kpi-sub">
              <span>
                Satış başına ortalama
              </span>
            </div>
          </article>
        </section>

        <section className="sw-modern-grid">
          <article className="sw-modern-card">
            <div className="sw-modern-card-header">
              <div>
                <h2>
                  Satış ve Brüt Kâr Trendi
                </h2>

                <p>
                  Son {period} gündeki günlük
                  performans
                </p>
              </div>

              <div className="sw-modern-legend">
                <span>
                  <i className="sales-dot" />
                  Satış
                </span>

                <span>
                  <i className="profit-dot" />
                  Brüt Kâr
                </span>
              </div>
            </div>

            {chart ? (
              <div className="sw-chart-container">
                <svg
                  viewBox={`0 0 ${chart.width} ${chart.height}`}
                  className="sw-modern-chart"
                  role="img"
                  aria-label="Satış ve brüt kâr trendi"
                >
                  {[0, 0.25, 0.5, 0.75, 1].map(
                    (ratio) => {
                      const y =
                        chart.padding.top +
                        chart.innerHeight *
                          ratio

                      const value =
                        chart.roundedMax *
                        (1 - ratio)

                      return (
                        <g key={ratio}>
                          <line
                            x1={
                              chart.padding.left
                            }
                            x2={
                              chart.width -
                              chart.padding.right
                            }
                            y1={y}
                            y2={y}
                            className="sw-chart-grid"
                          />

                          <text
                            x="6"
                            y={y + 4}
                            className="sw-chart-axis"
                          >
                            {formatCurrency(
                              value,
                              currency
                            )}
                          </text>
                        </g>
                      )
                    }
                  )}

                  <polyline
                    points={
                      chart.salesPoints
                    }
                    className="sw-chart-sales"
                  />

                  <polyline
                    points={
                      chart.profitPoints
                    }
                    className="sw-chart-profit"
                  />

                  {chart.values.map(
                    (item, index) => {
                      const showLabel =
                        index === 0 ||
                        index ===
                          chart.values
                            .length -
                            1 ||
                        chart.values.length <=
                          7 ||
                        index %
                          Math.max(
                            1,
                            Math.floor(
                              chart.values
                                .length /
                                6
                            )
                          ) ===
                          0

                      return (
                        <g
                          key={item.date}
                        >
                          <circle
                            cx={chart.getX(
                              index
                            )}
                            cy={chart.getY(
                              Number(
                                item.sales
                              )
                            )}
                            r="4"
                            className="sw-chart-sales-dot"
                          >
                            <title>
                              {formatDate(
                                item.date
                              )}
                              {' · '}
                              Satış:{' '}
                              {formatCurrency(
                                item.sales,
                                currency
                              )}
                            </title>
                          </circle>

                          <circle
                            cx={chart.getX(
                              index
                            )}
                            cy={chart.getY(
                              Number(
                                item.gross_profit
                              )
                            )}
                            r="3.5"
                            className="sw-chart-profit-dot"
                          >
                            <title>
                              {formatDate(
                                item.date
                              )}
                              {' · '}
                              Brüt Kâr:{' '}
                              {formatCurrency(
                                item.gross_profit,
                                currency
                              )}
                            </title>
                          </circle>

                          {showLabel && (
                            <text
                              x={chart.getX(
                                index
                              )}
                              y={
                                chart.height -
                                10
                              }
                              textAnchor={
                                index === 0
                                  ? 'start'
                                  : index ===
                                      chart.values
                                        .length -
                                        1
                                    ? 'end'
                                    : 'middle'
                              }
                              className="sw-chart-axis"
                            >
                              {formatShortDate(
                                item.date
                              )}
                            </text>
                          )}
                        </g>
                      )
                    }
                  )}
                </svg>
              </div>
            ) : (
              <div className="sw-empty">
                Bu dönemde yeterli satış
                verisi bulunmuyor.
              </div>
            )}
          </article>

          <article className="sw-modern-card">
            <div className="sw-modern-card-header">
              <div>
                <h2>
                  Stok Durumu
                </h2>

                <p>
                  Mevcut stok seviyelerinin
                  özeti
                </p>
              </div>

              <span className="sw-kpi-icon">
                <Icon name="stock" />
              </span>
            </div>

            <div className="sw-stock-summary">
              <div className="sw-stock-count is-critical">
                <strong>
                  {criticalProducts.length}
                </strong>
                <span>
                  Kritik
                </span>
              </div>

              <div className="sw-stock-count is-low">
                <strong>
                  {lowStockProducts.length}
                </strong>
                <span>
                  Düşük
                </span>
              </div>

              <div className="sw-stock-count is-normal">
                <strong>
                  {normalStockProducts.length}
                </strong>
                <span>
                  Normal
                </span>
              </div>
            </div>

            <div className="sw-stock-list">
              {stockAnalysis
                .slice(0, 6)
                .map((product) => (
                  <div
                    className="sw-stock-row"
                    key={product.product_id}
                  >
                    <span
                      className={`sw-stock-status ${product.status}`}
                    />

                    <div className="sw-stock-product">
                      <strong>
                        {product.product_name}
                      </strong>

                      <span>
                        {getStockLabel(
                          product.status
                        )}
                      </span>
                    </div>

                    <div className="sw-stock-value">
                      <strong>
                        {
                          product.metrics
                            .current_stock
                        }{' '}
                        adet
                      </strong>

                      <span>
                        {product.metrics
                          .stock_coverage_days !==
                        null
                          ? `${product.metrics.stock_coverage_days} gün`
                          : 'Kapsam yok'}
                      </span>
                    </div>
                  </div>
                ))}
            </div>

            {totalProducts > 6 && (
              <span className="sw-stock-more">
                {totalProducts - 6} ürün daha
              </span>
            )}
          </article>
        </section>

        <section className="sw-performance-grid">
          <article className="sw-performance-card">
            <div className="sw-performance-title">
              <strong>
                En Çok Satanlar
              </strong>
              <span>
                Satılan adet bazında
              </span>
            </div>

            <div className="sw-performance-list">
              {topSellingProducts.length ===
              0 ? (
                <div className="sw-empty">
                  Satış bulunmuyor.
                </div>
              ) : (
                topSellingProducts.map(
                  (product, index) => (
                    <div
                      className="sw-performance-row"
                      key={product.product_id}
                    >
                      <span className="sw-rank">
                        {index + 1}
                      </span>

                      <div className="sw-performance-product">
                        <strong>
                          {product.product_name}
                        </strong>

                        <span>
                          {product.product_sku}
                        </span>
                      </div>

                      <div className="sw-performance-value">
                        {
                          product.metrics
                            .quantity_sold
                        }{' '}
                        adet
                      </div>
                    </div>
                  )
                )
              )}
            </div>
          </article>

          <article className="sw-performance-card">
            <div className="sw-performance-title">
              <strong>
                En Yüksek Ciro
              </strong>
              <span>
                Gelir katkısı bazında
              </span>
            </div>

            <div className="sw-performance-list">
              {highestRevenueProducts.length ===
              0 ? (
                <div className="sw-empty">
                  Satış bulunmuyor.
                </div>
              ) : (
                highestRevenueProducts.map(
                  (product, index) => (
                    <div
                      className="sw-performance-row"
                      key={product.product_id}
                    >
                      <span className="sw-rank">
                        {index + 1}
                      </span>

                      <div className="sw-performance-product">
                        <strong>
                          {product.product_name}
                        </strong>

                        <span>
                          {product.product_sku}
                        </span>
                      </div>

                      <div className="sw-performance-value">
                        {formatCurrency(
                          product.metrics
                            .revenue,
                          currency
                        )}
                      </div>
                    </div>
                  )
                )
              )}
            </div>
          </article>

          <article className="sw-performance-card">
            <div className="sw-performance-title">
              <strong>
                En Yüksek Kâr
              </strong>
              <span>
                Brüt kâr katkısı bazında
              </span>
            </div>

            <div className="sw-performance-list">
              {highestProfitProducts.length ===
              0 ? (
                <div className="sw-empty">
                  Kâr verisi bulunmuyor.
                </div>
              ) : (
                highestProfitProducts.map(
                  (product, index) => (
                    <div
                      className="sw-performance-row"
                      key={product.product_id}
                    >
                      <span className="sw-rank">
                        {index + 1}
                      </span>

                      <div className="sw-performance-product">
                        <strong>
                          {product.product_name}
                        </strong>

                        <span>
                          {product.product_sku}
                        </span>
                      </div>

                      <div className="sw-performance-value">
                        {formatCurrency(
                          product.metrics
                            .gross_profit,
                          currency
                        )}
                      </div>
                    </div>
                  )
                )
              )}
            </div>
          </article>
        </section>

        <section className="sw-modern-card">
          <div className="sw-analysis-toolbar">
            <div>
              <h2>
                Ürün Performansı
              </h2>

              <p>
                Ürün bazında satış, ciro,
                kâr ve trend karşılaştırması
              </p>
            </div>

            <label className="sw-modern-search">
              <Icon name="search" />

              <input
                type="search"
                value={productSearch}
                onChange={(event) =>
                  setProductSearch(
                    event.target.value
                  )
                }
                placeholder="Ürün veya SKU ara..."
                aria-label="Ürün ara"
              />
            </label>
          </div>

          <div className="sw-product-table-wrap">
            <table className="sw-product-table">
              <thead>
                <tr>
                  <th>Ürün</th>
                  <th>SKU</th>
                  <th className="right">
                    Satılan
                  </th>
                  <th className="right">
                    Ciro
                  </th>
                  <th className="right">
                    Brüt Kâr
                  </th>
                  <th className="right">
                    Marj
                  </th>
                  <th className="right">
                    Trend
                  </th>
                  <th className="right">
                    Stok
                  </th>
                </tr>
              </thead>

              <tbody>
                {filteredProducts.map(
                  (product) => {
                    const revenue =
                      Number(
                        product.metrics
                          .revenue
                      )

                    const profit =
                      Number(
                        product.metrics
                          .gross_profit
                      )

                    const margin =
                      revenue > 0
                        ? (profit /
                            revenue) *
                          100
                        : 0

                    const trend =
                      getTrendClass(
                        product.metrics
                          .sales_trend_percent
                      )

                    return (
                      <tr
                        key={
                          product.product_id
                        }
                      >
                        <td>
                          <strong>
                            {
                              product.product_name
                            }
                          </strong>
                        </td>

                        <td>
                          {
                            product.product_sku
                          }
                        </td>

                        <td className="right">
                          {
                            product.metrics
                              .quantity_sold
                          }
                        </td>

                        <td className="right">
                          {formatCurrency(
                            product.metrics
                              .revenue,
                            currency
                          )}
                        </td>

                        <td className="right">
                          {formatCurrency(
                            product.metrics
                              .gross_profit,
                            currency
                          )}
                        </td>

                        <td className="right">
                          <span className="sw-margin">
                            %
                            {formatPercent(
                              margin
                            )}
                          </span>
                        </td>

                        <td className="right">
                          <span
                            className={`sw-product-trend ${trend}`}
                          >
                            {getTrendText(
                              product.metrics
                                .sales_trend_percent
                            )}
                          </span>
                        </td>

                        <td className="right">
                          {
                            product.metrics
                              .current_stock
                          }
                        </td>
                      </tr>
                    )
                  }
                )}
              </tbody>
            </table>
          </div>

          {filteredProducts.length ===
            0 && (
            <div className="sw-empty">
              Eşleşen ürün bulunamadı.
            </div>
          )}

          <div className="sw-modern-footer">
            {filteredProducts.length} ürün
            gösteriliyor
          </div>
        </section>

        <section className="sw-modern-card">
          <div className="sw-modern-card-header">
            <div>
              <h2>
                Stok Kapsamı
              </h2>

              <p>
                Mevcut stokların tahmini
                satış süresi
              </p>
            </div>

            <span className="sw-kpi-icon">
              <Icon name="box" />
            </span>
          </div>

          {stockCoverageProducts.length ===
          0 ? (
            <div className="sw-empty">
              Stok kapsamı hesaplanabilen
              ürün bulunmuyor.
            </div>
          ) : (
            <div className="sw-stock-coverage-grid">
              {stockCoverageProducts.map(
                (product) => {
                  const coverage =
                    Number(
                      product.metrics
                        .stock_coverage_days
                    )

                  return (
                    <div
                      className="sw-coverage-item"
                      key={
                        product.product_id
                      }
                    >
                      <strong>
                        {
                          product.product_name
                        }
                      </strong>

                      <span>
                        Yaklaşık{' '}
                        {formatPercent(
                          coverage
                        )}{' '}
                        gün
                      </span>
                    </div>
                  )
                }
              )}
            </div>
          )}
        </section>

        <section className="sw-modern-card">
          <div className="sw-modern-card-header">
            <div>
              <h2>
                Son Satışlar
              </h2>

              <p>
                Seçilen dönemdeki son
                işlemler
              </p>
            </div>

            <span className="sw-all-link">
              Tümünü Gör
              <Icon name="arrow" />
            </span>
          </div>

          {recentSales.length === 0 ? (
            <div className="sw-empty">
              Bu dönemde satış bulunmuyor.
            </div>
          ) : (
            <div className="sw-recent-list">
              {recentSales.map((sale) => {
                const productNames =
                  sale.items
                    .map(
                      (item) =>
                        `${item.product_name} × ${item.quantity}`
                    )
                    .join(', ')

                return (
                  <div
                    className="sw-recent-row"
                    key={sale.id}
                  >
                    <div className="sw-recent-date">
                      {formatDateTime(
                        sale.created_at
                      )}
                    </div>

                    <div className="sw-recent-products">
                      <strong>
                        {productNames}
                      </strong>

                      <span>
                        {sale.total_quantity}{' '}
                        ürün
                      </span>
                    </div>

                    <div className="sw-recent-amount">
                      <strong>
                        {formatCurrency(
                          sale.total_amount,
                          currency
                        )}
                      </strong>

                      <span>
                        +{' '}
                        {formatCurrency(
                          sale.gross_profit,
                          currency
                        )}{' '}
                        kâr
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </section>
      </div>
    </main>
  )
}