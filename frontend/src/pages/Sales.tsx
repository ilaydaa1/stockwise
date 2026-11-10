import {
  useEffect,
  useMemo,
  useState,
  type CSSProperties,
} from 'react'

import {
  createSale,
  getProducts,
  type Product,
} from '../lib/api'

import './dashboard.css'


type IconName =
  | 'cart'
  | 'search'
  | 'plus'
  | 'minus'
  | 'trash'
  | 'box'
  | 'refresh'
  | 'check'


const iconPaths: Record<IconName, string> = {
  cart:
    'M3 3h2l3 12h10l3-9H6M9 20h.01M18 20h.01',

  search:
    'm21 21-4.35-4.35M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z',

  plus:
    'M12 5v14M5 12h14',

  minus:
    'M5 12h14',

  trash:
    'M4 7h16M9 7V4h6v3M7 7l1 13h8l1-13M10 11v5M14 11v5',

  box:
    'm12 3 9 5v8l-9 5-9-5V8l9-5ZM3 8l9 5 9-5M12 13v8',

  refresh:
    'M20 6v5h-5M4 18v-5h5M18.5 9A7 7 0 0 0 6.3 6.3L4 9M5.5 15A7 7 0 0 0 17.7 17.7L20 15',

  check:
    'm5 12 4 4L19 6',
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


interface CartItem {
  product: Product
  quantity: number
}


function formatMoney(value: string | number) {
  const amount = Number(value)

  if (Number.isNaN(amount)) {
    return '₺0,00'
  }

  return new Intl.NumberFormat('tr-TR', {
    style: 'currency',
    currency: 'TRY',
  }).format(amount)
}


export default function Sales() {
  const [products, setProducts] =
    useState<Product[]>([])

  const [cart, setCart] =
    useState<CartItem[]>([])

  const [search, setSearch] =
    useState('')

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState<string | null>(null)

  const [saleError, setSaleError] =
    useState<string | null>(null)

  const [successMessage, setSuccessMessage] =
    useState<string | null>(null)

  const [saving, setSaving] =
    useState(false)


  const loadProducts = async () => {
    setLoading(true)
    setError(null)

    const result = await getProducts()

    if (!result.data) {
      setError(
        result.error ||
          'Ürünler yüklenirken bir hata oluştu.'
      )

      setLoading(false)
      return
    }

    setProducts(
      result.data.filter(
        (product) => product.is_active
      )
    )

    setLoading(false)
  }


  useEffect(() => {
    loadProducts()
  }, [])


  const normalizedSearch =
    search
      .trim()
      .toLocaleLowerCase('tr-TR')


  const filteredProducts =
    useMemo(() => {
      if (!normalizedSearch) {
        return products
      }

      return products.filter((product) => {
        const name =
          product.name.toLocaleLowerCase(
            'tr-TR'
          )

        const sku =
          product.sku.toLocaleLowerCase(
            'tr-TR'
          )

        return (
          name.includes(normalizedSearch) ||
          sku.includes(normalizedSearch)
        )
      })
    }, [
      products,
      normalizedSearch,
    ])


  const cartQuantity = (productId: string) => {
    return (
      cart.find(
        (item) =>
          item.product.id === productId
      )?.quantity || 0
    )
  }


  const addToCart = (product: Product) => {
    setSaleError(null)
    setSuccessMessage(null)

    if (product.stock_quantity <= 0) {
      return
    }

    setCart((current) => {
      const existing =
        current.find(
          (item) =>
            item.product.id === product.id
        )

      if (existing) {
        if (
          existing.quantity >=
          product.stock_quantity
        ) {
          return current
        }

        return current.map((item) =>
          item.product.id === product.id
            ? {
                ...item,
                quantity:
                  item.quantity + 1,
              }
            : item
        )
      }

      return [
        ...current,
        {
          product,
          quantity: 1,
        },
      ]
    })
  }


  const increaseQuantity = (
    productId: string
  ) => {
    setSaleError(null)

    setCart((current) =>
      current.map((item) => {
        if (
          item.product.id !== productId
        ) {
          return item
        }

        if (
          item.quantity >=
          item.product.stock_quantity
        ) {
          return item
        }

        return {
          ...item,
          quantity: item.quantity + 1,
        }
      })
    )
  }


  const decreaseQuantity = (
    productId: string
  ) => {
    setSaleError(null)

    setCart((current) =>
      current
        .map((item) => {
          if (
            item.product.id !== productId
          ) {
            return item
          }

          return {
            ...item,
            quantity: item.quantity - 1,
          }
        })
        .filter(
          (item) => item.quantity > 0
        )
    )
  }


  const removeFromCart = (
    productId: string
  ) => {
    setSaleError(null)

    setCart((current) =>
      current.filter(
        (item) =>
          item.product.id !== productId
      )
    )
  }


  const total = useMemo(() => {
    return cart.reduce(
      (sum, item) =>
        sum +
        Number(item.product.sale_price) *
          item.quantity,
      0
    )
  }, [cart])


  const totalUnits = useMemo(() => {
    return cart.reduce(
      (sum, item) =>
        sum + item.quantity,
      0
    )
  }, [cart])


  const handleCompleteSale = async () => {
    if (
      cart.length === 0 ||
      saving
    ) {
      return
    }

    setSaving(true)
    setSaleError(null)
    setSuccessMessage(null)

    const result = await createSale({
      items: cart.map((item) => ({
        product_id: item.product.id,
        quantity: item.quantity,
      })),
    })

    if (!result.data) {
      const message =
        result.error ===
        'INSUFFICIENT_STOCK'
          ? 'Ürünlerden birinde yeterli stok bulunmuyor. Stokları yenileyip tekrar deneyin.'
          : result.error ===
              'PRODUCT_NOT_FOUND'
            ? 'Sepetteki ürünlerden biri artık kullanılamıyor.'
            : result.error ===
                'DUPLICATE_PRODUCT'
              ? 'Aynı ürün satışa birden fazla kez eklenemez.'
              : result.error ||
                'Satış tamamlanamadı.'

      setSaleError(message)
      setSaving(false)
      return
    }

    const completedSale =
      result.data

    setCart([])

    setSuccessMessage(
      `Satış başarıyla tamamlandı. Toplam: ${formatMoney(
        completedSale.total_amount
      )}`
    )

    const productsResult =
      await getProducts()

    if (productsResult.data) {
      setProducts(
        productsResult.data.filter(
          (product) =>
            product.is_active
        )
      )
    }

    setSaving(false)
  }


  return (
    <main
      id="sw-main"
      className="sw-main"
    >
      <section className="sw-page-heading">
        <div>
          <p className="sw-eyebrow">
            SATIŞ
          </p>

          <h1>
            Satış Yap
          </h1>

          <p className="sw-subtitle">
            Ürünleri sepete ekle,
            miktarlarını belirle ve satışı
            tek adımda tamamla.
          </p>
        </div>
      </section>


      {successMessage && (
        <div
          role="status"
          style={successStyle}
        >
          <span style={successIconStyle}>
            <Icon
              name="check"
              size={19}
            />
          </span>

          <span>
            {successMessage}
          </span>
        </div>
      )}


      <div style={salesGridStyle}>
        <section className="sw-panel">
          <header className="sw-panel-heading">
            <div>
              <h2>
                Ürünler
              </h2>

              <p>
                Satışa eklemek istediğin
                ürünü seç
              </p>
            </div>

            {!loading && !error && (
              <span className="sw-count">
                {products.length} ürün
              </span>
            )}
          </header>


          {!loading &&
            !error &&
            products.length > 0 && (
              <div style={productToolbarStyle}>
                <div style={searchWrapperStyle}>
                  <span style={searchIconStyle}>
                    <Icon
                      name="search"
                      size={18}
                    />
                  </span>

                  <input
                    type="search"
                    value={search}
                    onChange={(event) =>
                      setSearch(
                        event.target.value
                      )
                    }
                    placeholder="Ürün adı veya SKU ara..."
                    aria-label="Satış ürünü ara"
                    style={searchInputStyle}
                  />
                </div>

                <button
                  type="button"
                  onClick={loadProducts}
                  style={refreshButtonStyle}
                  title="Ürünleri yenile"
                >
                  <Icon
                    name="refresh"
                    size={17}
                  />

                  Yenile
                </button>
              </div>
            )}


          {loading && (
            <div style={stateStyle}>
              Ürünler yükleniyor...
            </div>
          )}


          {!loading && error && (
            <div style={errorStateStyle}>
              <strong>
                Ürünler yüklenemedi
              </strong>

              <span style={mutedTextStyle}>
                {error}
              </span>

              <button
                type="button"
                className="sw-primary-button"
                onClick={loadProducts}
              >
                <Icon
                  name="refresh"
                  size={17}
                />

                Tekrar Dene
              </button>
            </div>
          )}


          {!loading &&
            !error &&
            products.length === 0 && (
              <div style={emptyStateStyle}>
                <span style={emptyIconStyle}>
                  <Icon
                    name="box"
                    size={27}
                  />
                </span>

                <h2 style={emptyTitleStyle}>
                  Satış yapılabilecek ürün yok
                </h2>

                <p style={emptyTextStyle}>
                  Satış yapabilmek için önce
                  işletmene aktif bir ürün
                  eklemelisin.
                </p>
              </div>
            )}


          {!loading &&
            !error &&
            products.length > 0 && (
              <>
                <div style={productListStyle}>
                  {filteredProducts.map(
                    (product) => {
                      const quantityInCart =
                        cartQuantity(
                          product.id
                        )

                      const outOfStock =
                        product.stock_quantity <= 0

                      const reachedLimit =
                        quantityInCart >=
                        product.stock_quantity

                      return (
                        <article
                          key={product.id}
                          style={productCardStyle}
                        >
                          <div
                            style={
                              productInfoStyle
                            }
                          >
                            <span
                              style={
                                productIconStyle
                              }
                            >
                              <Icon
                                name="box"
                                size={20}
                              />
                            </span>

                            <div
                              style={
                                productTextStyle
                              }
                            >
                              <strong
                                style={
                                  productNameStyle
                                }
                              >
                                {product.name}
                              </strong>

                              <span
                                style={
                                  productSkuStyle
                                }
                              >
                                SKU: {product.sku}
                              </span>
                            </div>
                          </div>


                          <div
                            style={
                              productDetailsStyle
                            }
                          >
                            <span
                              style={
                                productStockStyle
                              }
                            >
                              Stok:{' '}

                              <strong>
                                {
                                  product.stock_quantity
                                }
                              </strong>
                            </span>

                            <strong
                              style={
                                productPriceStyle
                              }
                            >
                              {formatMoney(
                                product.sale_price
                              )}
                            </strong>

                            <button
                              type="button"
                              onClick={() =>
                                addToCart(
                                  product
                                )
                              }
                              disabled={
                                outOfStock ||
                                reachedLimit
                              }
                              style={{
                                ...addButtonStyle,
                                ...(outOfStock ||
                                reachedLimit
                                  ? disabledButtonStyle
                                  : {}),
                              }}
                            >
                              <Icon
                                name="plus"
                                size={16}
                              />

                              {outOfStock
                                ? 'Stok Yok'
                                : reachedLimit
                                  ? 'Stok Sınırı'
                                  : quantityInCart >
                                      0
                                    ? 'Bir Tane Daha'
                                    : 'Sepete Ekle'}
                            </button>
                          </div>
                        </article>
                      )
                    }
                  )}
                </div>


                {filteredProducts.length ===
                  0 && (
                  <div style={noResultStyle}>
                    Aramana uygun ürün
                    bulunamadı.
                  </div>
                )}
              </>
            )}
        </section>


        <section
          className="sw-panel"
          style={cartPanelStyle}
        >
          <header className="sw-panel-heading">
            <div>
              <h2>
                Sepet
              </h2>

              <p>
                Satış özeti
              </p>
            </div>

            <span className="sw-count">
              {totalUnits} adet
            </span>
          </header>


          {cart.length === 0 ? (
            <div style={cartEmptyStyle}>
              <span style={cartEmptyIconStyle}>
                <Icon
                  name="cart"
                  size={28}
                />
              </span>

              <strong>
                Sepetin boş
              </strong>

              <p>
                Satışa başlamak için
                soldaki ürünlerden sepete
                ekle.
              </p>
            </div>
          ) : (
            <>
              <div style={cartItemsStyle}>
                {cart.map((item) => (
                  <div
                    key={item.product.id}
                    style={cartItemStyle}
                  >
                    <div
                      style={cartItemHeaderStyle}
                    >
                      <div>
                        <strong
                          style={
                            cartProductNameStyle
                          }
                        >
                          {item.product.name}
                        </strong>

                        <span
                          style={
                            cartProductSkuStyle
                          }
                        >
                          {item.product.sku}
                        </span>
                      </div>

                      <button
                        type="button"
                        onClick={() =>
                          removeFromCart(
                            item.product.id
                          )
                        }
                        disabled={saving}
                        aria-label={`${item.product.name} ürününü sepetten kaldır`}
                        title="Sepetten kaldır"
                        style={trashButtonStyle}
                      >
                        <Icon
                          name="trash"
                          size={17}
                        />
                      </button>
                    </div>


                    <div
                      style={cartItemBottomStyle}
                    >
                      <div
                        style={
                          quantityControlStyle
                        }
                      >
                        <button
                          type="button"
                          onClick={() =>
                            decreaseQuantity(
                              item.product.id
                            )
                          }
                          disabled={saving}
                          aria-label="Miktarı azalt"
                          style={
                            quantityButtonStyle
                          }
                        >
                          <Icon
                            name="minus"
                            size={15}
                          />
                        </button>

                        <strong
                          style={
                            quantityValueStyle
                          }
                        >
                          {item.quantity}
                        </strong>

                        <button
                          type="button"
                          onClick={() =>
                            increaseQuantity(
                              item.product.id
                            )
                          }
                          disabled={
                            saving ||
                            item.quantity >=
                              item.product
                                .stock_quantity
                          }
                          aria-label="Miktarı artır"
                          style={{
                            ...quantityButtonStyle,
                            ...(item.quantity >=
                            item.product
                              .stock_quantity
                              ? disabledQuantityStyle
                              : {}),
                          }}
                        >
                          <Icon
                            name="plus"
                            size={15}
                          />
                        </button>
                      </div>

                      <div
                        style={
                          cartPriceAreaStyle
                        }
                      >
                        <span>
                          {item.quantity} ×{' '}
                          {formatMoney(
                            item.product
                              .sale_price
                          )}
                        </span>

                        <strong>
                          {formatMoney(
                            Number(
                              item.product
                                .sale_price
                            ) *
                              item.quantity
                          )}
                        </strong>
                      </div>
                    </div>


                    <span
                      style={stockHintStyle}
                    >
                      Mevcut stok:{' '}
                      {
                        item.product
                          .stock_quantity
                      }
                    </span>
                  </div>
                ))}
              </div>


              <div style={cartSummaryStyle}>
                <div
                  style={summaryRowStyle}
                >
                  <span>
                    Ürün çeşidi
                  </span>

                  <strong>
                    {cart.length}
                  </strong>
                </div>

                <div
                  style={summaryRowStyle}
                >
                  <span>
                    Toplam adet
                  </span>

                  <strong>
                    {totalUnits}
                  </strong>
                </div>

                <div
                  style={totalRowStyle}
                >
                  <span>
                    Toplam
                  </span>

                  <strong>
                    {formatMoney(total)}
                  </strong>
                </div>
              </div>
            </>
          )}


          {saleError && (
            <div
              role="alert"
              style={saleErrorStyle}
            >
              {saleError}
            </div>
          )}


          <div style={checkoutAreaStyle}>
            <button
              type="button"
              className="sw-primary-button"
              onClick={handleCompleteSale}
              disabled={
                cart.length === 0 ||
                saving
              }
              style={{
                width: '100%',
                justifyContent: 'center',
                minHeight: '46px',
              }}
            >
              <Icon
                name="cart"
                size={18}
              />

              {saving
                ? 'Satış Tamamlanıyor...'
                : `Satışı Tamamla · ${formatMoney(
                    total
                  )}`}
            </button>
          </div>
        </section>
      </div>
    </main>
  )
}


const salesGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns:
    'minmax(0, 1.55fr) minmax(340px, 0.75fr)',
  gap: '20px',
  alignItems: 'start',
}


const productToolbarStyle: CSSProperties = {
  padding: '0 20px 20px',
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
}


const searchWrapperStyle: CSSProperties = {
  position: 'relative',
  flex: 1,
}


const searchIconStyle: CSSProperties = {
  position: 'absolute',
  left: '14px',
  top: '50%',
  transform: 'translateY(-50%)',
  display: 'flex',
  color: '#8591a6',
  pointerEvents: 'none',
}


const searchInputStyle: CSSProperties = {
  width: '100%',
  height: '44px',
  boxSizing: 'border-box',
  border: '1px solid #dce2ea',
  borderRadius: '9px',
  padding: '0 14px 0 42px',
  background: '#fff',
  color: '#172641',
  font: 'inherit',
  fontSize: '15px',
  outline: 'none',
}


const refreshButtonStyle: CSSProperties = {
  height: '44px',
  padding: '0 14px',
  border: '1px solid #dce2ea',
  borderRadius: '9px',
  background: '#fff',
  color: '#42516a',
  fontWeight: 600,
  fontSize: '14px',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  gap: '7px',
}


const productListStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  borderTop: '1px solid #edf0f4',
}


const productCardStyle: CSSProperties = {
  minHeight: '88px',
  padding: '16px 20px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: '18px',
  borderBottom: '1px solid #edf0f4',
}


const productInfoStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '13px',
  minWidth: 0,
}


const productIconStyle: CSSProperties = {
  width: '42px',
  height: '42px',
  flex: '0 0 42px',
  borderRadius: '10px',
  background: '#eef4ff',
  color: '#4285ff',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
}


const productTextStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '4px',
  minWidth: 0,
}


const productNameStyle: CSSProperties = {
  color: '#172641',
  fontSize: '16px',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
}


const productSkuStyle: CSSProperties = {
  color: '#7b8799',
  fontSize: '13px',
}


const productDetailsStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'flex-end',
  gap: '18px',
  flexWrap: 'wrap',
}


const productStockStyle: CSSProperties = {
  color: '#647188',
  fontSize: '14px',
  whiteSpace: 'nowrap',
}


const productPriceStyle: CSSProperties = {
  minWidth: '90px',
  color: '#172641',
  fontSize: '16px',
  textAlign: 'right',
  whiteSpace: 'nowrap',
}


const addButtonStyle: CSSProperties = {
  minWidth: '125px',
  height: '38px',
  border: '1px solid #d8e4ff',
  borderRadius: '8px',
  padding: '0 12px',
  background: '#eef4ff',
  color: '#2f6fe4',
  fontWeight: 600,
  fontSize: '13px',
  cursor: 'pointer',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '6px',
}


const disabledButtonStyle: CSSProperties = {
  opacity: 0.55,
  cursor: 'not-allowed',
}


const cartPanelStyle: CSSProperties = {
  position: 'sticky',
  top: '84px',
}


const cartEmptyStyle: CSSProperties = {
  minHeight: '260px',
  padding: '32px 24px',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  textAlign: 'center',
  color: '#738096',
}


const cartEmptyIconStyle: CSSProperties = {
  width: '58px',
  height: '58px',
  borderRadius: '14px',
  background: '#f3f6fa',
  color: '#718096',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  marginBottom: '14px',
}


const cartItemsStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
}


const cartItemStyle: CSSProperties = {
  padding: '16px 20px',
  borderBottom: '1px solid #edf0f4',
}


const cartItemHeaderStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  justifyContent: 'space-between',
  gap: '12px',
  marginBottom: '13px',
}


const cartProductNameStyle: CSSProperties = {
  display: 'block',
  color: '#172641',
  fontSize: '15px',
  marginBottom: '3px',
}


const cartProductSkuStyle: CSSProperties = {
  color: '#8591a6',
  fontSize: '12px',
}


const trashButtonStyle: CSSProperties = {
  width: '32px',
  height: '32px',
  flex: '0 0 32px',
  border: 'none',
  borderRadius: '7px',
  background: '#fff2f0',
  color: '#c44747',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
}


const cartItemBottomStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: '14px',
}


const quantityControlStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  border: '1px solid #dce2ea',
  borderRadius: '8px',
  overflow: 'hidden',
  background: '#fff',
}


const quantityButtonStyle: CSSProperties = {
  width: '34px',
  height: '34px',
  border: 'none',
  background: '#f7f9fb',
  color: '#42516a',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
}


const disabledQuantityStyle: CSSProperties = {
  opacity: 0.45,
  cursor: 'not-allowed',
}


const quantityValueStyle: CSSProperties = {
  minWidth: '38px',
  textAlign: 'center',
  color: '#172641',
  fontSize: '14px',
}


const cartPriceAreaStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'flex-end',
  gap: '2px',
  color: '#7b8799',
  fontSize: '12px',
}


const stockHintStyle: CSSProperties = {
  display: 'block',
  marginTop: '10px',
  color: '#8591a6',
  fontSize: '12px',
}


const cartSummaryStyle: CSSProperties = {
  padding: '18px 20px',
  background: '#f8fafc',
  borderBottom: '1px solid #e7ebf1',
}


const summaryRowStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  marginBottom: '10px',
  color: '#647188',
  fontSize: '14px',
}


const totalRowStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  paddingTop: '14px',
  marginTop: '4px',
  borderTop: '1px solid #dfe5ed',
  color: '#172641',
  fontSize: '18px',
}


const checkoutAreaStyle: CSSProperties = {
  padding: '18px 20px 20px',
}


const saleErrorStyle: CSSProperties = {
  margin: '16px 20px 0',
  padding: '12px 14px',
  borderRadius: '8px',
  background: '#fff2f0',
  border: '1px solid #ffd8d2',
  color: '#b33a2f',
  fontSize: '14px',
  lineHeight: 1.5,
}


const successStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
  padding: '13px 16px',
  marginBottom: '20px',
  borderRadius: '10px',
  border: '1px solid #cfeadd',
  background: '#effaf5',
  color: '#176f50',
  fontSize: '15px',
  fontWeight: 500,
}


const successIconStyle: CSSProperties = {
  width: '30px',
  height: '30px',
  flex: '0 0 30px',
  borderRadius: '50%',
  background: '#d9f3e7',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
}


const stateStyle: CSSProperties = {
  minHeight: '320px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  color: '#738096',
}


const errorStateStyle: CSSProperties = {
  minHeight: '320px',
  padding: '32px',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '14px',
  textAlign: 'center',
}


const mutedTextStyle: CSSProperties = {
  color: '#738096',
}


const emptyStateStyle: CSSProperties = {
  minHeight: '320px',
  padding: '40px 20px',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  textAlign: 'center',
}


const emptyIconStyle: CSSProperties = {
  width: '58px',
  height: '58px',
  borderRadius: '14px',
  background: '#eef4ff',
  color: '#4285ff',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  marginBottom: '18px',
}


const emptyTitleStyle: CSSProperties = {
  margin: '0 0 8px',
  color: '#172641',
}


const emptyTextStyle: CSSProperties = {
  margin: 0,
  maxWidth: '390px',
  color: '#738096',
  lineHeight: 1.6,
}


const noResultStyle: CSSProperties = {
  padding: '42px 20px',
  textAlign: 'center',
  color: '#738096',
  fontSize: '14px',
}