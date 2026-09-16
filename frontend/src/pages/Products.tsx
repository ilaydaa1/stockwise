import {
  useEffect,
  useState,
  type CSSProperties,
  type FormEvent,
} from 'react'

import {
  createProduct,
  deleteProduct,
  getProducts,
  updateProduct,
  type CreateProductPayload,
  type UpdateProductPayload,
  type Product,
} from '../lib/api'

import './dashboard.css'

type IconName =
  | 'box'
  | 'plus'
  | 'search'
  | 'refresh'
  | 'close'
  | 'edit'
  | 'trash'

const iconPaths: Record<IconName, string> = {
  box:
    'm12 3 9 5v8l-9 5-9-5V8l9-5ZM3 8l9 5 9-5M12 13v8M7.5 5.5l9 5',

  plus:
    'M12 5v14M5 12h14',

  search:
    'm21 21-4.35-4.35M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z',

  refresh:
    'M20 6v5h-5M4 18v-5h5M18.5 9A7 7 0 0 0 6.3 6.3L4 9M5.5 15A7 7 0 0 0 17.7 17.7L20 15',

  close:
    'm6 6 12 12M6 18 18 6',

  edit:
    'M12 20h9M16.5 3.5a2.12 2.12 0 0 1 3 3L8 18l-4 1 1-4Z',

  trash:
    'M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6M10 11v5M14 11v5',
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

interface ProductFormState {
  name: string
  sku: string
  purchase_price: string
  sale_price: string
  stock_quantity: string
  minimum_stock: string
}

const emptyForm: ProductFormState = {
  name: '',
  sku: '',
  purchase_price: '',
  sale_price: '',
  stock_quantity: '0',
  minimum_stock: '0',
}

function formatMoney(
  value: string,
  currency: string = 'TRY'
) {
  const amount = Number(value)

  if (Number.isNaN(amount)) {
    return value
  }

  return new Intl.NumberFormat('tr-TR', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

function getStockStatus(product: Product) {
  if (product.stock_quantity === 0) {
    return {
      label: 'Tükendi',
      className: 'is-critical',
    }
  }

  if (
    product.stock_quantity <=
    product.minimum_stock
  ) {
    return {
      label: 'Kritik',
      className: 'is-low',
    }
  }

  return {
    label: 'Yeterli',
    className: 'is-ok',
  }
}

export default function Products() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [search, setSearch] = useState('')

  const [formOpen, setFormOpen] = useState(false)
  const [editingProduct, setEditingProduct] =
    useState<Product | null>(null)

  const [form, setForm] =
    useState<ProductFormState>(emptyForm)

  const [formError, setFormError] =
    useState<string | null>(null)

  const [saving, setSaving] = useState(false)

  const [deletingProduct, setDeletingProduct] =
    useState<Product | null>(null)

  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] =
    useState<string | null>(null)

  const loadProducts = async () => {
    setLoading(true)
    setError(null)

    const result = await getProducts()

    if (result.data) {
      setProducts(result.data)
    } else {
      setError(
        result.error ||
          'Ürünler yüklenirken bir hata oluştu.'
      )
    }

    setLoading(false)
  }

  useEffect(() => {
    loadProducts()
  }, [])

  const openCreateForm = () => {
    setEditingProduct(null)
    setForm(emptyForm)
    setFormError(null)
    setFormOpen(true)
  }

  const openEditForm = (product: Product) => {
    setEditingProduct(product)

    setForm({
      name: product.name,
      sku: product.sku,
      purchase_price: product.purchase_price,
      sale_price: product.sale_price,
      stock_quantity:
        product.stock_quantity.toString(),
      minimum_stock:
        product.minimum_stock.toString(),
    })

    setFormError(null)
    setFormOpen(true)
  }

  const closeForm = () => {
    if (saving) {
      return
    }

    setFormOpen(false)
    setEditingProduct(null)
    setForm(emptyForm)
    setFormError(null)
  }

  const updateForm = (
    field: keyof ProductFormState,
    value: string
  ) => {
    setForm((current) => ({
      ...current,
      [field]: value,
    }))
  }

  const validateCommonFields = () => {
    const name = form.name.trim()
    const sku = form.sku.trim().toUpperCase()

    const purchasePrice = Number(
      form.purchase_price
    )

    const salePrice = Number(
      form.sale_price
    )

    const minimumStock = Number(
      form.minimum_stock
    )

    if (name.length < 2) {
      setFormError(
        'Ürün adı en az 2 karakter olmalıdır.'
      )
      return null
    }

    if (!sku) {
      setFormError('SKU boş olamaz.')
      return null
    }

    if (
      form.purchase_price.trim() === '' ||
      Number.isNaN(purchasePrice) ||
      purchasePrice < 0
    ) {
      setFormError(
        'Geçerli bir alış fiyatı girin.'
      )
      return null
    }

    if (
      form.sale_price.trim() === '' ||
      Number.isNaN(salePrice) ||
      salePrice < 0
    ) {
      setFormError(
        'Geçerli bir satış fiyatı girin.'
      )
      return null
    }

    if (
      form.minimum_stock.trim() === '' ||
      !Number.isInteger(minimumStock) ||
      minimumStock < 0
    ) {
      setFormError(
        'Minimum stok 0 veya daha büyük bir tam sayı olmalıdır.'
      )
      return null
    }

    return {
      name,
      sku,
      minimumStock,
    }
  }

  const handleSaveProduct = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault()

    setFormError(null)

    const validated = validateCommonFields()

    if (!validated) {
      return
    }

    const {
      name,
      sku,
      minimumStock,
    } = validated

    setSaving(true)

    if (editingProduct) {
      const payload: UpdateProductPayload = {
        name,
        sku,
        purchase_price:
          form.purchase_price,
        sale_price:
          form.sale_price,
        minimum_stock:
          minimumStock,
      }

      const result = await updateProduct(
        editingProduct.id,
        payload
      )

      if (!result.data) {
        setFormError(
          result.error ||
            'Ürün güncellenirken bir hata oluştu.'
        )
        setSaving(false)
        return
      }

      const updatedProduct = result.data

      setProducts((current) =>
        current.map((product) =>
          product.id === updatedProduct.id
            ? updatedProduct
            : product
        )
      )

      setSaving(false)
      closeForm()
      return
    }

    const stockQuantity = Number(
      form.stock_quantity
    )

    if (
      form.stock_quantity.trim() === '' ||
      !Number.isInteger(stockQuantity) ||
      stockQuantity < 0
    ) {
      setFormError(
        'Başlangıç stoku 0 veya daha büyük bir tam sayı olmalıdır.'
      )
      setSaving(false)
      return
    }

    const payload: CreateProductPayload = {
      name,
      sku,
      purchase_price:
        form.purchase_price,
      sale_price:
        form.sale_price,
      stock_quantity:
        stockQuantity,
      minimum_stock:
        minimumStock,
    }

    const result = await createProduct(payload)

    if (!result.data) {
      setFormError(
        result.error ||
          'Ürün kaydedilirken bir hata oluştu.'
      )

      setSaving(false)
      return
    }

    setProducts((current) => [
      result.data as Product,
      ...current,
    ])

    setSaving(false)
    closeForm()
  }

  const openDeleteConfirmation = (
    product: Product
  ) => {
    setDeletingProduct(product)
    setDeleteError(null)
  }

  const closeDeleteConfirmation = () => {
    if (deleting) {
      return
    }

    setDeletingProduct(null)
    setDeleteError(null)
  }

  const handleDeleteProduct = async () => {
    if (!deletingProduct) {
      return
    }

    setDeleting(true)
    setDeleteError(null)

    const productId = deletingProduct.id

    const result = await deleteProduct(productId)

    if (result.status !== 204) {
      setDeleteError(
        result.error ||
          'Ürün silinirken bir hata oluştu.'
      )

      setDeleting(false)
      return
    }

    setProducts((current) =>
      current.filter(
        (product) =>
          product.id !== productId
      )
    )

    setDeleting(false)
    setDeletingProduct(null)
  }

  const normalizedSearch =
    search
      .trim()
      .toLocaleLowerCase('tr-TR')

  const filteredProducts =
    products.filter((product) => {
      if (!normalizedSearch) {
        return true
      }

      return (
        product.name
          .toLocaleLowerCase('tr-TR')
          .includes(normalizedSearch) ||
        product.sku
          .toLocaleLowerCase('tr-TR')
          .includes(normalizedSearch)
      )
    })

  return (
    <>
      <main
        id="sw-main"
        className="sw-main"
      >
        <section className="sw-page-heading">
          <div>
            <p className="sw-eyebrow">
              ÜRÜN YÖNETİMİ
            </p>

            <h1>Ürünler</h1>

            <p className="sw-subtitle">
              Ürünlerini, fiyatlarını ve stok
              seviyelerini tek yerden yönet.
            </p>
          </div>

          <div className="sw-heading-actions">
            <button
              type="button"
              className="sw-primary-button"
              onClick={openCreateForm}
            >
              <Icon
                name="plus"
                size={17}
              />

              Yeni Ürün
            </button>
          </div>
        </section>

        <section className="sw-panel">
          <header className="sw-panel-heading">
            <div>
              <h2>Ürün listesi</h2>

              <p>
                İşletmene kayıtlı aktif ürünler
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
              <div
                style={{
                  padding: '0 20px 20px',
                }}
              >
                <div
                  style={{
                    position: 'relative',
                    maxWidth: '360px',
                  }}
                >
                  <span
                    style={{
                      position: 'absolute',
                      left: '13px',
                      top: '50%',
                      transform:
                        'translateY(-50%)',
                      color: '#8591a6',
                      display: 'flex',
                    }}
                  >
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
                    placeholder="Ürün adı veya SKU ara..."
                    aria-label="Ürün ara"
                    style={{
                      width: '100%',
                      height: '42px',
                      border:
                        '1px solid #dfe5ee',
                      borderRadius: '8px',
                      padding:
                        '0 14px 0 40px',
                      outline: 'none',
                      font: 'inherit',
                      color: '#13213c',
                      background: '#fff',
                    }}
                  />
                </div>
              </div>
            )}

          {loading && (
            <div
              style={{
                minHeight: '280px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#738096',
              }}
            >
              Ürünler yükleniyor...
            </div>
          )}

          {!loading && error && (
            <div
              style={{
                minHeight: '280px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '14px',
                padding: '32px',
                textAlign: 'center',
              }}
            >
              <strong>
                Ürünler yüklenemedi
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
                onClick={loadProducts}
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
              <div
                style={{
                  minHeight: '320px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  textAlign: 'center',
                  padding: '40px 20px',
                }}
              >
                <span
                  style={{
                    width: '58px',
                    height: '58px',
                    borderRadius: '14px',
                    background: '#eef4ff',
                    color: '#4285ff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent:
                      'center',
                    marginBottom: '18px',
                  }}
                >
                  <Icon
                    name="box"
                    size={26}
                  />
                </span>

                <h2
                  style={{
                    margin: '0 0 8px',
                  }}
                >
                  Henüz ürün yok
                </h2>

                <p
                  style={{
                    margin: '0 0 20px',
                    color: '#738096',
                    maxWidth: '380px',
                  }}
                >
                  İlk ürününü eklediğinde stok
                  ve fiyat bilgilerini burada
                  görebileceksin.
                </p>

                <button
                  type="button"
                  className="sw-primary-button"
                  onClick={openCreateForm}
                >
                  <Icon
                    name="plus"
                    size={17}
                  />

                  İlk Ürünü Ekle
                </button>
              </div>
            )}

          {!loading &&
            !error &&
            products.length > 0 && (
              <div className="sw-table-container">
                <table className="sw-product-table">
                  <thead>
                    <tr>
                      <th scope="col">
                        Ürün
                      </th>

                      <th scope="col">
                        Alış Fiyatı
                      </th>

                      <th scope="col">
                        Satış Fiyatı
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

                      <th scope="col">
                        İşlemler
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {filteredProducts.map(
                      (product) => {
                        const stockStatus =
                          getStockStatus(
                            product
                          )

                        return (
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

                            <td>
                              {formatMoney(
                                product.purchase_price
                              )}
                            </td>

                            <td>
                              {formatMoney(
                                product.sale_price
                              )}
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
                              <span
                                className={`sw-status ${stockStatus.className}`}
                              >
                                {
                                  stockStatus.label
                                }
                              </span>
                            </td>

                            <td>
                              <div
                                style={{
                                  display: 'flex',
                                  gap: '7px',
                                  alignItems:
                                    'center',
                                }}
                              >
                                <button
                                  type="button"
                                  onClick={() =>
                                    openEditForm(
                                      product
                                    )
                                  }
                                  title="Ürünü düzenle"
                                  aria-label={`${product.name} ürününü düzenle`}
                                  style={
                                    editButtonStyle
                                  }
                                >
                                  <Icon
                                    name="edit"
                                    size={16}
                                  />
                                </button>

                                <button
                                  type="button"
                                  onClick={() =>
                                    openDeleteConfirmation(
                                      product
                                    )
                                  }
                                  title="Ürünü sil"
                                  aria-label={`${product.name} ürününü sil`}
                                  style={
                                    deleteButtonStyle
                                  }
                                >
                                  <Icon
                                    name="trash"
                                    size={16}
                                  />
                                </button>
                              </div>
                            </td>
                          </tr>
                        )
                      }
                    )}
                  </tbody>
                </table>

                {filteredProducts.length ===
                  0 && (
                  <div
                    style={{
                      padding:
                        '40px 20px',
                      textAlign: 'center',
                      color: '#738096',
                    }}
                  >
                    Aramana uygun ürün
                    bulunamadı.
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
            aria-labelledby="product-form-title"
            style={modalStyle}
          >
            <div style={modalHeaderStyle}>
              <div>
                <h2
                  id="product-form-title"
                  style={{
                    margin: '0 0 5px',
                    color: '#10213f',
                    fontSize: '20px',
                  }}
                >
                  {editingProduct
                    ? 'Ürünü Düzenle'
                    : 'Yeni Ürün'}
                </h2>

                <p
                  style={{
                    margin: 0,
                    color: '#7b8799',
                    fontSize: '13px',
                  }}
                >
                  {editingProduct
                    ? 'Ürünün temel bilgilerini güncelle.'
                    : 'Ürünün temel bilgilerini ve başlangıç stokunu gir.'}
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

            <form
              onSubmit={handleSaveProduct}
            >
              <div style={formGridStyle}>
                <label
                  style={{
                    ...labelStyle,
                    gridColumn: '1 / -1',
                  }}
                >
                  Ürün adı

                  <input
                    type="text"
                    value={form.name}
                    onChange={(event) =>
                      updateForm(
                        'name',
                        event.target.value
                      )
                    }
                    maxLength={150}
                    autoFocus
                    disabled={saving}
                    placeholder="Örn. Kablosuz Kulaklık"
                    style={inputStyle}
                  />
                </label>

                <label style={labelStyle}>
                  SKU

                  <input
                    type="text"
                    value={form.sku}
                    onChange={(event) =>
                      updateForm(
                        'sku',
                        event.target.value.toUpperCase()
                      )
                    }
                    maxLength={50}
                    disabled={saving}
                    placeholder="Örn. ELK-001"
                    style={inputStyle}
                  />
                </label>

                <label style={labelStyle}>
                  Minimum stok

                  <input
                    type="number"
                    value={
                      form.minimum_stock
                    }
                    onChange={(event) =>
                      updateForm(
                        'minimum_stock',
                        event.target.value
                      )
                    }
                    min="0"
                    step="1"
                    disabled={saving}
                    style={inputStyle}
                  />
                </label>

                <label style={labelStyle}>
                  Alış fiyatı

                  <input
                    type="number"
                    value={
                      form.purchase_price
                    }
                    onChange={(event) =>
                      updateForm(
                        'purchase_price',
                        event.target.value
                      )
                    }
                    min="0"
                    step="0.01"
                    disabled={saving}
                    placeholder="0,00"
                    style={inputStyle}
                  />
                </label>

                <label style={labelStyle}>
                  Satış fiyatı

                  <input
                    type="number"
                    value={
                      form.sale_price
                    }
                    onChange={(event) =>
                      updateForm(
                        'sale_price',
                        event.target.value
                      )
                    }
                    min="0"
                    step="0.01"
                    disabled={saving}
                    placeholder="0,00"
                    style={inputStyle}
                  />
                </label>

                {!editingProduct && (
                  <label
                    style={{
                      ...labelStyle,
                      gridColumn:
                        '1 / -1',
                    }}
                  >
                    Başlangıç stoku

                    <input
                      type="number"
                      value={
                        form.stock_quantity
                      }
                      onChange={(event) =>
                        updateForm(
                          'stock_quantity',
                          event.target.value
                        )
                      }
                      min="0"
                      step="1"
                      disabled={saving}
                      style={inputStyle}
                    />

                    <span
                      style={{
                        fontSize: '12px',
                        fontWeight: 400,
                        lineHeight: 1.5,
                        color: '#8591a6',
                      }}
                    >
                      Bu değer yalnızca
                      ürünün ilk kaydı için
                      kullanılır. Sonraki stok
                      değişiklikleri stok
                      hareketlerinden
                      yönetilecek.
                    </span>
                  </label>
                )}

                {editingProduct && (
                  <div
                    style={{
                      gridColumn:
                        '1 / -1',
                      padding:
                        '12px 14px',
                      borderRadius: '8px',
                      background:
                        '#f5f8fc',
                      border:
                        '1px solid #e3e9f1',
                      fontSize: '13px',
                      color: '#647188',
                    }}
                  >
                    Mevcut stok:{' '}
                    <strong
                      style={{
                        color:
                          '#243550',
                      }}
                    >
                      {
                        editingProduct.stock_quantity
                      }
                    </strong>
                    . Stok miktarı ürün
                    düzenleme ekranından
                    değiştirilemez. Stok
                    hareketlerinden
                    yönetilecektir.
                  </div>
                )}

                {formError && (
                  <div
                    role="alert"
                    style={{
                      gridColumn:
                        '1 / -1',
                      padding:
                        '11px 13px',
                      borderRadius: '8px',
                      background:
                        '#fff2f0',
                      border:
                        '1px solid #ffd8d2',
                      color: '#b33a2f',
                      fontSize: '13px',
                    }}
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
                  disabled={saving}
                >
                  {saving
                    ? editingProduct
                      ? 'Güncelleniyor...'
                      : 'Kaydediliyor...'
                    : editingProduct
                      ? 'Değişiklikleri Kaydet'
                      : 'Ürünü Kaydet'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {deletingProduct && (
        <div
          role="presentation"
          onMouseDown={(event) => {
            if (
              event.target ===
              event.currentTarget
            ) {
              closeDeleteConfirmation()
            }
          }}
          style={overlayStyle}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-product-title"
            style={{
              ...modalStyle,
              maxWidth: '440px',
            }}
          >
            <div style={modalHeaderStyle}>
              <div>
                <h2
                  id="delete-product-title"
                  style={{
                    margin: '0 0 5px',
                    color: '#10213f',
                    fontSize: '20px',
                  }}
                >
                  Ürünü Sil
                </h2>

                <p
                  style={{
                    margin: 0,
                    color: '#7b8799',
                    fontSize: '13px',
                  }}
                >
                  Bu işlem ürünü aktif ürün
                  listesinden kaldırır.
                </p>
              </div>

              <button
                type="button"
                onClick={
                  closeDeleteConfirmation
                }
                disabled={deleting}
                aria-label="Pencereyi kapat"
                style={{
                  ...iconButtonStyle,
                  cursor: deleting
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

            <div
              style={{
                padding: '24px',
              }}
            >
              <p
                style={{
                  margin: 0,
                  color: '#42516a',
                  lineHeight: 1.6,
                  fontSize: '14px',
                }}
              >
                <strong>
                  {deletingProduct.name}
                </strong>{' '}
                ({deletingProduct.sku})
                ürününü silmek istediğine
                emin misin?
              </p>

              {deleteError && (
                <div
                  role="alert"
                  style={{
                    marginTop: '16px',
                    padding:
                      '11px 13px',
                    borderRadius: '8px',
                    background:
                      '#fff2f0',
                    border:
                      '1px solid #ffd8d2',
                    color: '#b33a2f',
                    fontSize: '13px',
                  }}
                >
                  {deleteError}
                </div>
              )}
            </div>

            <div style={modalFooterStyle}>
              <button
                type="button"
                onClick={
                  closeDeleteConfirmation
                }
                disabled={deleting}
                style={{
                  ...secondaryButtonStyle,
                  cursor: deleting
                    ? 'not-allowed'
                    : 'pointer',
                }}
              >
                Vazgeç
              </button>

              <button
                type="button"
                onClick={
                  handleDeleteProduct
                }
                disabled={deleting}
                style={{
                  height: '40px',
                  padding: '0 18px',
                  border: 'none',
                  borderRadius: '8px',
                  background: '#c94040',
                  color: '#fff',
                  fontWeight: 600,
                  cursor: deleting
                    ? 'not-allowed'
                    : 'pointer',
                  opacity: deleting
                    ? 0.7
                    : 1,
                }}
              >
                {deleting
                  ? 'Siliniyor...'
                  : 'Ürünü Sil'}
              </button>
            </div>
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

const editButtonStyle: CSSProperties = {
  width: '34px',
  height: '34px',
  border: '1px solid #dce5f2',
  borderRadius: '8px',
  background: '#f6f9ff',
  color: '#356fd6',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
}

const deleteButtonStyle: CSSProperties = {
  width: '34px',
  height: '34px',
  border: '1px solid #f0d8d8',
  borderRadius: '8px',
  background: '#fff7f7',
  color: '#c94040',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
}