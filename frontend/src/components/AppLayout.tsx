import { useState } from 'react'
import {
  NavLink,
  Outlet,
  useLocation,
  useNavigate,
} from 'react-router-dom'

import { useAuth } from '../contexts/AuthContext'
import { useBusiness } from '../contexts/BusinessContext'
import { logoutUser } from '../lib/api'

import '../pages/dashboard.css'


type IconName =
  | 'layers'
  | 'home'
  | 'box'
  | 'stock'
  | 'cart'
  | 'chart'
  | 'spark'
  | 'settings'
  | 'logout'
  | 'menu'
  | 'close'


const iconPaths: Record<IconName, string> = {
  layers:
    'M12 3 3 8l9 5 9-5-9-5ZM3 12l9 5 9-5M3 16l9 5 9-5',

  home:
    'm3 10 9-7 9 7M5 9v12h5v-7h4v7h5V9',

  box:
    'm12 3 9 5v8l-9 5-9-5V8l9-5ZM3 8l9 5 9-5M12 13v8M7.5 5.5l9 5',

  stock:
    'M4 7h15m-4-4 4 4-4 4M20 17H5m4-4-4 4 4 4',

  cart:
    'M3 3h2l3 12h10l3-9H6M9 20h.01M18 20h.01',

  chart:
    'M4 20V10h4v10M10 20V4h4v16M16 20v-7h4v7',

  spark:
    'm12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z',

  settings:
    'M9 3h6l1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1 1-3ZM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6',

  logout:
    'M9 4H4v16h5M13 8l4 4-4 4M8 12h13',

  menu:
    'M4 6h16M4 12h16M4 18h16',

  close:
    'm6 6 12 12M6 18 18 6',
}


function Icon({
  name,
  size = 20,
}: {
  name: IconName
  size?: number
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={iconPaths[name]} />
    </svg>
  )
}


interface NavigationItem {
  label: string
  icon: IconName
  path?: string
  available: boolean
}


const navigation: NavigationItem[] = [
  {
    label: 'Genel Bakış',
    icon: 'home',
    path: '/app',
    available: true,
  },
  {
    label: 'Ürünler',
    icon: 'box',
    path: '/app/products',
    available: true,
  },
  {
    label: 'Stok Hareketleri',
    icon: 'stock',
    path: '/app/stock-movements',
    available: true,
  },
  {
    label: 'Satışlar',
    icon: 'cart',
    available: false,
  },
  {
    label: 'Analizler',
    icon: 'chart',
    available: false,
  },
  {
    label: 'Karar Destek',
    icon: 'spark',
    available: false,
  },
]


function getPageName(
  pathname: string
): string {
  if (pathname === '/app/products') {
    return 'Ürünler'
  }

  if (
    pathname === '/app/stock-movements'
  ) {
    return 'Stok Hareketleri'
  }

  return 'Genel Bakış'
}


export default function AppLayout() {
  const { user, setUser } = useAuth()

  const {
    business,
    setBusiness,
  } = useBusiness()

  const navigate = useNavigate()
  const location = useLocation()

  const [menuOpen, setMenuOpen] =
    useState(false)

  const [loggingOut, setLoggingOut] =
    useState(false)


  const initials =
    user?.name
      ?.trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part[0])
      .join('')
      .toLocaleUpperCase('tr-TR') || 'SW'


  const pageName =
    getPageName(location.pathname)


  const handleLogout = async () => {
    setLoggingOut(true)

    try {
      await logoutUser()
    } finally {
      setUser(null)
      setBusiness(null)

      navigate('/login', {
        replace: true,
      })
    }
  }


  return (
    <div className="sw-dashboard">
      <a
        href="#sw-main"
        className="sw-skip-link"
      >
        Ana içeriğe geç
      </a>


      {menuOpen && (
        <button
          type="button"
          className="sw-overlay"
          aria-label="Menüyü kapat"
          onClick={() =>
            setMenuOpen(false)
          }
        />
      )}


      <aside
        id="sw-sidebar"
        className={`sw-sidebar ${
          menuOpen ? 'is-open' : ''
        }`}
      >
        <NavLink
          to="/app"
          className="sw-brand"
          onClick={() =>
            setMenuOpen(false)
          }
        >
          <span className="sw-brand-mark">
            <Icon
              name="layers"
              size={27}
            />
          </span>

          <span>StockWise</span>
        </NavLink>


        <div className="sw-business">
          <span className="sw-business-label">
            ÇALIŞMA ALANI
          </span>

          <strong title={business?.name}>
            {business?.name}
          </strong>

          <span>
            {business?.currency} ·{' '}
            {business?.timezone}
          </span>
        </div>


        <nav
          className="sw-navigation"
          aria-label="Ana menü"
        >
          {navigation.map((item) => {
            if (
              item.available &&
              item.path
            ) {
              return (
                <NavLink
                  key={item.label}
                  to={item.path}
                  end={
                    item.path === '/app'
                  }
                  className={({
                    isActive,
                  }) =>
                    `sw-nav-item ${
                      isActive
                        ? 'is-active'
                        : ''
                    }`
                  }
                  onClick={() =>
                    setMenuOpen(false)
                  }
                >
                  <Icon
                    name={item.icon}
                  />

                  <span>
                    {item.label}
                  </span>
                </NavLink>
              )
            }

            return (
              <button
                key={item.label}
                type="button"
                className="sw-nav-item"
                disabled
                title="Bu bölüm sonraki aşamada kullanıma açılacak."
              >
                <Icon
                  name={item.icon}
                />

                <span>
                  {item.label}
                </span>

                <span className="sw-soon">
                  Yakında
                </span>
              </button>
            )
          })}
        </nav>


        <div className="sw-sidebar-bottom">
          <button
            type="button"
            className="sw-nav-item"
            disabled
            title="İşletme ayarları sonraki aşamada eklenecek."
          >
            <Icon name="settings" />

            <span>
              İşletme Ayarları
            </span>
          </button>


          <div className="sw-user">
            <span className="sw-avatar">
              {initials}
            </span>

            <div className="sw-user-info">
              <strong title={user?.name}>
                {user?.name}
              </strong>

              <span>
                İşletme sahibi
              </span>
            </div>

            <button
              type="button"
              className="sw-logout"
              onClick={handleLogout}
              disabled={loggingOut}
              aria-label={
                loggingOut
                  ? 'Çıkış yapılıyor'
                  : 'Çıkış yap'
              }
              title="Çıkış yap"
            >
              <Icon
                name="logout"
                size={18}
              />
            </button>
          </div>
        </div>
      </aside>


      <div className="sw-workspace">
        <header className="sw-topbar">
          <div className="sw-topbar-left">
            <button
              type="button"
              className="sw-mobile-toggle"
              aria-label={
                menuOpen
                  ? 'Menüyü kapat'
                  : 'Menüyü aç'
              }
              aria-expanded={menuOpen}
              aria-controls="sw-sidebar"
              onClick={() =>
                setMenuOpen(!menuOpen)
              }
            >
              <Icon
                name={
                  menuOpen
                    ? 'close'
                    : 'menu'
                }
              />
            </button>


            <span className="sw-breadcrumb">
              Çalışma alanı

              <span>/</span>

              <strong>
                {pageName}
              </strong>
            </span>
          </div>


          {location.pathname ===
            '/app' && (
            <span className="sw-demo-badge">
              <span />

              Örnek veriler
            </span>
          )}
        </header>

        <Outlet />
      </div>
    </div>
  )
}