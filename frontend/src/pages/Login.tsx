import React, { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../contexts/AuthContext'
import { loginUser, registerUser } from '../lib/api'

import './login.css'

type AuthMode = 'login' | 'register'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const { setUser } = useAuth()

  const [mode, setMode] = useState<AuthMode>('login')

  // Login
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)

  // Register
  const [name, setName] = useState('')
  const [registerEmail, setRegisterEmail] = useState('')
  const [registerPassword, setRegisterPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')

  // Password visibility
  const [showPassword, setShowPassword] = useState(false)
  const [showRegisterPassword, setShowRegisterPassword] = useState(false)
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false)

  // Feedback
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState(
    (location.state as { message?: string } | null)?.message ?? ''
  )
  const [loading, setLoading] = useState(false)

  const switchMode = (newMode: AuthMode) => {
    setMode(newMode)
    setError('')
    setSuccessMessage('')

    setShowPassword(false)
    setShowRegisterPassword(false)
    setShowPasswordConfirm(false)
  }

  const handleLogin = async (
    event: React.FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault()

    if (loading) {
      return
    }

    setError('')
    setSuccessMessage('')
    setLoading(true)

    try {
      const result = await loginUser({
        email: email.trim(),
        password,
        remember_me: rememberMe,
      })

      if (result.error) {
        setError(
          typeof result.error === 'string'
            ? result.error
            : 'Giriş yapılamadı. Lütfen bilgilerinizi kontrol edin.'
        )
        return
      }

      if (!result.data) {
        setError('Giriş sırasında beklenmeyen bir hata oluştu.')
        return
      }

      setUser(result.data)

      navigate('/app', {
        replace: true,
      })
    } catch {
      setError('Sunucuya bağlanılamadı. Lütfen tekrar deneyin.')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (
    event: React.FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault()

    if (loading) {
      return
    }

    setError('')
    setSuccessMessage('')

    const cleanName = name.trim()
    const cleanEmail = registerEmail.trim()

    if (!cleanName) {
      setError('İsim boş olamaz.')
      return
    }

    if (registerPassword !== passwordConfirm) {
      setError('Şifreler eşleşmiyor.')
      return
    }

    if (registerPassword.length < 12) {
      setError('Şifre en az 12 karakter olmalıdır.')
      return
    }

    setLoading(true)

    try {
      const result = await registerUser({
        name: cleanName,
        email: cleanEmail,
        password: registerPassword,
        password_confirm: passwordConfirm,
      })

      if (result.error) {
        setError(
          typeof result.error === 'string'
            ? result.error
            : 'Kayıt oluşturulamadı. Lütfen bilgilerinizi kontrol edin.'
        )
        return
      }

      setEmail(cleanEmail)
      setPassword('')
      setRememberMe(false)

      setName('')
      setRegisterEmail('')
      setRegisterPassword('')
      setPasswordConfirm('')

      setMode('login')
      setSuccessMessage(
        'Hesabın başarıyla oluşturuldu. Şimdi giriş yapabilirsin.'
      )
    } catch {
      setError('Bir hata oluştu. Lütfen tekrar deneyin.')
    } finally {
      setLoading(false)
    }
  }

  const PasswordEyeIcon = ({
    visible,
  }: {
    visible: boolean
  }) => {
    if (visible) {
      return (
        <svg
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          <path
            d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"
            stroke="currentColor"
            strokeWidth="1.8"
          />

          <circle
            cx="12"
            cy="12"
            r="2.5"
            stroke="currentColor"
            strokeWidth="1.8"
          />
        </svg>
      )
    }

    return (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden="true"
      >
        <path
          d="m3 3 18 18"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />

        <path
          d="M10.7 6.1A9.7 9.7 0 0 1 12 6c6 0 9.5 6 9.5 6a15 15 0 0 1-2.7 3.4M6.2 6.2C3.8 8 2.5 12 2.5 12s3.5 6 9.5 6c1.3 0 2.5-.3 3.5-.7"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />

        <path
          d="M9.8 9.8A3.1 3.1 0 0 0 9 12a3 3 0 0 0 5.2 2.1"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
      </svg>
    )
  }

  return (
    <main className="sw-login-page">
      <section className="sw-login-brand-panel">
        <div className="sw-login-brand-glow" />

        <div className="sw-login-brand-inner">
          <div>
            <Link
              to="/"
              className="sw-login-logo"
              aria-label="StockWise ana sayfa"
            >
              <span
                className="sw-login-logo-bars"
                aria-hidden="true"
              >
                <span className="sw-login-logo-bar sw-login-logo-bar-1" />
                <span className="sw-login-logo-bar sw-login-logo-bar-2" />
                <span className="sw-login-logo-bar sw-login-logo-bar-3" />
              </span>

              <span className="sw-login-logo-name">
                Stock<span>Wise</span>
              </span>
            </Link>

            <p className="sw-login-logo-subtitle">
              Stoklarını akıllıca yönet
            </p>
          </div>

          <div className="sw-login-brand-message">
            <h1>
              İşletmen için
              <br />
              daha fazlası,
              <br />
              <span>daha az karmaşa.</span>
            </h1>

            <p>
              StockWise ile ürünlerini, stoklarını ve
              satışlarını tek yerden yönet. İşine odaklan,
              gerisini StockWise halletsin.
            </p>
          </div>

          <div className="sw-login-feature-list">
            <div className="sw-login-feature">
              <div className="sw-login-feature-icon">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  aria-hidden="true"
                >
                  <path
                    d="M4 7.5 12 3l8 4.5v9L12 21l-8-4.5v-9Z"
                    stroke="currentColor"
                    strokeWidth="1.7"
                    strokeLinejoin="round"
                  />
                  <path
                    d="m4.5 7.5 7.5 4.3 7.5-4.3M12 11.8V21"
                    stroke="currentColor"
                    strokeWidth="1.7"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>

              <div>
                <h2>Stok Takibi</h2>
                <p>Ürünlerini anlık olarak takip et.</p>
              </div>
            </div>

            <div className="sw-login-feature">
              <div className="sw-login-feature-icon">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  aria-hidden="true"
                >
                  <path
                    d="M5 19v-5M12 19V9M19 19V4"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                </svg>
              </div>

              <div>
                <h2>Satış Yönetimi</h2>
                <p>Satışlarını kolayca kaydet ve analiz et.</p>
              </div>
            </div>

            <div className="sw-login-feature">
              <div className="sw-login-feature-icon">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  aria-hidden="true"
                >
                  <path
                    d="m4 17 5-5 4 3 7-8"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />

                  <path
                    d="M16 7h4v4"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>

              <div>
                <h2>Detaylı Raporlar</h2>
                <p>İşletmenin performansını keşfet.</p>
              </div>
            </div>

            <div className="sw-login-feature">
              <div className="sw-login-feature-icon">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  aria-hidden="true"
                >
                  <path
                    d="M12 3 19 6v5c0 4.7-2.8 8-7 10-4.2-2-7-5.3-7-10V6l7-3Z"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinejoin="round"
                  />

                  <path
                    d="m9 12 2 2 4-4"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>

              <div>
                <h2>Güvenli ve Seninle</h2>
                <p>Verilerin her zaman güvende.</p>
              </div>
            </div>
          </div>

          <div
            className="sw-login-chart"
            aria-hidden="true"
          >
            <svg
              viewBox="0 0 620 220"
              preserveAspectRatio="none"
            >
              <defs>
                <linearGradient
                  id="sw-login-chart-fill"
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop
                    offset="0%"
                    stopColor="#4386ff"
                    stopOpacity="0.25"
                  />

                  <stop
                    offset="100%"
                    stopColor="#4386ff"
                    stopOpacity="0"
                  />
                </linearGradient>
              </defs>

              <path
                className="sw-login-chart-fill"
                d="
                  M0 195
                  C55 175 70 145 115 155
                  C150 164 168 194 205 175
                  C240 157 250 111 285 122
                  C315 132 327 158 355 125
                  C385 89 397 37 427 67
                  C448 88 458 126 484 84
                  C510 43 532 20 553 55
                  C578 94 590 63 620 20
                  L620 220
                  L0 220
                  Z
                "
              />

              <path
                className="sw-login-chart-line"
                d="
                  M0 195
                  C55 175 70 145 115 155
                  C150 164 168 194 205 175
                  C240 157 250 111 285 122
                  C315 132 327 158 355 125
                  C385 89 397 37 427 67
                  C448 88 458 126 484 84
                  C510 43 532 20 553 55
                  C578 94 590 63 620 20
                "
              />
            </svg>
          </div>

          <blockquote className="sw-login-quote">
            “Daha organize bir işletme,
            <br />
            daha güçlü bir gelecek.”
          </blockquote>
        </div>
      </section>

      <section className="sw-login-form-side">
        <div className="sw-login-mobile-logo">
          <Link
            to="/"
            className="sw-login-logo"
          >
            <span
              className="sw-login-logo-bars"
              aria-hidden="true"
            >
              <span className="sw-login-logo-bar sw-login-logo-bar-1" />
              <span className="sw-login-logo-bar sw-login-logo-bar-2" />
              <span className="sw-login-logo-bar sw-login-logo-bar-3" />
            </span>

            <span className="sw-login-logo-name">
              Stock<span>Wise</span>
            </span>
          </Link>
        </div>

        <div className="sw-login-card">
          {mode === 'login' ? (
            <>
              <div className="sw-login-card-header">
                <h2>Hesabına giriş yap</h2>
                <p>StockWise’a tekrar hoş geldin.</p>
              </div>

              {successMessage && (
                <div
                  className="sw-login-alert sw-login-alert-success"
                  role="status"
                >
                  {successMessage}
                </div>
              )}

              {error && (
                <div
                  className="sw-login-alert sw-login-alert-error"
                  role="alert"
                >
                  {error}
                </div>
              )}

              <form
                onSubmit={handleLogin}
                className="sw-login-form"
              >
                <div className="sw-login-field">
                  <label htmlFor="login-email">
                    E-posta adresi
                  </label>

                  <div className="sw-login-input-wrapper">
                    <span
                      className="sw-login-input-icon"
                      aria-hidden="true"
                    >
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                      >
                        <rect
                          x="3"
                          y="5"
                          width="18"
                          height="14"
                          rx="2"
                          stroke="currentColor"
                          strokeWidth="1.8"
                        />

                        <path
                          d="m4 7 8 6 8-6"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </span>

                    <input
                      id="login-email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(event) =>
                        setEmail(event.target.value)
                      }
                      placeholder="ornek@eposta.com"
                      required
                      disabled={loading}
                    />
                  </div>
                </div>

                <div className="sw-login-field">
                  <label htmlFor="login-password">
                    Şifre
                  </label>

                  <div className="sw-login-input-wrapper">
                    <span
                      className="sw-login-input-icon"
                      aria-hidden="true"
                    >
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                      >
                        <rect
                          x="5"
                          y="10"
                          width="14"
                          height="10"
                          rx="2"
                          stroke="currentColor"
                          strokeWidth="1.8"
                        />

                        <path
                          d="M8 10V7a4 4 0 0 1 8 0v3"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                        />
                      </svg>
                    </span>

                    <input
                      id="login-password"
                      name="password"
                      type={
                        showPassword
                          ? 'text'
                          : 'password'
                      }
                      autoComplete="current-password"
                      value={password}
                      onChange={(event) =>
                        setPassword(event.target.value)
                      }
                      placeholder="Şifrenizi girin"
                      required
                      disabled={loading}
                    />

                    <button
                      type="button"
                      className="sw-login-password-toggle"
                      onClick={() =>
                        setShowPassword(
                          (current) => !current
                        )
                      }
                      aria-label={
                        showPassword
                          ? 'Şifreyi gizle'
                          : 'Şifreyi göster'
                      }
                    >
                      <PasswordEyeIcon
                        visible={showPassword}
                      />
                    </button>
                  </div>
                </div>

                <div className="sw-login-options">
                  <label className="sw-login-remember">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(event) =>
                        setRememberMe(
                          event.target.checked
                        )
                      }
                      disabled={loading}
                    />

                    <span className="sw-login-custom-checkbox">
                      <svg
                        viewBox="0 0 16 16"
                        fill="none"
                        aria-hidden="true"
                      >
                        <path
                          d="m3.5 8 3 3 6-6"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </span>

                    <span>Beni hatırla</span>
                  </label>

                  <span
                    className="sw-login-forgot sw-login-forgot-disabled"
                    title="Şifre sıfırlama özelliği yakında eklenecek"
                  >
                    Şifremi unuttum?
                  </span>
                </div>

                <button
                  type="submit"
                  className="sw-login-submit"
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <span className="sw-login-spinner" />
                      Giriş yapılıyor...
                    </>
                  ) : (
                    <>
                      Giriş yap

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
              </form>

              <div className="sw-login-divider">
                <span />
                <p>Henüz hesabın yok mu?</p>
                <span />
              </div>

              <button
                type="button"
                className="sw-login-register"
                onClick={() => switchMode('register')}
              >
                Hemen kayıt ol
              </button>
            </>
          ) : (
            <>
              <div className="sw-login-card-header">
                <h2>Hesabını oluştur</h2>
                <p>
                  StockWise ile işletmeni yönetmeye başla.
                </p>
              </div>

              {error && (
                <div
                  className="sw-login-alert sw-login-alert-error"
                  role="alert"
                >
                  {error}
                </div>
              )}

              <form
                onSubmit={handleRegister}
                className="sw-login-form"
              >
                <div className="sw-login-field">
                  <label htmlFor="register-name">
                    Ad Soyad
                  </label>

                  <div className="sw-login-input-wrapper">
                    <span
                      className="sw-login-input-icon"
                      aria-hidden="true"
                    >
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                      >
                        <circle
                          cx="12"
                          cy="8"
                          r="4"
                          stroke="currentColor"
                          strokeWidth="1.8"
                        />

                        <path
                          d="M4.5 20c.7-4 3.2-6 7.5-6s6.8 2 7.5 6"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                        />
                      </svg>
                    </span>

                    <input
                      id="register-name"
                      name="name"
                      type="text"
                      autoComplete="name"
                      value={name}
                      onChange={(event) =>
                        setName(event.target.value)
                      }
                      placeholder="Adınız Soyadınız"
                      required
                      disabled={loading}
                    />
                  </div>
                </div>

                <div className="sw-login-field">
                  <label htmlFor="register-email">
                    E-posta adresi
                  </label>

                  <div className="sw-login-input-wrapper">
                    <span
                      className="sw-login-input-icon"
                      aria-hidden="true"
                    >
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                      >
                        <rect
                          x="3"
                          y="5"
                          width="18"
                          height="14"
                          rx="2"
                          stroke="currentColor"
                          strokeWidth="1.8"
                        />

                        <path
                          d="m4 7 8 6 8-6"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </span>

                    <input
                      id="register-email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      value={registerEmail}
                      onChange={(event) =>
                        setRegisterEmail(event.target.value)
                      }
                      placeholder="ornek@eposta.com"
                      required
                      disabled={loading}
                    />
                  </div>
                </div>

                <div className="sw-login-field">
                  <label htmlFor="register-password">
                    Şifre
                  </label>

                  <div className="sw-login-input-wrapper">
                    <span
                      className="sw-login-input-icon"
                      aria-hidden="true"
                    >
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                      >
                        <rect
                          x="5"
                          y="10"
                          width="14"
                          height="10"
                          rx="2"
                          stroke="currentColor"
                          strokeWidth="1.8"
                        />

                        <path
                          d="M8 10V7a4 4 0 0 1 8 0v3"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                        />
                      </svg>
                    </span>

                    <input
                      id="register-password"
                      name="password"
                      type={
                        showRegisterPassword
                          ? 'text'
                          : 'password'
                      }
                      autoComplete="new-password"
                      value={registerPassword}
                      onChange={(event) =>
                        setRegisterPassword(
                          event.target.value
                        )
                      }
                      placeholder="En az 12 karakter"
                      required
                      minLength={12}
                      disabled={loading}
                    />

                    <button
                      type="button"
                      className="sw-login-password-toggle"
                      onClick={() =>
                        setShowRegisterPassword(
                          (current) => !current
                        )
                      }
                      aria-label={
                        showRegisterPassword
                          ? 'Şifreyi gizle'
                          : 'Şifreyi göster'
                      }
                    >
                      <PasswordEyeIcon
                        visible={showRegisterPassword}
                      />
                    </button>
                  </div>
                </div>

                <div className="sw-login-field">
                  <label htmlFor="register-password-confirm">
                    Şifre Tekrarı
                  </label>

                  <div className="sw-login-input-wrapper">
                    <span
                      className="sw-login-input-icon"
                      aria-hidden="true"
                    >
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                      >
                        <rect
                          x="5"
                          y="10"
                          width="14"
                          height="10"
                          rx="2"
                          stroke="currentColor"
                          strokeWidth="1.8"
                        />

                        <path
                          d="M8 10V7a4 4 0 0 1 8 0v3"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                        />
                      </svg>
                    </span>

                    <input
                      id="register-password-confirm"
                      name="passwordConfirm"
                      type={
                        showPasswordConfirm
                          ? 'text'
                          : 'password'
                      }
                      autoComplete="new-password"
                      value={passwordConfirm}
                      onChange={(event) =>
                        setPasswordConfirm(
                          event.target.value
                        )
                      }
                      placeholder="Şifrenizi tekrar girin"
                      required
                      minLength={12}
                      disabled={loading}
                    />

                    <button
                      type="button"
                      className="sw-login-password-toggle"
                      onClick={() =>
                        setShowPasswordConfirm(
                          (current) => !current
                        )
                      }
                      aria-label={
                        showPasswordConfirm
                          ? 'Şifreyi gizle'
                          : 'Şifreyi göster'
                      }
                    >
                      <PasswordEyeIcon
                        visible={showPasswordConfirm}
                      />
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  className="sw-login-submit"
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <span className="sw-login-spinner" />
                      Hesap oluşturuluyor...
                    </>
                  ) : (
                    <>
                      Hesap oluştur

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
              </form>

              <div className="sw-login-divider">
                <span />
                <p>Zaten hesabın var mı?</p>
                <span />
              </div>

              <button
                type="button"
                className="sw-login-register"
                onClick={() => switchMode('login')}
              >
                Giriş yap
              </button>
            </>
          )}

          <div className="sw-login-security">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden="true"
            >
              <rect
                x="6"
                y="10"
                width="12"
                height="10"
                rx="2"
                fill="currentColor"
              />

              <path
                d="M9 10V7a3 3 0 0 1 6 0v3"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>

            <span>
              Hesabın güvende. Verilerin bizim için önemli.
            </span>
          </div>
        </div>
      </section>
    </main>
  )
}