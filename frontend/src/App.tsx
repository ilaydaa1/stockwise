import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'

import { AuthProvider, useAuth } from './contexts/AuthContext'
import { BusinessProvider, useBusiness } from './contexts/BusinessContext'

import AppLayout from './components/AppLayout'

import Home from './pages/Home'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Products from './pages/Products'
import StockMovements from './pages/StockMovements'
import Onboarding from './pages/Onboarding'


function AuthLoading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="w-8 h-8 border-4 border-blue-800 border-t-transparent rounded-full animate-spin mx-auto mb-4" />

        <p className="text-gray-600">
          Yükleniyor...
        </p>
      </div>
    </div>
  )
}


function ProtectedRoute({
  children,
}: {
  children: React.ReactNode
}) {
  const { user, loading } = useAuth()

  if (loading) {
    return <AuthLoading />
  }

  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
      />
    )
  }

  return <>{children}</>
}


function GuestRoute({
  children,
}: {
  children: React.ReactNode
}) {
  const { user, loading } = useAuth()

  if (loading) {
    return <AuthLoading />
  }

  if (user) {
    return (
      <Navigate
        to="/app"
        replace
      />
    )
  }

  return <>{children}</>
}


function BusinessGuard({
  children,
}: {
  children: React.ReactNode
}) {
  const {
    business,
    loading,
    error,
  } = useBusiness()

  const {
    user,
    loading: authLoading,
  } = useAuth()

  if (authLoading || loading) {
    return <AuthLoading />
  }

  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
      />
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md">
          <p className="text-gray-600 mb-4">
            İşletme bilgileri yüklenemedi.
          </p>

          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-blue-800 text-white rounded-lg hover:bg-blue-900 transition-colors font-medium"
          >
            Tekrar Dene
          </button>
        </div>
      </div>
    )
  }

  if (!business) {
    return (
      <Navigate
        to="/onboarding"
        replace
      />
    )
  }

  return <>{children}</>
}


function OnboardingGuard({
  children,
}: {
  children: React.ReactNode
}) {
  const {
    business,
    loading,
    error,
  } = useBusiness()

  const {
    user,
    loading: authLoading,
  } = useAuth()

  if (authLoading || loading) {
    return <AuthLoading />
  }

  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
      />
    )
  }

  if (error) {
    return <>{children}</>
  }

  if (business) {
    return (
      <Navigate
        to="/app"
        replace
      />
    )
  }

  return <>{children}</>
}


function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/"
        element={<Home />}
      />

      <Route
        path="/login"
        element={
          <GuestRoute>
            <Login />
          </GuestRoute>
        }
      />

      <Route
        path="/register"
        element={
          <GuestRoute>
            <Register />
          </GuestRoute>
        }
      />

      <Route
        path="/onboarding"
        element={
          <ProtectedRoute>
            <OnboardingGuard>
              <Onboarding />
            </OnboardingGuard>
          </ProtectedRoute>
        }
      />

      <Route
        path="/app"
        element={
          <ProtectedRoute>
            <BusinessGuard>
              <AppLayout />
            </BusinessGuard>
          </ProtectedRoute>
        }
      >
        <Route
          index
          element={<Dashboard />}
        />

        <Route
          path="products"
          element={<Products />}
        />

        <Route
          path="stock-movements"
          element={<StockMovements />}
        />
      </Route>

      <Route
        path="*"
        element={
          <Navigate
            to="/"
            replace
          />
        }
      />
    </Routes>
  )
}


function App() {
  return (
    <AuthProvider>
      <BusinessProvider>
        <AppRoutes />
      </BusinessProvider>
    </AuthProvider>
  )
}


export default App