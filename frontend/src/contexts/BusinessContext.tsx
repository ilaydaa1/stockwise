import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
import { getMyBusiness, type Business } from '../lib/api'
import { useAuth } from './AuthContext'

interface BusinessContextType {
  business: Business | null
  loading: boolean
  error: boolean
  setBusiness: (business: Business | null) => void
  refetch: () => Promise<void>
}

const BusinessContext = createContext<BusinessContextType>({
  business: null,
  loading: true,
  error: false,
  setBusiness: () => {},
  refetch: async () => {},
})

export function BusinessProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  const [business, setBusiness] = useState<Business | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const prevUserIdRef = useRef<string | null>(null)

  const fetchBusiness = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const result = await getMyBusiness()
      if (result.data) {
        setBusiness(result.data)
      } else if (result.status === 404) {
        setBusiness(null)
      } else {
        setError(true)
      }
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const currentUserId = user?.id ?? null
    if (currentUserId !== prevUserIdRef.current) {
      prevUserIdRef.current = currentUserId
      setBusiness(null)
      setError(false)
      if (currentUserId) {
        fetchBusiness()
      } else {
        setLoading(false)
      }
    }
  }, [user, fetchBusiness])

  return (
    <BusinessContext.Provider value={{ business, loading, error, setBusiness, refetch: fetchBusiness }}>
      {children}
    </BusinessContext.Provider>
  )
}

export function useBusiness() {
  return useContext(BusinessContext)
}
