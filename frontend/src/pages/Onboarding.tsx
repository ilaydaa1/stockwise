import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { createBusiness, getMyBusiness } from '../lib/api'
import { useBusiness } from '../contexts/BusinessContext'
import { useAuth } from '../contexts/AuthContext'
import { logoutUser } from '../lib/api'

export default function Onboarding() {
  const navigate = useNavigate()
  const { setBusiness } = useBusiness()
  const { setUser } = useAuth()
  const [name, setName] = useState('')
  const [currency, setCurrency] = useState('TRY')
  const [timezone, setTimezone] = useState('Europe/Istanbul')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogout = async () => {
    try {
      await logoutUser()
    } finally {
      setUser(null)
      setBusiness(null)
      navigate('/login')
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const result = await createBusiness({ name, currency, timezone })
      if (result.error) {
        if (result.status === 409) {
          const meResult = await getMyBusiness()
          if (meResult.data) {
            setBusiness(meResult.data)
            navigate('/app')
            return
          }
        }
        const msg = typeof result.error === 'string' ? result.error : JSON.stringify(result.error)
        setError(msg)
        return
      }
      if (result.data) {
        setBusiness(result.data)
        navigate('/app')
      }
    } catch {
      setError('Bir hata oluştu. Lütfen tekrar deneyin.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-blue-900">StockWise</Link>
          <button
            onClick={handleLogout}
            className="px-4 py-2 text-sm text-red-700 bg-red-50 rounded-lg hover:bg-red-100 transition-colors font-medium"
          >
            Çıkış Yap
          </button>
        </div>
      </header>
      <main className="max-w-lg mx-auto px-4 py-12">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">İşletmeni oluştur</h1>
          <p className="text-gray-600">
            Satışlarını ve stoklarını yönetmeye başlamak için işletme bilgilerini ekle.
          </p>
        </div>
        <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-md p-8 space-y-5">
          {error && (
            <div className="bg-red-50 border border-red-300 text-red-700 rounded-lg p-3 text-sm">
              {error}
            </div>
          )}
          <div>
            <label htmlFor="businessName" className="block text-sm font-medium text-gray-700 mb-1">
              İşletme adı
            </label>
            <input
              id="businessName"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              minLength={2}
              maxLength={100}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors"
              placeholder="İşletme adınızı girin"
            />
          </div>
          <div>
            <label htmlFor="currency" className="block text-sm font-medium text-gray-700 mb-1">
              Para birimi
            </label>
            <select
              id="currency"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors bg-white"
            >
              <option value="TRY">TRY — Türk Lirası</option>
              <option value="USD">USD — ABD Doları</option>
              <option value="EUR">EUR — Euro</option>
            </select>
          </div>
          <div>
            <label htmlFor="timezone" className="block text-sm font-medium text-gray-700 mb-1">
              Saat dilimi
            </label>
            <select
              id="timezone"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors bg-white"
            >
              <option value="Europe/Istanbul">Europe/Istanbul — İstanbul</option>
              <option value="Europe/London">Europe/London — Londra</option>
              <option value="Europe/Berlin">Europe/Berlin — Berlin</option>
              <option value="America/New_York">America/New_York — New York</option>
              <option value="UTC">UTC — UTC</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 bg-blue-800 text-white rounded-lg hover:bg-blue-900 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Oluşturuluyor...' : 'İşletme Oluştur'}
          </button>
        </form>
      </main>
    </div>
  )
}
