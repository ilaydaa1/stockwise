import { type CSSProperties } from 'react'

import './dashboard.css'


type IconName =
  | 'box'
  | 'stock'
  | 'cart'
  | 'chart'
  | 'spark'
  | 'calendar'


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


// Illustrative data; these values do not come from the business API.
const demoSales = [
  5000,
  4900,
  5100,
  5800,
  10200,
  9800,
  9100,
  8600,
  11800,
  13700,
  8000,
  11200,
  7900,
  8200,
  10900,
]


const demoProfit = demoSales.map(
  (amount) => amount * 0.3
)


const totalSales = demoSales.reduce(
  (sum, amount) => sum + amount,
  0
)


const totalProfit = demoProfit.reduce(
  (sum, amount) => sum + amount,
  0
)


const demoProducts = [
  {
    name: 'Kablosuz Kulaklık Pro',
    sku: 'ELK-001',
    stock: 2,
    minimum: 10,
    status: 'Kritik',
    color: '#e8edf5',
    icon: 'box' as IconName,
  },
  {
    name: 'Filtre Kahve 250 g',
    sku: 'GDA-012',
    stock: 3,
    minimum: 12,
    status: 'Kritik',
    color: '#f3e9dd',
    icon: 'box' as IconName,
  },
  {
    name: 'Seramik Kupa',
    sku: 'EV-024',
    stock: 5,
    minimum: 15,
    status: 'Düşük',
    color: '#e6eef1',
    icon: 'box' as IconName,
  },
  {
    name: 'Telefon Kılıfı',
    sku: 'ELK-038',
    stock: 6,
    minimum: 20,
    status: 'Düşük',
    color: '#ece8f5',
    icon: 'box' as IconName,
  },
  {
    name: 'Defter A5 Çizgili',
    sku: 'KRT-007',
    stock: 7,
    minimum: 20,
    status: 'Düşük',
    color: '#e5efe8',
    icon: 'box' as IconName,
  },
]


const money = new Intl.NumberFormat(
  'tr-TR',
  {
    style: 'currency',
    currency: 'TRY',
    maximumFractionDigits: 0,
  }
)


function SalesChart() {
  const width = 640
  const height = 280

  const left = 52
  const right = 18
  const top = 20
  const bottom = 40

  const maximum = 15000


  const x = (index: number) =>
    left +
    (index / (demoSales.length - 1)) *
      (width - left - right)


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


  const area = [
    `${x(0)},${y(0)}`,
    points(demoSales),
    `${x(demoSales.length - 1)},${y(0)}`,
  ].join(' ')


  return (
    <svg
      className="sw-chart"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-labelledby="sw-chart-title sw-chart-description"
    >
      <title id="sw-chart-title">
        Örnek günlük satış ve brüt kâr grafiği
      </title>

      <desc id="sw-chart-description">
        1–15 Eylül arasındaki örnek satışlar mavi,
        brüt kâr yeşil çizgiyle gösterilir. Toplam
        satış {money.format(totalSales)}, toplam brüt
        kâr {money.format(totalProfit)}.
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


      {[0, 5000, 10000, 15000].map(
        (value) => (
          <g key={value}>
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
              {value === 0
                ? '0'
                : `${value / 1000} bin`}
            </text>
          </g>
        )
      )}


      <polygon
        points={area}
        fill="url(#sw-sales-fill)"
      />


      <polyline
        points={points(demoSales)}
        fill="none"
        stroke="#4285ff"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />


      <polyline
        points={points(demoProfit)}
        fill="none"
        stroke="#58ad88"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />


      {demoSales.map(
        (value, index) => (
          <circle
            key={`sales-${index}`}
            cx={x(index)}
            cy={y(value)}
            r="3"
            fill="white"
            stroke="#4285ff"
            strokeWidth="1.8"
          >
            <title>
              {index + 1} Eylül:{' '}
              {money.format(value)} satış
            </title>
          </circle>
        )
      )}


      {demoProfit.map(
        (value, index) => (
          <circle
            key={`profit-${index}`}
            cx={x(index)}
            cy={y(value)}
            r="2.6"
            fill="white"
            stroke="#58ad88"
            strokeWidth="1.6"
          />
        )
      )}


      {[0, 2, 4, 6, 8, 10, 12, 14].map(
        (index) => (
          <text
            key={index}
            x={x(index)}
            y={height - 12}
            textAnchor="middle"
            fill="#8591a6"
            fontSize="11"
          >
            {index + 1} Eyl
          </text>
        )
      )}
    </svg>
  )
}


export default function Dashboard() {
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
            Satışlarını, kârlılığını ve stok durumunu
            tek yerden takip et.
          </p>
        </div>


        <div className="sw-heading-actions">
          <div className="sw-date">
            <Icon
              name="calendar"
              size={17}
            />

            <span>
              1–15 Eylül 2026
            </span>
          </div>

          <button
            type="button"
            className="sw-primary-button"
            disabled
            title="Satış modülü eklendiğinde kullanıma açılacak."
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
        aria-label="Örnek işletme özeti"
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
              Seçili dönemdeki satış tutarı
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
              {money.format(totalProfit)}
            </strong>

            <p className="sw-positive">
              Brüt kâr marjı %30
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
              186
            </strong>

            <p>
              Seçili dönemde tamamlanan
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
              8
            </strong>

            <span className="sw-status is-critical">
              Kontrol gerekiyor
            </span>
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
                Günlük performans dağılımı
              </p>
            </div>

            <span className="sw-period">
              Günlük
            </span>
          </header>


          <div className="sw-legend">
            <span>
              <i className="is-sales" /> Satış (₺)
            </span>

            <span>
              <i className="is-profit" /> Brüt Kâr (₺)
            </span>
          </div>


          <div className="sw-chart-container">
            <SalesChart />
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

              <strong className="sw-positive">
                {money.format(totalProfit)}
              </strong>
            </div>

            <div>
              <span>
                Ort. Günlük Satış
              </span>

              <strong>
                {money.format(
                  totalSales /
                    demoSales.length
                )}
              </strong>
            </div>

            <div>
              <span>
                Ort. Günlük Brüt Kâr
              </span>

              <strong>
                {money.format(
                  totalProfit /
                    demoProfit.length
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
                Öncelik verilmesi gereken ürünler
              </p>
            </div>

            <span className="sw-count">
              İlk 5 ürün
            </span>
          </header>


          <div className="sw-table-container">
            <table className="sw-product-table">
              <caption className="sw-sr-only">
                Örnek ürünlerin mevcut stok ve minimum
                stok miktarları
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
                {demoProducts.map(
                  (product) => (
                    <tr key={product.sku}>
                      <td>
                        <div className="sw-product">
                          <span
                            className="sw-product-icon"
                            style={
                              {
                                '--product-color':
                                  product.color,
                              } as CSSProperties
                            }
                          >
                            <Icon
                              name={product.icon}
                              size={18}
                            />
                          </span>

                          <span>
                            <strong>
                              {product.name}
                            </strong>

                            <small>
                              {product.sku}
                            </small>
                          </span>
                        </div>
                      </td>

                      <td className="sw-stock-value">
                        {product.stock}
                      </td>

                      <td>
                        {product.minimum}
                      </td>

                      <td>
                        <span
                          className={`sw-status ${
                            product.status ===
                            'Kritik'
                              ? 'is-critical'
                              : 'is-low'
                          }`}
                        >
                          {product.status}
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

            Minimum stok seviyesinin altındaki ürünler
            gösterilir.
          </footer>
        </section>
      </div>


      <footer className="sw-demo-note">
        <Icon
          name="spark"
          size={16}
        />

        <p>
          Bu paneldeki tutarlar, grafik ve ürünler
          tasarım önizlemesi için örnektir. Örnek
          tutarlar TRY cinsindedir; işletmenin gerçek
          kayıtlarını göstermez.
        </p>
      </footer>
    </main>
  )
}