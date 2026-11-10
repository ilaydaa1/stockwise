import { useEffect, useMemo, useState, type FormEvent } from 'react'

import {
  createCategory,
  createSupplier,
  getCategories,
  getProducts,
  getSuppliers,
  updateSupplier,
  type Category,
  type Product,
  type Supplier,
} from '../lib/api'
import {
  ErrorBanner,
  Modal,
  emptyStateStyle,
  hintStyle,
  inputStyle,
  labelStyle,
  secondaryButtonStyle,
  smallButtonStyle,
} from '../components/ui'

import './dashboard.css'


const MAX_LEAD_TIME_DAYS = 365


function describeError(error: string | undefined, fallback: string) {
  if (error === 'SUPPLIER_ALREADY_EXISTS') {
    return 'Bu adla kayıtlı bir tedarikçi zaten var.'
  }

  if (error === 'CATEGORY_ALREADY_EXISTS') {
    return 'Bu adla kayıtlı bir kategori zaten var.'
  }

  return error || fallback
}


export default function Suppliers() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Supplier dialog: null = closed, 'new' = create, otherwise edit.
  const [editing, setEditing] = useState<Supplier | 'new' | null>(null)
  const [supplierName, setSupplierName] = useState('')
  const [leadTime, setLeadTime] = useState('')
  const [supplierError, setSupplierError] = useState<string | null>(null)
  const [savingSupplier, setSavingSupplier] = useState(false)

  const [categoryName, setCategoryName] = useState('')
  const [categoryError, setCategoryError] = useState<string | null>(null)
  const [savingCategory, setSavingCategory] = useState(false)

  const load = async () => {
    setLoading(true)
    setError(null)

    const [supplierResult, categoryResult, productResult] =
      await Promise.all([
        getSuppliers(),
        getCategories(),
        getProducts(),
      ])

    if (
      !supplierResult.data ||
      !categoryResult.data ||
      !productResult.data
    ) {
      setError(
        supplierResult.error ||
          categoryResult.error ||
          productResult.error ||
          'Veriler yüklenirken bir hata oluştu.'
      )
      setLoading(false)
      return
    }

    setSuppliers(supplierResult.data)
    setCategories(categoryResult.data)
    setProducts(productResult.data)
    setLoading(false)
  }

  useEffect(() => {
    load()
  }, [])

  // How many active products use each supplier and category.
  const productCounts = useMemo(() => {
    const bySupplier = new Map<string, number>()
    const byCategory = new Map<string, number>()

    for (const product of products) {
      if (product.supplier_id) {
        bySupplier.set(
          product.supplier_id,
          (bySupplier.get(product.supplier_id) || 0) + 1
        )
      }

      if (product.category_id) {
        byCategory.set(
          product.category_id,
          (byCategory.get(product.category_id) || 0) + 1
        )
      }
    }

    return { bySupplier, byCategory }
  }, [products])

  const openNewSupplier = () => {
    setEditing('new')
    setSupplierName('')
    setLeadTime('')
    setSupplierError(null)
  }

  const openEditSupplier = (supplier: Supplier) => {
    setEditing(supplier)
    setSupplierName(supplier.name)
    setLeadTime(supplier.lead_time_days.toString())
    setSupplierError(null)
  }

  const closeSupplierDialog = () => {
    if (!savingSupplier) {
      setEditing(null)
    }
  }

  const handleSaveSupplier = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault()

    const name = supplierName.trim()
    const days = Number(leadTime)

    if (name.length < 2) {
      setSupplierError('Tedarikçi adı en az 2 karakter olmalıdır.')
      return
    }

    if (
      leadTime.trim() === '' ||
      !Number.isInteger(days) ||
      days < 0 ||
      days > MAX_LEAD_TIME_DAYS
    ) {
      setSupplierError(
        `Tedarik süresi 0 ile ${MAX_LEAD_TIME_DAYS} gün arasında bir tam sayı olmalıdır.`
      )
      return
    }

    setSavingSupplier(true)
    setSupplierError(null)

    const result =
      editing === 'new' || editing === null
        ? await createSupplier({ name, lead_time_days: days })
        : await updateSupplier(editing.id, {
            name,
            lead_time_days: days,
          })

    setSavingSupplier(false)

    if (!result.data) {
      setSupplierError(
        describeError(result.error, 'Tedarikçi kaydedilemedi.')
      )
      return
    }

    const saved = result.data

    setSuppliers((current) =>
      [
        ...current.filter((supplier) => supplier.id !== saved.id),
        saved,
      ].sort((a, b) => a.name.localeCompare(b.name, 'tr-TR'))
    )
    setEditing(null)
  }

  const handleAddCategory = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault()

    const name = categoryName.trim()

    if (name.length < 2) {
      setCategoryError('Kategori adı en az 2 karakter olmalıdır.')
      return
    }

    setSavingCategory(true)
    setCategoryError(null)

    const result = await createCategory({ name })

    setSavingCategory(false)

    if (!result.data) {
      setCategoryError(
        describeError(result.error, 'Kategori kaydedilemedi.')
      )
      return
    }

    const saved = result.data

    setCategories((current) =>
      [...current, saved].sort((a, b) =>
        a.name.localeCompare(b.name, 'tr-TR')
      )
    )
    setCategoryName('')
  }

  return (
    <>
      <main id="sw-main" className="sw-main">
        <section className="sw-page-heading">
          <div>
            <p className="sw-eyebrow">TANIMLAR</p>

            <h1>Tedarikçiler ve Kategoriler</h1>

            <p className="sw-subtitle">
              Ürünlerini gruplandır ve her tedarikçinin teslim
              süresini kaydet. Bu bilgiler stok analizlerinde
              kullanılır.
            </p>
          </div>

          <div className="sw-heading-actions">
            <button
              type="button"
              className="sw-primary-button"
              onClick={openNewSupplier}
            >
              + Yeni Tedarikçi
            </button>
          </div>
        </section>

        {error && (
          <section className="sw-panel">
            <div style={emptyStateStyle}>
              <strong style={{ color: '#172641' }}>
                Veriler yüklenemedi
              </strong>

              <span>{error}</span>

              <button
                type="button"
                className="sw-primary-button"
                onClick={load}
              >
                Tekrar Dene
              </button>
            </div>
          </section>
        )}

        {!error && (
          <>
            <section className="sw-panel">
              <header className="sw-panel-heading">
                <div>
                  <h2>Tedarikçiler</h2>

                  <p>
                    Tedarik süresi, sipariş verildikten sonra
                    ürünün teslim edilmesine kadar geçen gün
                    sayısıdır.
                  </p>
                </div>

                {!loading && (
                  <span className="sw-count">
                    {suppliers.length} tedarikçi
                  </span>
                )}
              </header>

              {loading && (
                <div style={emptyStateStyle}>Yükleniyor...</div>
              )}

              {!loading && suppliers.length === 0 && (
                <div style={emptyStateStyle}>
                  <strong style={{ color: '#172641' }}>
                    Henüz tedarikçi yok
                  </strong>

                  <span>
                    İlk tedarikçini ekleyip ürünlerine
                    atayabilirsin.
                  </span>
                </div>
              )}

              {!loading && suppliers.length > 0 && (
                <div className="sw-table-container">
                  <table className="sw-product-table">
                    <thead>
                      <tr>
                        <th scope="col">Tedarikçi</th>
                        <th scope="col">Tedarik Süresi</th>
                        <th scope="col">Ürün Sayısı</th>
                        <th scope="col">İşlemler</th>
                      </tr>
                    </thead>

                    <tbody>
                      {suppliers.map((supplier) => (
                        <tr key={supplier.id}>
                          <td>
                            <strong>{supplier.name}</strong>
                          </td>

                          <td>{supplier.lead_time_days} gün</td>

                          <td>
                            {productCounts.bySupplier.get(
                              supplier.id
                            ) || 0}
                          </td>

                          <td>
                            <button
                              type="button"
                              style={smallButtonStyle}
                              onClick={() =>
                                openEditSupplier(supplier)
                              }
                              aria-label={`${supplier.name} tedarikçisini düzenle`}
                            >
                              Düzenle
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section
              className="sw-panel"
              style={{ marginTop: '20px' }}
            >
              <header className="sw-panel-heading">
                <div>
                  <h2>Kategoriler</h2>

                  <p>Ürünleri gruplamak için kullanılır.</p>
                </div>

                {!loading && (
                  <span className="sw-count">
                    {categories.length} kategori
                  </span>
                )}
              </header>

              <form
                onSubmit={handleAddCategory}
                style={{
                  padding: '0 20px 16px',
                  display: 'flex',
                  gap: '10px',
                  flexWrap: 'wrap',
                  alignItems: 'flex-start',
                }}
              >
                <input
                  type="text"
                  value={categoryName}
                  onChange={(event) =>
                    setCategoryName(event.target.value)
                  }
                  placeholder="Yeni kategori adı"
                  aria-label="Yeni kategori adı"
                  maxLength={100}
                  disabled={savingCategory}
                  style={{
                    ...inputStyle,
                    maxWidth: '320px',
                  }}
                />

                <button
                  type="submit"
                  className="sw-primary-button"
                  disabled={savingCategory}
                >
                  {savingCategory ? 'Ekleniyor...' : 'Kategori Ekle'}
                </button>
              </form>

              {categoryError && (
                <div style={{ padding: '0 20px 16px' }}>
                  <ErrorBanner>{categoryError}</ErrorBanner>
                </div>
              )}

              {loading && (
                <div style={emptyStateStyle}>Yükleniyor...</div>
              )}

              {!loading && categories.length === 0 && (
                <div style={emptyStateStyle}>
                  Henüz kategori yok.
                </div>
              )}

              {!loading && categories.length > 0 && (
                <div className="sw-table-container">
                  <table className="sw-product-table">
                    <thead>
                      <tr>
                        <th scope="col">Kategori</th>
                        <th scope="col">Ürün Sayısı</th>
                      </tr>
                    </thead>

                    <tbody>
                      {categories.map((category) => (
                        <tr key={category.id}>
                          <td>
                            <strong>{category.name}</strong>
                          </td>

                          <td>
                            {productCounts.byCategory.get(
                              category.id
                            ) || 0}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </>
        )}
      </main>

      {editing !== null && (
        <form onSubmit={handleSaveSupplier}>
          <Modal
            title={
              editing === 'new'
                ? 'Yeni Tedarikçi'
                : 'Tedarikçiyi Düzenle'
            }
            subtitle="Tedarikçinin adını ve teslim süresini gir."
            onClose={closeSupplierDialog}
            maxWidth={480}
            footer={
              <>
                <button
                  type="button"
                  onClick={closeSupplierDialog}
                  disabled={savingSupplier}
                  style={secondaryButtonStyle}
                >
                  Vazgeç
                </button>

                <button
                  type="submit"
                  className="sw-primary-button"
                  disabled={savingSupplier}
                >
                  {savingSupplier ? 'Kaydediliyor...' : 'Kaydet'}
                </button>
              </>
            }
          >
            <label style={labelStyle}>
              Tedarikçi adı
              <input
                type="text"
                value={supplierName}
                onChange={(event) =>
                  setSupplierName(event.target.value)
                }
                maxLength={100}
                disabled={savingSupplier}
                autoFocus
                style={inputStyle}
              />
            </label>

            <label style={labelStyle}>
              Tedarik süresi (gün)
              <input
                type="number"
                min="0"
                max={MAX_LEAD_TIME_DAYS}
                step="1"
                value={leadTime}
                onChange={(event) =>
                  setLeadTime(event.target.value)
                }
                disabled={savingSupplier}
                placeholder="Örn. 5"
                style={inputStyle}
              />
              <span style={hintStyle}>
                Sipariş ile teslimat arasındaki ortalama gün
                sayısı.
              </span>
            </label>

            {supplierError && (
              <ErrorBanner>{supplierError}</ErrorBanner>
            )}
          </Modal>
        </form>
      )}
    </>
  )
}
