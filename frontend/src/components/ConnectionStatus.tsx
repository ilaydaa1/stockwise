import React, { useState, useEffect } from 'react'
import { getHealth, getReady } from '../lib/api'

type Status = 'checking' | 'connected' | 'error'

export default function ConnectionStatus() {
  const [backendStatus, setBackendStatus] = useState<Status>('checking')
  const [dbStatus, setDbStatus] = useState<Status>('checking')
  const [backendMessage, setBackendMessage] = useState('')
  const [dbMessage, setDbMessage] = useState('')

  const checkConnection = async () => {
    setBackendStatus('checking')
    setDbStatus('checking')
    setBackendMessage('Yoxlanır...')
    setDbMessage('Yoxlanır...')

    const health = await getHealth()
    if (health.data?.status === 'ok') {
      setBackendStatus('connected')
      setBackendMessage('Backend bağlı')
    } else {
      setBackendStatus('error')
      setBackendMessage(health.error || 'Backend bağlı deyil')
    }

    const ready = await getReady()
    if (ready.data?.status === 'ready') {
      setDbStatus('connected')
      setDbMessage('Veritabanı bağlı')
    } else {
      setDbStatus('error')
      setDbMessage(ready.error || 'Veritabanı bağlı deyil')
    }
  }

  useEffect(() => {
    checkConnection()
  }, [])

  return (
    <div className="mt-8 space-y-4">
      <div className="flex items-center gap-3 p-4 bg-white rounded-lg shadow">
        <span className={`w-3 h-3 rounded-full ${backendStatus === 'connected' ? 'bg-green-500' : backendStatus === 'error' ? 'bg-red-500' : 'bg-yellow-500 animate-pulse'}`} />
        <div>
          <p className="font-semibold text-gray-800">Backend</p>
          <p className="text-sm text-gray-600">{backendMessage}</p>
        </div>
      </div>
      <div className="flex items-center gap-3 p-4 bg-white rounded-lg shadow">
        <span className={`w-3 h-3 rounded-full ${dbStatus === 'connected' ? 'bg-green-500' : dbStatus === 'error' ? 'bg-red-500' : 'bg-yellow-500 animate-pulse'}`} />
        <div>
          <p className="font-semibold text-gray-800">Veritabanı</p>
          <p className="text-sm text-gray-600">{dbMessage}</p>
        </div>
      </div>
      <button
        onClick={checkConnection}
        className="mt-4 w-full py-3 px-4 bg-blue-800 text-white rounded-lg hover:bg-blue-900 transition-colors font-medium"
      >
        Yeniden dene
      </button>
    </div>
  )
}
