import React, { useState, useEffect } from 'react'
import { useNavigate, Link, useLocation } from 'react-router-dom'
import { loginUser } from '../lib/api'
import { useAuth } from '../contexts/AuthContext'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const { setUser, user } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (user) {
      navigate('/app', { replace: true })
    }
  }, [user, navigate])

  useEffect(() => {
    const msg = (location.state as { message?: string })?.message
    if (msg) {
      setSuccessMessage(msg)
      window.history.replaceState({}, '')
    }
  }, [location.state])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccessMessage('')

    setLoading(true)
    try {
      const result = await loginUser({ email, password })
      if (result.error) {
        const msg = typeof result.error === 'string' ? result.error : JSON.stringify(result.error)
        setError(msg)
        return
      }
      if (result.data) {
        setUser(result.data)
        navigate('/app')
      }
    } catch {
      setError('Bir hata oluştu. Lütfen tekrar deneyin.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="text-3xl font-bold text-blue-900">StockWise</Link>
          <p className="text-gray-600 mt-2">Hesabınıza giriş yapın</p>
        </div>
        <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-md p-8 space-y-5">
          {successMessage && (
            <div className="bg-green-50 border border-green-300 text-green-700 rounded-lg p-3 text-sm">
              {successMessage}
            </div>
          )}
          {error && (
            <div className="bg-red-50 border border-red-300 text-red-700 rounded-lg p-3 text-sm">
              {error}
            </div>
          )}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              E-posta
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors"
              placeholder="ornek@email.com"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Şifre
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors"
              placeholder="Şifrenizi girin"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 bg-blue-800 text-white rounded-lg hover:bg-blue-900 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Giriş yapılıyor...' : 'Giriş Yap'}
          </button>
          <p className="text-center text-sm text-gray-600">
            Hesabınız yok mu?{' '}
            <Link to="/register" className="text-blue-800 hover:underline font-medium">
              Kayıt Olun
            </Link>
          </p>
        </form>
      </div>
    </div>
  )
}
