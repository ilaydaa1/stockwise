import {
  useEffect,
  useMemo,
  useState,
  type CSSProperties,
  type FormEvent,
} from 'react'

import {
  createStockMovement,
  getProducts,
  getStockMovements,
  type MovementType,
  type Product,
  type StockMovement,
} from '../lib/api'

import './dashboard.css'


type IconName =
  | 'stock'
  | 'plus'
  | 'refresh'
  | 'close'
  | 'search'
  | 'arrowIn'
  | 'arrowOut'


const iconPaths: Record<IconName, string> = {
  stock:
    'M4 7h15m-4-4 4 4-4 4M20 17H5m4-4-4 4 4 4',

  plus:
    'M12 5v14M5 12h14',

  refresh:
    'M20 6v5h-5M4 18v-5h5M18.5 9A7 7 0 0 0 6.3 6.3L4 9M5.5 15A7 7 0 0 0 17.7 17.7L20 15',

  close:
    'm6 6 12 12M6 18 18 6',

  search:
    'm21 21-4.35-4.35M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z',

  arrowIn:
    'M12 3v14M7 12l5 5 5-5M5 21h14',

  arrowOut:
    'M12 21V7M7 12l5-5 5 5M5 3h14',
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


interface MovementFormState {
  product_id: string
  movement_type: MovementType
  quantity: string
  note: string
}


const emptyForm: MovementFormState = {
  product_id: '',
  movement_type: 'IN',
  quantity: '',
  note: '',
}


const movementLabels: Record<MovementType, string> = {
  IN: 'Stok Girişi',
  OUT: 'Stok Çıkışı',
  ADJUSTMENT_IN: 'Sayım Fazlası',
  ADJUSTMENT_OUT: 'Sayım Eksiği',
}


function isIncomingMovement(
  movementType: MovementType
) {
  return (
    movementType === 'IN' ||
    movementType === 'ADJUSTMENT_IN'
  )
}


function formatDate(value: string) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat('tr-TR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date)
}


export default function StockMovements() {
  const [products, setProducts] =
    useState<Product[]>([])

  const [movements, setMovements] =
    useState<StockMovement[]>([])

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState<string | null>(null)

  const [search, setSearch] =
    useState('')

  const [productFilter, setProductFilter] =
    useState('')

  const [formOpen, setFormOpen] =
    useState(false)

  const [form, setForm] =
    useState<MovementFormState>(emptyForm)

  const [formError, setFormError] =
    useState<string | null>(null)

  const [saving, setSaving] =
    useState(false)


  const loadData = async () => {
    setLoading(true)
    setError(null)

    const [
      productsResult,
      movementsResult,
    ] = await Promise.all([
      getProducts(),
      getStockMovements(),
    ])

    if (!productsResult.data) {
      setError(
        productsResult.error ||
          'Ürünler yüklenirken bir hata oluştu.'
      )

      setLoading(false)
      return
    }

    if (!movementsResult.data) {
      setError(
        movementsResult.error ||
          'Stok hareketleri yüklenirken bir hata oluştu.'
      )

      setLoading(false)
      return
    }

    setProducts(productsResult.data)
    setMovements(movementsResult.data)
    setLoading(false)
  }


  useEffect(() => {
    loadData()
  }, [])


  const productMap = useMemo(() => {
    return new Map(
      products.map((product) => [
        product.id,
        product,
      ])
    )
  }, [products])


  const normalizedSearch =
    search
      .trim()
      .toLocaleLowerCase('tr-TR')


  const filteredMovements =
    movements.filter((movement) => {
      if (
        productFilter &&
        movement.product_id !== productFilter
      ) {
        return false
      }

      if (!normalizedSearch) {
        return true
      }

      const product =
        productMap.get(movement.product_id)

      const productName =
        product?.name
          .toLocaleLowerCase('tr-TR') || ''

      const sku =
        product?.sku
          .toLocaleLowerCase('tr-TR') || ''

      const note =
        movement.note
          ?.toLocaleLowerCase('tr-TR') || ''

      return (
        productName.includes(normalizedSearch) ||
        sku.includes(normalizedSearch) ||
        note.includes(normalizedSearch)
      )
    })


  const openForm = () => {
    setForm({
      ...emptyForm,
      product_id:
        productFilter ||
        products[0]?.id ||
        '',
    })

    setFormError(null)
    setFormOpen(true)
  }


  const closeForm = () => {
    if (saving) {
      return
    }

    setFormOpen(false)
    setForm(emptyForm)
    setFormError(null)
  }


  const updateForm = (
    field: keyof MovementFormState,
    value: string
  ) => {
    setForm((current) => ({
      ...current,
      [field]: value,
    }))
  }


  const selectedProduct =
    products.find(
      (product) =>
        product.id === form.product_id
    ) || null


  const quantity = Number(form.quantity)

  const hasValidQuantity =
    form.quantity.trim() !== '' &&
    Number.isInteger(quantity) &&
    quantity > 0

  const insufficientStock =
    selectedProduct !== null &&
    hasValidQuantity &&
    !isIncomingMovement(
      form.movement_type
    ) &&
    quantity >
      selectedProduct.stock_quantity

  const estimatedStock =
    selectedProduct &&
    hasValidQuantity &&
    !insufficientStock
      ? selectedProduct.stock_quantity +
        (isIncomingMovement(
          form.movement_type
        )
          ? quantity
          : -quantity)
      : null


  const handleSaveMovement = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault()
    setFormError(null)

    if (!form.product_id) {
      setFormError(
        'Lütfen bir ürün seçin.'
      )
      return
    }

    if (!hasValidQuantity) {
      setFormError(
        'Miktar 0’dan büyük bir tam sayı olmalıdır.'
      )
      return
    }

    if (insufficientStock) {
      setFormError(
        `Yetersiz stok. Mevcut stok: ${selectedProduct?.stock_quantity ?? 0}`
      )
      return
    }

    setSaving(true)

    const result =
      await createStockMovement({
        product_id: form.product_id,
        movement_type:
          form.movement_type,
        quantity,
        note:
          form.note.trim() || undefined,
      })

    if (!result.data) {
      const message =
        result.error === 'INSUFFICIENT_STOCK'
          ? 'Bu işlem için yeterli stok bulunmuyor.'
          : result.error === 'PRODUCT_NOT_FOUND'
            ? 'Seçilen ürün bulunamadı.'
            : result.error ||
              'Stok hareketi kaydedilemedi.'

      setFormError(message)
      setSaving(false)
      return
    }

    const createdMovement =
      result.data

    setMovements((current) => [
      createdMovement,
      ...current,
    ])

    setProducts((current) =>
      current.map((product) =>
        product.id ===
        createdMovement.product_id
          ? {
              ...product,
              stock_quantity:
                createdMovement.stock_after,
            }
          : product
      )
    )

    setSaving(false)
    setFormOpen(false)
    setForm(emptyForm)
    setFormError(null)
  }


  return (
    <>
      <main
        id="sw-main"
        className="sw-main"
      >
        <section className="sw-page-heading">
          <div>
            <p className="sw-eyebrow">
              STOK YÖNETİMİ
            </p>

            <h1>
              Stok Hareketleri
            </h1>

            <p className="sw-subtitle">
              Ürün girişlerini, çıkışlarını ve
              stok düzeltmelerini kaydet ve takip et.
            </p>
          </div>

          <div className="sw-heading-actions">
            <button
              type="button"
              className="sw-primary-button"
              onClick={openForm}
              disabled={
                loading ||
                products.length === 0
              }
            >
              <Icon
                name="plus"
                size={17}
              />

              Yeni Stok Hareketi
            </button>
          </div>
        </section>


        <section className="sw-panel">
          <header className="sw-panel-heading">
            <div>
              <h2>
                Hareket geçmişi
              </h2>

              <p>
                İşletmendeki tüm stok
                değişiklikleri
              </p>
            </div>

            {!loading && !error && (
              <span className="sw-count">
                {movements.length} hareket
              </span>
            )}
          </header>


          {!loading &&
            !error &&
            products.length > 0 && (
              <div style={filterAreaStyle}>
                <div style={searchWrapperStyle}>
                  <span style={searchIconStyle}>
                    <Icon
                      name="search"
                      size={17}
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
                    placeholder="Ürün, SKU veya not ara..."
                    aria-label="Stok hareketi ara"
                    style={{
                      ...inputStyle,
                      paddingLeft: '40px',
                    }}
                  />
                </div>

                <select
                  value={productFilter}
                  onChange={(event) =>
                    setProductFilter(
                      event.target.value
                    )
                  }
                  aria-label="Ürüne göre filtrele"
                  style={{
                    ...inputStyle,
                    width: '220px',
                  }}
                >
                  <option value="">
                    Tüm ürünler
                  </option>

                  {products.map((product) => (
                    <option
                      key={product.id}
                      value={product.id}
                    >
                      {product.name} ({product.sku})
                    </option>
                  ))}
                </select>

                <button
                  type="button"
                  onClick={loadData}
                  style={refreshButtonStyle}
                  title="Listeyi yenile"
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
              Stok hareketleri yükleniyor...
            </div>
          )}


          {!loading && error && (
            <div style={errorStateStyle}>
              <strong>
                Stok hareketleri yüklenemedi
              </strong>

              <span
                style={{
                  color: '#738096',
                }}
              >
                {error}
              </span>

              <button
                type="button"
                onClick={loadData}
                className="sw-primary-button"
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
                    name="stock"
                    size={27}
                  />
                </span>

                <h2
                  style={{
                    margin: '0 0 8px',
                  }}
                >
                  Önce ürün eklemelisin
                </h2>

                <p style={emptyTextStyle}>
                  Stok hareketi oluşturabilmek
                  için işletmende en az bir aktif
                  ürün bulunmalıdır.
                </p>
              </div>
            )}


          {!loading &&
            !error &&
            products.length > 0 &&
            movements.length === 0 && (
              <div style={emptyStateStyle}>
                <span style={emptyIconStyle}>
                  <Icon
                    name="stock"
                    size={27}
                  />
                </span>

                <h2
                  style={{
                    margin: '0 0 8px',
                  }}
                >
                  Henüz stok hareketi yok
                </h2>

                <p style={emptyTextStyle}>
                  İlk stok girişini veya çıkışını
                  kaydettiğinde hareket geçmişi
                  burada görünecek.
                </p>

                <button
                  type="button"
                  className="sw-primary-button"
                  onClick={openForm}
                >
                  <Icon
                    name="plus"
                    size={17}
                  />

                  İlk Hareketi Ekle
                </button>
              </div>
            )}


          {!loading &&
            !error &&
            movements.length > 0 && (
              <div className="sw-table-container">
                <table className="sw-product-table">
                  <thead>
                    <tr>
                      <th scope="col">
                        Ürün
                      </th>

                      <th scope="col">
                        Hareket
                      </th>

                      <th scope="col">
                        Miktar
                      </th>

                      <th scope="col">
                        Önceki Stok
                      </th>

                      <th scope="col">
                        Sonraki Stok
                      </th>

                      <th scope="col">
                        Not
                      </th>

                      <th scope="col">
                        Tarih
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {filteredMovements.map(
                      (movement) => {
                        const product =
                          productMap.get(
                            movement.product_id
                          )

                        const incoming =
                          isIncomingMovement(
                            movement.movement_type
                          )

                        return (
                          <tr key={movement.id}>
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
                                    name="stock"
                                    size={18}
                                  />
                                </span>

                                <span>
                                  <strong>
                                    {product?.name ||
                                      'Ürün'}
                                  </strong>

                                  <small>
                                    {product?.sku ||
                                      movement.product_id}
                                  </small>
                                </span>
                              </div>
                            </td>

                            <td>
                              <span
                                style={{
                                  ...movementBadgeStyle,
                                  ...(incoming
                                    ? incomingBadgeStyle
                                    : outgoingBadgeStyle),
                                }}
                              >
                                <Icon
                                  name={
                                    incoming
                                      ? 'arrowIn'
                                      : 'arrowOut'
                                  }
                                  size={14}
                                />

                                {
                                  movementLabels[
                                    movement
                                      .movement_type
                                  ]
                                }
                              </span>
                            </td>

                            <td>
                              <strong
                                style={{
                                  color: incoming
                                    ? '#16805b'
                                    : '#c44747',
                                }}
                              >
                                {incoming
                                  ? '+'
                                  : '-'}
                                {movement.quantity}
                              </strong>
                            </td>

                            <td>
                              {
                                movement.stock_before
                              }
                            </td>

                            <td>
                              <strong>
                                {
                                  movement.stock_after
                                }
                              </strong>
                            </td>

                            <td>
                              <span
                                title={
                                  movement.note || ''
                                }
                                style={noteStyle}
                              >
                                {movement.note || '—'}
                              </span>
                            </td>

                            <td>
                              <span style={dateStyle}>
                                {formatDate(
                                  movement.created_at
                                )}
                              </span>
                            </td>
                          </tr>
                        )
                      }
                    )}
                  </tbody>
                </table>

                {filteredMovements.length ===
                  0 && (
                  <div
                    style={{
                      padding: '40px 20px',
                      textAlign: 'center',
                      color: '#738096',
                    }}
                  >
                    Filtrelere uygun stok
                    hareketi bulunamadı.
                  </div>
                )}
              </div>
            )}
        </section>
      </main>


      {formOpen && (
        <div
          role="presentation"
          onMouseDown={(event) => {
            if (
              event.target ===
              event.currentTarget
            ) {
              closeForm()
            }
          }}
          style={overlayStyle}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="stock-movement-title"
            style={modalStyle}
          >
            <div style={modalHeaderStyle}>
              <div>
                <h2
                  id="stock-movement-title"
                  style={{
                    margin: '0 0 5px',
                    color: '#10213f',
                    fontSize: '20px',
                  }}
                >
                  Yeni Stok Hareketi
                </h2>

                <p
                  style={{
                    margin: 0,
                    color: '#7b8799',
                    fontSize: '13px',
                  }}
                >
                  Ürünün stok miktarını giriş,
                  çıkış veya sayım düzeltmesiyle
                  güncelle.
                </p>
              </div>

              <button
                type="button"
                onClick={closeForm}
                disabled={saving}
                aria-label="Formu kapat"
                style={{
                  ...iconButtonStyle,
                  cursor: saving
                    ? 'not-allowed'
                    : 'pointer',
                }}
              >
                <Icon
                  name="close"
                  size={18}
                />
              </button>
            </div>


            <form onSubmit={handleSaveMovement}>
              <div style={formGridStyle}>
                <label
                  style={{
                    ...labelStyle,
                    gridColumn: '1 / -1',
                  }}
                >
                  Ürün

                  <select
                    value={form.product_id}
                    onChange={(event) =>
                      updateForm(
                        'product_id',
                        event.target.value
                      )
                    }
                    disabled={saving}
                    style={inputStyle}
                    autoFocus
                  >
                    <option value="">
                      Ürün seçin
                    </option>

                    {products.map((product) => (
                      <option
                        key={product.id}
                        value={product.id}
                      >
                        {product.name} —{' '}
                        {product.sku}
                      </option>
                    ))}
                  </select>
                </label>


                {selectedProduct && (
                  <div style={stockInfoStyle}>
                    <span>
                      Mevcut stok
                    </span>

                    <strong>
                      {
                        selectedProduct.stock_quantity
                      }
                    </strong>

                    <small>
                      Minimum stok:{' '}
                      {
                        selectedProduct.minimum_stock
                      }
                    </small>
                  </div>
                )}


                <label style={labelStyle}>
                  Hareket türü

                  <select
                    value={
                      form.movement_type
                    }
                    onChange={(event) =>
                      updateForm(
                        'movement_type',
                        event.target
                          .value as MovementType
                      )
                    }
                    disabled={saving}
                    style={inputStyle}
                  >
                    <option value="IN">
                      Stok Girişi
                    </option>

                    <option value="OUT">
                      Stok Çıkışı
                    </option>

                    <option value="ADJUSTMENT_IN">
                      Sayım Fazlası
                    </option>

                    <option value="ADJUSTMENT_OUT">
                      Sayım Eksiği
                    </option>
                  </select>
                </label>


                <label style={labelStyle}>
                  Miktar

                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={form.quantity}
                    onChange={(event) =>
                      updateForm(
                        'quantity',
                        event.target.value
                      )
                    }
                    disabled={saving}
                    placeholder="Örn. 10"
                    style={inputStyle}
                  />
                </label>


                <label
                  style={{
                    ...labelStyle,
                    gridColumn: '1 / -1',
                  }}
                >
                  Not

                  <textarea
                    value={form.note}
                    onChange={(event) =>
                      updateForm(
                        'note',
                        event.target.value
                      )
                    }
                    disabled={saving}
                    maxLength={255}
                    placeholder="İsteğe bağlı açıklama..."
                    style={textareaStyle}
                  />

                  <span style={characterCountStyle}>
                    {form.note.length}/255
                  </span>
                </label>


                {selectedProduct &&
                  hasValidQuantity && (
                    <div style={previewStyle}>
                      <span>
                        İşlem sonrası tahmini stok
                      </span>

                      <strong
                        style={{
                          color: insufficientStock
                            ? '#c44747'
                            : '#172641',
                        }}
                      >
                        {insufficientStock
                          ? 'Yetersiz stok'
                          : estimatedStock}
                      </strong>
                    </div>
                  )}


                {insufficientStock && (
                  <div
                    role="alert"
                    style={formErrorStyle}
                  >
                    Yetersiz stok. Mevcut stok:{' '}
                    {
                      selectedProduct
                        ?.stock_quantity
                    }
                  </div>
                )}


                {formError &&
                  !insufficientStock && (
                    <div
                      role="alert"
                      style={formErrorStyle}
                    >
                      {formError}
                    </div>
                  )}
              </div>


              <div style={modalFooterStyle}>
                <button
                  type="button"
                  onClick={closeForm}
                  disabled={saving}
                  style={{
                    ...secondaryButtonStyle,
                    cursor: saving
                      ? 'not-allowed'
                      : 'pointer',
                  }}
                >
                  İptal
                </button>

                <button
                  type="submit"
                  className="sw-primary-button"
                  disabled={
                    saving ||
                    insufficientStock
                  }
                >
                  {saving
                    ? 'Kaydediliyor...'
                    : 'Hareketi Kaydet'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}


const labelStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '7px',
  fontSize: '13px',
  fontWeight: 600,
  color: '#293851',
}


const inputStyle: CSSProperties = {
  width: '100%',
  height: '42px',
  boxSizing: 'border-box',
  border: '1px solid #dce2ea',
  borderRadius: '8px',
  padding: '0 12px',
  background: '#fff',
  color: '#172641',
  font: 'inherit',
  outline: 'none',
}


const textareaStyle: CSSProperties = {
  ...inputStyle,
  height: '92px',
  minHeight: '92px',
  padding: '11px 12px',
  resize: 'vertical',
}


const filterAreaStyle: CSSProperties = {
  padding: '0 20px 20px',
  display: 'flex',
  alignItems: 'center',
  flexWrap: 'wrap',
  gap: '10px',
}


const searchWrapperStyle: CSSProperties = {
  position: 'relative',
  width: '100%',
  maxWidth: '360px',
}


const searchIconStyle: CSSProperties = {
  position: 'absolute',
  left: '13px',
  top: '50%',
  transform: 'translateY(-50%)',
  color: '#8591a6',
  display: 'flex',
  zIndex: 1,
}


const refreshButtonStyle: CSSProperties = {
  height: '42px',
  padding: '0 14px',
  border: '1px solid #dce2ea',
  borderRadius: '8px',
  background: '#fff',
  color: '#42516a',
  fontWeight: 600,
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  gap: '7px',
}


const stateStyle: CSSProperties = {
  minHeight: '280px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  color: '#738096',
}


const errorStateStyle: CSSProperties = {
  minHeight: '280px',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '14px',
  padding: '32px',
  textAlign: 'center',
}


const emptyStateStyle: CSSProperties = {
  minHeight: '320px',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  textAlign: 'center',
  padding: '40px 20px',
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


const emptyTextStyle: CSSProperties = {
  margin: '0 0 20px',
  color: '#738096',
  maxWidth: '420px',
  lineHeight: 1.6,
}


const movementBadgeStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '6px',
  padding: '6px 9px',
  borderRadius: '7px',
  fontSize: '12px',
  fontWeight: 600,
  whiteSpace: 'nowrap',
}


const incomingBadgeStyle: CSSProperties = {
  background: '#edf9f4',
  color: '#16805b',
}


const outgoingBadgeStyle: CSSProperties = {
  background: '#fff1f1',
  color: '#c44747',
}


const noteStyle: CSSProperties = {
  display: 'block',
  maxWidth: '190px',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
  color: '#647188',
}


const dateStyle: CSSProperties = {
  color: '#647188',
  fontSize: '13px',
  whiteSpace: 'nowrap',
}


const overlayStyle: CSSProperties = {
  position: 'fixed',
  inset: 0,
  zIndex: 1000,
  background: 'rgba(8, 25, 50, 0.48)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '24px',
}


const modalStyle: CSSProperties = {
  width: '100%',
  maxWidth: '620px',
  maxHeight: 'calc(100vh - 48px)',
  overflowY: 'auto',
  background: '#fff',
  borderRadius: '14px',
  boxShadow:
    '0 24px 60px rgba(15, 31, 56, 0.22)',
}


const modalHeaderStyle: CSSProperties = {
  padding: '22px 24px',
  borderBottom: '1px solid #e7ebf1',
  display: 'flex',
  alignItems: 'flex-start',
  justifyContent: 'space-between',
  gap: '20px',
}


const formGridStyle: CSSProperties = {
  padding: '24px',
  display: 'grid',
  gridTemplateColumns:
    'repeat(2, minmax(0, 1fr))',
  gap: '18px',
}


const modalFooterStyle: CSSProperties = {
  padding: '18px 24px',
  borderTop: '1px solid #e7ebf1',
  display: 'flex',
  justifyContent: 'flex-end',
  gap: '10px',
}


const secondaryButtonStyle: CSSProperties = {
  height: '40px',
  padding: '0 18px',
  borderRadius: '8px',
  border: '1px solid #dce2ea',
  background: '#fff',
  color: '#35445d',
  fontWeight: 600,
}


const iconButtonStyle: CSSProperties = {
  width: '34px',
  height: '34px',
  border: 'none',
  borderRadius: '8px',
  background: '#f4f6f9',
  color: '#647188',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
}


const stockInfoStyle: CSSProperties = {
  gridColumn: '1 / -1',
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
  padding: '12px 14px',
  borderRadius: '8px',
  background: '#f5f8fc',
  border: '1px solid #e3e9f1',
  color: '#647188',
  fontSize: '13px',
}


const previewStyle: CSSProperties = {
  gridColumn: '1 / -1',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '13px 14px',
  borderRadius: '8px',
  background: '#eef4ff',
  border: '1px solid #d9e6ff',
  color: '#42516a',
  fontSize: '13px',
}


const formErrorStyle: CSSProperties = {
  gridColumn: '1 / -1',
  padding: '11px 13px',
  borderRadius: '8px',
  background: '#fff2f0',
  border: '1px solid #ffd8d2',
  color: '#b33a2f',
  fontSize: '13px',
}


const characterCountStyle: CSSProperties = {
  alignSelf: 'flex-end',
  color: '#8591a6',
  fontSize: '11px',
  fontWeight: 400,
}