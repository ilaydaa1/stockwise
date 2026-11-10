import { useEffect, useState, type FormEvent } from 'react'

import { useBusiness } from '../contexts/BusinessContext'
import {
  createSaleReturn,
  getSales,
  type SaleRecord,
} from '../lib/api'
import {
  ErrorBanner,
  Modal,
  emptyStateStyle,
  formatDateTime,
  formatMoney,
  hintStyle,
  inputStyle,
  labelStyle,
  mutedTextStyle,
  secondaryButtonStyle,
  smallButtonStyle,
} from '../components/ui'

import './dashboard.css'


const PAGE_SIZE = 20


function describeReturnError(error: string | undefined) {
  if (error === 'RETURN_EXCEEDS_SOLD') {
    return 'İade miktarı, satılan ve henüz iade edilmemiş miktarı aşamaz. Sayfayı yenileyip tekrar deneyin.'
  }

  if (error === 'SALE_NOT_FOUND' || error === 'SALE_ITEM_NOT_FOUND') {
    return 'Satış bulunamadı. Sayfayı yenileyip tekrar deneyin.'
  }

  return error || 'İade kaydedilemedi.'
}


function remainingOf(sale: SaleRecord) {
  return sale.items.reduce(
    (sum, line) => sum + (line.quantity - line.returned_quantity),
    0
  )
}


export default function SalesHistory() {
  const { business } = useBusiness()
  const currency = business?.currency ?? 'TRY'

  const [sales, setSales] = useState<SaleRecord[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const [returning, setReturning] = useState<SaleRecord | null>(null)
  // Quantity to return per sale item id, as typed.
  const [quantities, setQuantities] = useState<Record<string, string>>({})
  const [reason, setReason] = useState('')
  const [returnError, setReturnError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const load = async (nextOffset: number) => {
    setLoading(true)
    setError(null)

    const result = await getSales(PAGE_SIZE, nextOffset)

    if (!result.data) {
      setError(result.error || 'Satışlar yüklenirken bir hata oluştu.')
      setLoading(false)
      return
    }

    setSales(result.data.items)
    setTotal(result.data.total)
    setOffset(nextOffset)
    setLoading(false)
  }

  useEffect(() => {
    load(0)
  }, [])

  const openReturn = (sale: SaleRecord) => {
    setReturning(sale)
    setQuantities({})
    setReason('')
    setReturnError(null)
    setNotice(null)
  }

  const closeReturn = () => {
    if (!saving) {
      setReturning(null)
    }
  }

  const handleReturn = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!returning) {
      return
    }

    const lines: { sale_item_id: string; quantity: number }[] = []

    for (const line of returning.items) {
      const typed = (quantities[line.id] ?? '').trim()

      if (typed === '' || typed === '0') {
        continue
      }

      const quantity = Number(typed)
      const remaining = line.quantity - line.returned_quantity

      if (
        !Number.isInteger(quantity) ||
        quantity < 0 ||
        quantity > remaining
      ) {
        setReturnError(
          `${line.product_name} için en fazla ${remaining} adet iade alınabilir.`
        )
        return
      }

      lines.push({ sale_item_id: line.id, quantity })
    }

    if (lines.length === 0) {
      setReturnError('İade edilecek en az bir ürün miktarı girin.')
      return
    }

    setSaving(true)
    setReturnError(null)

    const result = await createSaleReturn(returning.id, {
      items: lines,
      reason: reason.trim() || undefined,
    })

    setSaving(false)

    if (!result.data) {
      setReturnError(describeReturnError(result.error))
      return
    }

    const refunded = result.data.reduce(
      (sum, line) => sum + Number(line.refund_amount),
      0
    )

    setReturning(null)
    setNotice(
      `İade kaydedildi. ${formatMoney(refunded, currency)} iade edildi ve ürünler stoğa geri eklendi.`
    )
    load(offset)
  }

  const firstShown = total === 0 ? 0 : offset + 1
  const lastShown = Math.min(offset + PAGE_SIZE, total)

  return (
    <>
      <main id="sw-main" className="sw-main">
        <section className="sw-page-heading">
          <div>
            <p className="sw-eyebrow">SATIŞ YÖNETİMİ</p>

            <h1>Satış Geçmişi</h1>

            <p className="sw-subtitle">
              Tamamlanan satışları incele ve müşteri iadelerini
              kaydet.
            </p>
          </div>
        </section>

        {notice && (
          <div
            role="status"
            style={{
              marginBottom: '16px',
              padding: '12px 14px',
              borderRadius: '8px',
              background: '#effaf4',
              border: '1px solid #cdeeda',
              color: '#16805b',
              fontSize: '14px',
            }}
          >
            {notice}
          </div>
        )}

        <section className="sw-panel">
          <header className="sw-panel-heading">
            <div>
              <h2>Satışlar</h2>

              <p>En yeni satış en üstte gösterilir.</p>
            </div>

            {!loading && !error && (
              <span className="sw-count">{total} satış</span>
            )}
          </header>

          {loading && (
            <div style={emptyStateStyle}>Satışlar yükleniyor...</div>
          )}

          {!loading && error && (
            <div style={emptyStateStyle}>
              <strong style={{ color: '#172641' }}>
                Satışlar yüklenemedi
              </strong>

              <span>{error}</span>

              <button
                type="button"
                className="sw-primary-button"
                onClick={() => load(offset)}
              >
                Tekrar Dene
              </button>
            </div>
          )}

          {!loading && !error && sales.length === 0 && (
            <div style={emptyStateStyle}>
              <strong style={{ color: '#172641' }}>
                Henüz satış yok
              </strong>

              <span>
                İlk satışını tamamladığında burada görünecek.
              </span>
            </div>
          )}

          {!loading && !error && sales.length > 0 && (
            <>
              <div className="sw-table-container">
                <table className="sw-product-table">
                  <thead>
                    <tr>
                      <th scope="col">Tarih</th>
                      <th scope="col">Ürünler</th>
                      <th scope="col">Tutar</th>
                      <th scope="col">İade</th>
                      <th scope="col">Brüt Kâr</th>
                      <th scope="col">İşlemler</th>
                    </tr>
                  </thead>

                  <tbody>
                    {sales.map((sale) => {
                      const remaining = remainingOf(sale)
                      const refunded = Number(sale.refund_amount)

                      return (
                        <tr key={sale.id}>
                          <td style={{ whiteSpace: 'nowrap' }}>
                            {formatDateTime(sale.created_at)}
                          </td>

                          <td>
                            {sale.items.map((line) => (
                              <div key={line.id}>
                                <strong>{line.product_name}</strong>{' '}
                                <span style={mutedTextStyle}>
                                  × {line.quantity}
                                  {line.returned_quantity > 0 &&
                                    ` (${line.returned_quantity} iade)`}
                                </span>
                              </div>
                            ))}
                          </td>

                          <td>
                            {formatMoney(sale.total_amount, currency)}
                          </td>

                          <td>
                            {refunded > 0 ? (
                              <span style={{ color: '#c44747' }}>
                                −{formatMoney(refunded, currency)}
                              </span>
                            ) : (
                              <span style={mutedTextStyle}>—</span>
                            )}
                          </td>

                          <td>
                            {formatMoney(sale.gross_profit, currency)}
                          </td>

                          <td>
                            {remaining > 0 ? (
                              <button
                                type="button"
                                style={smallButtonStyle}
                                onClick={() => openReturn(sale)}
                              >
                                İade Al
                              </button>
                            ) : (
                              <span style={mutedTextStyle}>
                                Tamamı iade edildi
                              </span>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>

              <div
                style={{
                  padding: '14px 20px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '12px',
                  flexWrap: 'wrap',
                }}
              >
                <span style={{ ...mutedTextStyle, fontSize: '13px' }}>
                  {firstShown}–{lastShown} / {total}
                </span>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    type="button"
                    style={{
                      ...secondaryButtonStyle,
                      opacity: offset === 0 ? 0.5 : 1,
                    }}
                    disabled={offset === 0}
                    onClick={() =>
                      load(Math.max(0, offset - PAGE_SIZE))
                    }
                  >
                    Önceki
                  </button>

                  <button
                    type="button"
                    style={{
                      ...secondaryButtonStyle,
                      opacity: lastShown >= total ? 0.5 : 1,
                    }}
                    disabled={lastShown >= total}
                    onClick={() => load(offset + PAGE_SIZE)}
                  >
                    Sonraki
                  </button>
                </div>
              </div>
            </>
          )}
        </section>
      </main>

      {returning && (
        <form onSubmit={handleReturn}>
          <Modal
            title="İade Al"
            subtitle={`${formatDateTime(returning.created_at)} tarihli satış`}
            onClose={closeReturn}
            footer={
              <>
                <button
                  type="button"
                  onClick={closeReturn}
                  disabled={saving}
                  style={secondaryButtonStyle}
                >
                  Vazgeç
                </button>

                <button
                  type="submit"
                  className="sw-primary-button"
                  disabled={saving}
                >
                  {saving ? 'Kaydediliyor...' : 'İadeyi Kaydet'}
                </button>
              </>
            }
          >
            <div style={{ display: 'grid', gap: '12px' }}>
              {returning.items.map((line) => {
                const remaining =
                  line.quantity - line.returned_quantity

                return (
                  <div
                    key={line.id}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'minmax(0, 1fr) 110px',
                      gap: '12px',
                      alignItems: 'center',
                    }}
                  >
                    <div>
                      <strong style={{ color: '#172641' }}>
                        {line.product_name}
                      </strong>

                      <div style={hintStyle}>
                        {line.quantity} adet satıldı ·{' '}
                        {formatMoney(line.unit_sale_price, currency)}{' '}
                        birim fiyat ·{' '}
                        {remaining > 0
                          ? `${remaining} adet iade alınabilir`
                          : 'tamamı iade edildi'}
                      </div>
                    </div>

                    <input
                      type="number"
                      min="0"
                      max={remaining}
                      step="1"
                      value={quantities[line.id] ?? ''}
                      onChange={(event) =>
                        setQuantities((current) => ({
                          ...current,
                          [line.id]: event.target.value,
                        }))
                      }
                      disabled={saving || remaining === 0}
                      placeholder="0"
                      aria-label={`${line.product_name} iade miktarı`}
                      style={inputStyle}
                    />
                  </div>
                )
              })}
            </div>

            <label style={labelStyle}>
              İade nedeni (isteğe bağlı)
              <input
                type="text"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                maxLength={255}
                disabled={saving}
                placeholder="Örn. Hasarlı ürün"
                style={inputStyle}
              />
            </label>

            <span style={hintStyle}>
              İade tutarı satış anındaki fiyat üzerinden hesaplanır.
              İade edilen ürünler stoğa geri eklenir; orijinal satış
              kaydı değişmez.
            </span>

            {returnError && <ErrorBanner>{returnError}</ErrorBanner>}
          </Modal>
        </form>
      )}
    </>
  )
}
