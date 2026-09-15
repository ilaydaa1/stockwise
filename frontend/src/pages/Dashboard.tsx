import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { logoutUser } from '../lib/api'

export default function Dashboard() {
  const { user, setUser } = useAuth()
  const navigate = useNavigate()
  const [loggingOut, setLoggingOut] = React.useState(false)

  const handleLogout = async () => {
    setLoggingOut(true)
    try {
      await logoutUser()
    } finally {
      setUser(null)
      navigate('/login')
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold text-blue-900">StockWise</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">
              Merhaba, <span className="font-medium text-gray-800">{user?.name}</span>
            </span>
            <button
              onClick={handleLogout}
              disabled={loggingOut}
              className="px-4 py-2 text-sm text-red-700 bg-red-50 rounded-lg hover:bg-red-100 transition-colors font-medium disabled:opacity-50"
            >
              {loggingOut ? 'Çıkış...' : 'Çıkış Yap'}
            </button>
          </div>
        </div>
      </header>
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow-md p-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-4">Hoş geldiniz!</h2>
          <p className="text-gray-600 text-lg">
            İşletme kurulumu sonraki adımda eklenecek.
          </p>
        </div>
      </main>
    </div>
  )
}
