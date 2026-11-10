import {
  useEffect,
  useMemo,
  useState,
  type CSSProperties,
} from 'react'
import { useNavigate } from 'react-router-dom'

import { useBusiness } from '../contexts/BusinessContext'
import {
  getDashboardSummary,
  type DashboardSummary,
  type DailyPerformance,
} from '../lib/api'

import './dashboard.css'


type IconName =
  | 'box'
  | 'stock'
  | 'cart'
  | 'chart'
  | 'spark'
  | 'calendar'
  | 'refresh'


const iconPaths: Record<IconName, string> = {
  box:
    'm12 3 9 5v8l-9 5-9-5V8l9-5ZM3 8l9 5 9-5M12 13v8M7.5 5.5l9 5',

  stock:
    'M4 7h15m-4-4 4 4-4 4M20 17H5m4-4-4 4 4 4',

  cart:
    'M3 3h2l3 12h10l3-9H6M9 20h.01M18 20h.01',

  chart:
    'M4 20V10h4v10M10 20V4h4v16M16 20v-7h4v7',

  spark:
    'm12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z',

  calendar:
    'M4 5h16v16H4V5ZM8 3v4M16 3v4M4 10h16',

  refresh:
    'M20 6v5h-5M4 18v-5h5M18.5 9A7 7 0 0 0 6.3 6.3L4 9M5.5 15A7 7 0 0 0 17.7 17.7L20 15',
}


function Icon({
  name,
  size = 20,
}: {
  name: IconName
  size?: number
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={iconPaths[name]} />
    </svg>
  )
}


function formatDateLabel(dateString: string) {
  const date = new Date(
    `${dateString}T00:00:00`
  )

  return new Intl.DateTimeFormat(
    'tr-TR',
    {
      day: 'numeric',
      month: 'short',
    }
  ).format(date)
}


function formatLongDate(dateString: string) {
  const date = new Date(
    `${dateString}T00:00:00`
  )

  return new Intl.DateTimeFormat(
    'tr-TR',
    {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    }
  ).format(date)
}


function SalesChart({
  data,
  money,
}: {
  data: DailyPerformance[]
  money: Intl.NumberFormat
}) {
  const width = 640
  const height = 280

  const left = 58
  const right = 18
  const top = 20
  const bottom = 42

  const salesValues = data.map(
    (item) => Number(item.sales)
  )

  const profitValues = data.map(
    (item) => Number(item.gross_profit)
  )

  const highestValue = Math.max(
    ...salesValues,
    ...profitValues,
    1
  )

  const maximum =
    highestValue <= 100
      ? Math.ceil(highestValue / 10) * 10 ||
        10
      : Math.ceil(highestValue / 100) * 100

  const x = (index: number) => {
    if (data.length <= 1) {
      return left
    }

    return (
      left +
      (index / (data.length - 1)) *
        (width - left - right)
    )
  }

  const y = (amount: number) =>
    top +
    (1 - amount / maximum) *
      (height - top - bottom)

  const points = (values: number[]) =>
    values
      .map(
        (value, index) =>
          `${x(index)},${y(value)}`
      )
      .join(' ')

  const salesPoints = points(salesValues)
  const profitPoints = points(profitValues)

  const area =
    data.length > 0
      ? [
          `${x(0)},${y(0)}`,
          salesPoints,
          `${x(data.length - 1)},${y(0)}`,
        ].join(' ')
      : ''

  const gridValues = [
    0,
    maximum / 3,
    (maximum / 3) * 2,
    maximum,
  ]

  const visibleDateIndexes =
    data.length <= 8
      ? data.map((_, index) => index)
      : [0, 2, 4, 6, 8, 10, 12, 14].filter(
          (index) => index < data.length
        )

  const formatAxisValue = (
    value: number
  ) => {
    if (value >= 1000) {
      const thousands = value / 1000

      return Number.isInteger(thousands)
        ? `${thousands} bin`
        : `${thousands.toFixed(1)} bin`
    }

    return Math.round(value).toString()
  }

  return (
    <svg
      className="sw-chart"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-labelledby="sw-chart-title sw-chart-description"
    >
      <title id="sw-chart-title">
        Günlük satış ve brüt kâr grafiği
      </title>

      <desc id="sw-chart-description">
        Son 15 günlük gerçek satış ve brüt
        kâr performansı.
      </desc>

      <defs>
        <linearGradient
          id="sw-sales-fill"
          x1="0"
          y1="0"
          x2="0"
          y2="1"
        >
          <stop
            offset="0%"
            stopColor="#4285ff"
            stopOpacity="0.12"
          />

          <stop
            offset="100%"
            stopColor="#4285ff"
            stopOpacity="0"
          />
        </linearGradient>
      </defs>

      {gridValues.map(
        (value, index) => (
          <g key={index}>
            <line
              x1={left}
              y1={y(value)}
              x2={width - right}
              y2={y(value)}
              stroke="#e9eef5"
              strokeDasharray="4 5"
            />

            <text
              x={left - 12}
              y={y(value) + 4}
              textAnchor="end"
              fill="#8591a6"
              fontSize="11"
            >
              {formatAxisValue(value)}
            </text>
          </g>
        )
      )}

      {area && (
        <polygon
          points={area}
          fill="url(#sw-sales-fill)"
        />
      )}

      {data.length > 0 && (
        <>
          <polyline
            points={salesPoints}
            fill="none"
            stroke="#4285ff"
            strokeWidth="2.5"
            strokeLinejoin="round"
          />

          <polyline
            points={profitPoints}
            fill="none"
            stroke="#58ad88"
            strokeWidth="2.5"
            strokeLinejoin="round"
          />
        </>
      )}

      {data.map((item, index) => (
        <circle
          key={`sales-${item.date}`}
          cx={x(index)}
          cy={y(Number(item.sales))}
          r="3"
          fill="white"
          stroke="#4285ff"
          strokeWidth="1.8"
        >
          <title>
            {formatDateLabel(item.date)}:{' '}
            {money.format(
              Number(item.sales)
            )}{' '}
            satış
          </title>
        </circle>
      ))}

      {data.map((item, index) => (
        <circle
          key={`profit-${item.date}`}
          cx={x(index)}
          cy={y(
            Number(item.gross_profit)
          )}
          r="2.6"
          fill="white"
          stroke="#58ad88"
          strokeWidth="1.6"
        >
          <title>
            {formatDateLabel(item.date)}:{' '}
            {money.format(
              Number(item.gross_profit)
            )}{' '}
            brüt kâr
          </title>
        </circle>
      ))}

      {visibleDateIndexes.map(
        (index) => (
          <text
            key={data[index].date}
            x={x(index)}
            y={height - 12}
            textAnchor="middle"
            fill="#8591a6"
            fontSize="11"
          >
            {formatDateLabel(
              data[index].date
            )}
          </text>
        )
      )}
    </svg>
  )
}


export default function Dashboard() {
  const navigate = useNavigate()

  const { business } = useBusiness()

  const [summary, setSummary] =
    useState<DashboardSummary | null>(
      null
    )

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState<string | null>(null)


  const currency =
    business?.currency || 'TRY'


  const money = useMemo(
    () =>
      new Intl.NumberFormat(
        'tr-TR',
        {
          style: 'currency',
          currency,
          maximumFractionDigits: 2,
        }
      ),
    [currency]
  )


  const loadDashboard = async () => {
    setLoading(true)
    setError(null)

    const result =
      await getDashboardSummary()

    if (!result.data) {
      setError(
        result.error ||
          'Dashboard verileri yüklenemedi.'
      )

      setLoading(false)
      return
    }

    setSummary(result.data)
    setLoading(false)
  }


  useEffect(() => {
    loadDashboard()
  }, [])


  const totalSales = Number(
    summary?.total_sales || 0
  )

  const grossProfit = Number(
    summary?.gross_profit || 0
  )

  const grossProfitMargin = Number(
    summary?.gross_profit_margin || 0
  )

  const saleCount =
    summary?.sale_count || 0

  const criticalStockCount =
    summary?.critical_stock_count || 0

  const dailyPerformance =
    summary?.daily_performance || []

  const activeDays =
    dailyPerformance.filter(
      (item) => Number(item.sales) > 0
    ).length

  const averageDailySales =
    activeDays > 0
      ? totalSales / activeDays
      : 0

  const averageDailyProfit =
    activeDays > 0
      ? grossProfit / activeDays
      : 0


  const periodText =
    dailyPerformance.length > 0
      ? `${formatLongDate(
          dailyPerformance[0].date
        )} – ${formatLongDate(
          dailyPerformance[
            dailyPerformance.length - 1
          ].date
        )}`
      : 'Son 15 gün'


  if (loading) {
    return (
      <main
        id="sw-main"
        className="sw-main"
      >
        <section className="sw-page-heading">
          <div>
            <p className="sw-eyebrow">
              İŞLETMENİN NABZI
            </p>

            <h1>
              İşletmene genel bakış
            </h1>

            <p className="sw-subtitle">
              Dashboard verileri
              yükleniyor...
            </p>
          </div>
        </section>

        <section
          className="sw-panel"
          style={statePanelStyle}
        >
          Veriler yükleniyor...
        </section>
      </main>
    )
  }


  if (error || !summary) {
    return (
      <main
        id="sw-main"
        className="sw-main"
      >
        <section className="sw-page-heading">
          <div>
            <p className="sw-eyebrow">
              İŞLETMENİN NABZI
            </p>

            <h1>
              İşletmene genel bakış
            </h1>

            <p className="sw-subtitle">
              Satışlarını, kârlılığını ve
              stok durumunu tek yerden
              takip et.
            </p>
          </div>
        </section>

        <section
          className="sw-panel"
          style={errorPanelStyle}
        >
          <strong>
            Dashboard verileri
            yüklenemedi
          </strong>

          <span style={errorTextStyle}>
            {error}
          </span>

          <button
            type="button"
            className="sw-primary-button"
            onClick={loadDashboard}
          >
            <Icon
              name="refresh"
              size={17}
            />

            Tekrar Dene
          </button>
        </section>
      </main>
    )
  }


  return (
    <main
      id="sw-main"
      className="sw-main"
    >
      <section className="sw-page-heading">
        <div>
          <p className="sw-eyebrow">
            İŞLETMENİN NABZI
          </p>

          <h1>
            İşletmene genel bakış
          </h1>

          <p className="sw-subtitle">
            Satışlarını, kârlılığını ve
            stok durumunu tek yerden
            takip et.
          </p>
        </div>


        <div className="sw-heading-actions">
          <div className="sw-date">
            <Icon
              name="calendar"
              size={17}
            />

            <span>
              {periodText}
            </span>
          </div>

          <button
            type="button"
            className="sw-primary-button"
            onClick={() =>
              navigate('/app/sales')
            }
          >
            <span aria-hidden="true">
              +
            </span>

            Yeni Satış
          </button>
        </div>
      </section>


      <section
        className="sw-stats"
        aria-label="İşletme özeti"
      >
        <article className="sw-stat-card">
          <span className="sw-stat-icon is-blue">
            <Icon name="chart" />
          </span>

          <div>
            <h2>
              Toplam Satış
            </h2>

            <strong>
              {money.format(totalSales)}
            </strong>

            <p>
              Son 15 gündeki satış tutarı
              {Number(summary?.refund_total ?? 0) > 0 &&
                ` · ${money.format(
                  Number(summary?.refund_total ?? 0)
                )} iade düşülünce ${money.format(
                  Number(summary?.net_sales ?? 0)
                )}`}
            </p>
          </div>
        </article>


        <article className="sw-stat-card">
          <span className="sw-stat-icon is-green">
            <Icon name="stock" />
          </span>

          <div>
            <h2>
              Brüt Kâr
            </h2>

            <strong>
              {money.format(grossProfit)}
            </strong>

            <p
              className={
                grossProfit >= 0
                  ? 'sw-positive'
                  : undefined
              }
            >
              Brüt kâr marjı %
              {grossProfitMargin.toLocaleString(
                'tr-TR',
                {
                  maximumFractionDigits: 2,
                }
              )}
            </p>
          </div>
        </article>


        <article className="sw-stat-card">
          <span className="sw-stat-icon is-purple">
            <Icon name="cart" />
          </span>

          <div>
            <h2>
              Satış Sayısı
            </h2>

            <strong>
              {saleCount}
            </strong>

            <p>
              Son 15 günde tamamlanan
            </p>
          </div>
        </article>


        <article className="sw-stat-card">
          <span className="sw-stat-icon is-orange">
            <Icon name="box" />
          </span>

          <div>
            <h2>
              Kritik Stoktaki Ürün
            </h2>

            <strong>
              {criticalStockCount}
            </strong>

            {criticalStockCount > 0 ? (
              <span className="sw-status is-critical">
                Kontrol gerekiyor
              </span>
            ) : (
              <span
                className="sw-status"
                style={healthyStatusStyle}
              >
                Stoklar yeterli
              </span>
            )}
          </div>
        </article>
      </section>


      <div className="sw-content-grid">
        <section className="sw-panel">
          <header className="sw-panel-heading">
            <div>
              <h2>
                Satış ve Brüt Kâr
              </h2>

              <p>
                Son 15 günlük performans
              </p>
            </div>

            <span className="sw-period">
              Günlük
            </span>
          </header>


          <div className="sw-legend">
            <span>
              <i className="is-sales" />{' '}
              Satış ({currency})
            </span>

            <span>
              <i className="is-profit" />{' '}
              Brüt Kâr ({currency})
            </span>
          </div>


          <div className="sw-chart-container">
            <SalesChart
              data={dailyPerformance}
              money={money}
            />
          </div>


          <div className="sw-chart-summary">
            <div>
              <span>
                Toplam Satış
              </span>

              <strong>
                {money.format(totalSales)}
              </strong>
            </div>

            <div>
              <span>
                Toplam Brüt Kâr
              </span>

              <strong
                className={
                  grossProfit >= 0
                    ? 'sw-positive'
                    : undefined
                }
              >
                {money.format(
                  grossProfit
                )}
              </strong>
            </div>

            <div>
              <span>
                Ort. Aktif Gün Satışı
              </span>

              <strong>
                {money.format(
                  averageDailySales
                )}
              </strong>
            </div>

            <div>
              <span>
                Ort. Aktif Gün Brüt Kârı
              </span>

              <strong>
                {money.format(
                  averageDailyProfit
                )}
              </strong>
            </div>
          </div>
        </section>


        <section className="sw-panel">
          <header className="sw-panel-heading">
            <div>
              <h2>
                Kritik stoktaki ürünler
              </h2>

              <p>
                Öncelik verilmesi gereken
                ürünler
              </p>
            </div>

            <span className="sw-count">
              {criticalStockCount > 5
                ? `İlk 5 / ${criticalStockCount}`
                : `${criticalStockCount} ürün`}
            </span>
          </header>


          {summary.critical_products
            .length > 0 ? (
            <>
              <div className="sw-table-container">
                <table className="sw-product-table">
                  <caption className="sw-sr-only">
                    Minimum stok seviyesine
                    ulaşmış veya altına düşmüş
                    ürünler
                  </caption>

                  <thead>
                    <tr>
                      <th scope="col">
                        Ürün
                      </th>

                      <th scope="col">
                        Stok
                      </th>

                      <th scope="col">
                        Min.
                      </th>

                      <th scope="col">
                        Durum
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {summary.critical_products.map(
                      (product) => (
                        <tr key={product.id}>
                          <td>
                            <div className="sw-product">
                              <span
                                className="sw-product-icon"
                                style={
                                  {
                                    '--product-color':
                                      '#e8edf5',
                                  } as CSSProperties
                                }
                              >
                                <Icon
                                  name="box"
                                  size={18}
                                />
                              </span>

                              <span>
                                <strong>
                                  {
                                    product.name
                                  }
                                </strong>

                                <small>
                                  {
                                    product.sku
                                  }
                                </small>
                              </span>
                            </div>
                          </td>

                          <td className="sw-stock-value">
                            {
                              product.stock_quantity
                            }
                          </td>

                          <td>
                            {
                              product.minimum_stock
                            }
                          </td>

                          <td>
                            <span className="sw-status is-critical">
                              {product.stock_quantity ===
                              0
                                ? 'Stok Tükendi'
                                : product.stock_quantity <
                                    product.minimum_stock
                                  ? 'Kritik'
                                  : 'Minimum'}
                            </span>
                          </td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>

              <footer className="sw-stock-note">
                <span aria-hidden="true">
                  ⓘ
                </span>

                Minimum stok seviyesine
                ulaşan veya altına düşen
                ürünler gösterilir.
              </footer>
            </>
          ) : (
            <div style={emptyStockStyle}>
              <span style={emptyStockIconStyle}>
                <Icon
                  name="box"
                  size={25}
                />
              </span>

              <strong>
                Kritik stok bulunmuyor
              </strong>

              <p>
                Tüm aktif ürünlerin stok
                seviyesi belirlenen minimum
                seviyenin üzerinde.
              </p>
            </div>
          )}
        </section>
      </div>
    </main>
  )
}


const statePanelStyle: CSSProperties = {
  minHeight: '300px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  color: '#738096',
  fontSize: '15px',
}


const errorPanelStyle: CSSProperties = {
  minHeight: '300px',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '14px',
  textAlign: 'center',
  padding: '30px',
}


const errorTextStyle: CSSProperties = {
  color: '#738096',
}


const healthyStatusStyle: CSSProperties = {
  color: '#18785b',
  background: '#eaf8f2',
}


const emptyStockStyle: CSSProperties = {
  minHeight: '320px',
  padding: '35px 24px',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  textAlign: 'center',
  color: '#738096',
}


const emptyStockIconStyle: CSSProperties = {
  width: '54px',
  height: '54px',
  borderRadius: '13px',
  background: '#eef4ff',
  color: '#4285ff',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  marginBottom: '14px',
}