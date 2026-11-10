import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { createBusiness, getMyBusiness } from '../lib/api'
import { useBusiness } from '../contexts/BusinessContext'

import './onboarding.css'

export default function Onboarding() {
  const navigate = useNavigate()
  const { setBusiness } = useBusiness()

  const [name, setName] = useState('')
  const [currency, setCurrency] = useState('TRY')
  const [timezone, setTimezone] = useState('Europe/Istanbul')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (
    event: React.FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault()

    if (loading) {
      return
    }

    const cleanName = name.trim()

    if (cleanName.length < 2) {
      setError('İşletme adı en az 2 karakter olmalıdır.')
      return
    }

    setError('')
    setLoading(true)

    try {
      const result = await createBusiness({
        name: cleanName,
        currency,
        timezone,
      })

      if (result.error) {
        if (result.status === 409) {
          const meResult = await getMyBusiness()

          if (meResult.data) {
            setBusiness(meResult.data)
            navigate('/app', { replace: true })
            return
          }
        }

        const message =
          typeof result.error === 'string'
            ? result.error
            : 'İşletme oluşturulamadı. Lütfen bilgilerinizi kontrol edin.'

        setError(message)
        return
      }

      if (result.data) {
        setBusiness(result.data)
        navigate('/app', { replace: true })
        return
      }

      setError('İşletme oluşturulurken beklenmeyen bir hata oluştu.')
    } catch {
      setError('Bir hata oluştu. Lütfen tekrar deneyin.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="sw-onboarding-page">
      <header className="sw-onboarding-header">
        <div className="sw-onboarding-header-inner">
          <Link
            to="/"
            className="sw-onboarding-logo"
            aria-label="StockWise ana sayfa"
          >
            <span
              className="sw-onboarding-logo-mark"
              aria-hidden="true"
            >
              <span />
              <span />
              <span />
            </span>

            <span className="sw-onboarding-logo-text">
              Stock<span>Wise</span>
            </span>
          </Link>
        </div>
      </header>

      <main className="sw-onboarding-main">
        <div className="sw-onboarding-progress">
          <div className="sw-onboarding-progress-item completed">
            <div className="sw-onboarding-progress-circle">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="m6 12 4 4 8-8"
                  stroke="currentColor"
                  strokeWidth="2.4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>

            <span>Hesap oluşturuldu</span>
          </div>

          <div className="sw-onboarding-progress-line completed" />

          <div className="sw-onboarding-progress-item active">
            <div className="sw-onboarding-progress-circle">
              2
            </div>

            <span>İşletmeni oluştur</span>
          </div>

          <div className="sw-onboarding-progress-line" />

          <div className="sw-onboarding-progress-item">
            <div className="sw-onboarding-progress-circle">
              3
            </div>

            <span>Başla</span>
          </div>
        </div>

        <div className="sw-onboarding-heading">
          <h1>İşletmeni oluşturalım</h1>

          <p>
            Satışlarını ve stoklarını yönetmeye başlamak için
            işletme bilgilerini ekle. Bu bilgileri daha sonra
            değiştirebilirsin.
          </p>
        </div>

        <section className="sw-onboarding-card">
          <div className="sw-onboarding-card-heading">
            <div
              className="sw-onboarding-business-icon"
              aria-hidden="true"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
              >
                <path
                  d="M4 21V8l8-4v17M12 10h8v11M8 9v2M8 14v2M16 13v2M16 18v2M2 21h20"
                  stroke="currentColor"
                  strokeWidth="1.7"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>

            <div>
              <h2>İşletme bilgileri</h2>

              <p>
                StockWise'ı işletmene göre hazırlamak için
                temel bilgilerini gir.
              </p>
            </div>
          </div>

          {error && (
            <div
              className="sw-onboarding-error"
              role="alert"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden="true"
              >
                <circle
                  cx="12"
                  cy="12"
                  r="9"
                  stroke="currentColor"
                  strokeWidth="1.8"
                />

                <path
                  d="M12 7.5v5M12 16.5h.01"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>

              <span>{error}</span>
            </div>
          )}

          <form
            className="sw-onboarding-form"
            onSubmit={handleSubmit}
          >
            <div className="sw-onboarding-field">
              <label htmlFor="businessName">
                İşletme adı
                <span aria-hidden="true">*</span>
              </label>

              <div className="sw-onboarding-control">
                <span
                  className="sw-onboarding-control-icon"
                  aria-hidden="true"
                >
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <path
                      d="M4 21V8l8-4v17M12 10h8v11M8 9v2M8 14v2M16 13v2M16 18v2M2 21h20"
                      stroke="currentColor"
                      strokeWidth="1.7"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>

                <input
                  id="businessName"
                  name="businessName"
                  type="text"
                  value={name}
                  onChange={(event) =>
                    setName(event.target.value)
                  }
                  required
                  minLength={2}
                  maxLength={100}
                  autoComplete="organization"
                  placeholder="Örn. Karahan Kırtasiye"
                  disabled={loading}
                />
              </div>

              <p className="sw-onboarding-help">
                İşletmenin adı raporlarında ve kayıtlarında
                kullanılacak.
              </p>
            </div>

            <div className="sw-onboarding-grid">
              <div className="sw-onboarding-field">
                <label htmlFor="currency">
                  Para birimi
                </label>

                <div className="sw-onboarding-control">
                  <span
                    className="sw-onboarding-control-icon"
                    aria-hidden="true"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                    >
                      <rect
                        x="3"
                        y="6"
                        width="18"
                        height="13"
                        rx="2"
                        stroke="currentColor"
                        strokeWidth="1.7"
                      />

                      <path
                        d="M3 10h18M16 15h2"
                        stroke="currentColor"
                        strokeWidth="1.7"
                        strokeLinecap="round"
                      />
                    </svg>
                  </span>

                  <select
                    id="currency"
                    value={currency}
                    onChange={(event) =>
                      setCurrency(event.target.value)
                    }
                    disabled={loading}
                  >
                    <option value="TRY">
                      TRY — Türk Lirası
                    </option>

                    <option value="USD">
                      USD — ABD Doları
                    </option>

                    <option value="EUR">
                      EUR — Euro
                    </option>
                  </select>
                </div>

                <p className="sw-onboarding-help">
                  Ürün ve satışlarda kullanılacak para birimi.
                </p>
              </div>

              <div className="sw-onboarding-field">
                <label htmlFor="timezone">
                  Saat dilimi
                </label>

                <div className="sw-onboarding-control">
                  <span
                    className="sw-onboarding-control-icon"
                    aria-hidden="true"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                    >
                      <circle
                        cx="12"
                        cy="12"
                        r="9"
                        stroke="currentColor"
                        strokeWidth="1.7"
                      />

                      <path
                        d="M12 7v5l3 2"
                        stroke="currentColor"
                        strokeWidth="1.7"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </span>

                  <select
                    id="timezone"
                    value={timezone}
                    onChange={(event) =>
                      setTimezone(event.target.value)
                    }
                    disabled={loading}
                  >
                    <option value="Europe/Istanbul">
                      Europe/Istanbul — İstanbul
                    </option>

                    <option value="Europe/London">
                      Europe/London — Londra
                    </option>

                    <option value="Europe/Berlin">
                      Europe/Berlin — Berlin
                    </option>

                    <option value="America/New_York">
                      America/New_York — New York
                    </option>

                    <option value="UTC">
                      UTC — UTC
                    </option>
                  </select>
                </div>

                <p className="sw-onboarding-help">
                  Raporlarının ve kayıtlarının saat dilimi.
                </p>
              </div>
            </div>

            <button
              type="submit"
              className="sw-onboarding-submit"
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="sw-onboarding-spinner" />
                  İşletme oluşturuluyor...
                </>
              ) : (
                <>
                  İşletmemi Oluştur

                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    aria-hidden="true"
                  >
                    <path
                      d="M5 12h14M14 7l5 5-5 5"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </>
              )}
            </button>

            <div className="sw-onboarding-note">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden="true"
              >
                <circle
                  cx="12"
                  cy="12"
                  r="9"
                  stroke="currentColor"
                  strokeWidth="1.8"
                />

                <path
                  d="M12 11v5M12 8h.01"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>

              <span>
                Bu bilgileri daha sonra İşletme Ayarları'ndan
                değiştirebilirsin.
              </span>
            </div>
          </form>
        </section>
      </main>

      <footer className="sw-onboarding-footer">
        <div className="sw-onboarding-footer-inner">
          <span>© 2026 StockWise. Tüm hakları saklıdır.</span>

          <div>
            <span>Gizlilik Politikası</span>
            <span>Kullanım Koşulları</span>
            <span>Destek</span>
          </div>
        </div>
      </footer>
    </div>
  )
}