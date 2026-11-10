import type { CSSProperties, ReactNode } from 'react'

/* Shared building blocks for form dialogs and tables. */

export const labelStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '7px',
  fontSize: '13px',
  fontWeight: 600,
  color: '#293851',
}

export const inputStyle: CSSProperties = {
  width: '100%',
  height: '42px',
  boxSizing: 'border-box',
  border: '1px solid #dce2ea',
  borderRadius: '8px',
  padding: '0 12px',
  background: '#fff',
  color: '#172641',
  font: 'inherit',
  outline: 'none',
}

export const hintStyle: CSSProperties = {
  fontSize: '12px',
  fontWeight: 400,
  lineHeight: 1.5,
  color: '#8591a6',
}

export const secondaryButtonStyle: CSSProperties = {
  height: '40px',
  padding: '0 18px',
  borderRadius: '8px',
  border: '1px solid #dce2ea',
  background: '#fff',
  color: '#35445d',
  fontWeight: 600,
  cursor: 'pointer',
}

export const smallButtonStyle: CSSProperties = {
  height: '34px',
  padding: '0 12px',
  borderRadius: '8px',
  border: '1px solid #dce5f2',
  background: '#f6f9ff',
  color: '#356fd6',
  fontWeight: 600,
  fontSize: '13px',
  cursor: 'pointer',
}

export const mutedTextStyle: CSSProperties = {
  color: '#738096',
}

export const emptyStateStyle: CSSProperties = {
  minHeight: '180px',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '10px',
  padding: '32px 20px',
  textAlign: 'center',
  color: '#738096',
}

export function ErrorBanner({ children }: { children: ReactNode }) {
  return (
    <div
      role="alert"
      style={{
        padding: '11px 13px',
        borderRadius: '8px',
        background: '#fff2f0',
        border: '1px solid #ffd8d2',
        color: '#b33a2f',
        fontSize: '13px',
      }}
    >
      {children}
    </div>
  )
}

export function Modal({
  title,
  subtitle,
  onClose,
  children,
  footer,
  maxWidth = 620,
}: {
  title: string
  subtitle?: string
  onClose: () => void
  children: ReactNode
  footer: ReactNode
  maxWidth?: number
}) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        background: 'rgba(8, 25, 50, 0.48)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: `${maxWidth}px`,
          maxHeight: 'calc(100vh - 48px)',
          overflowY: 'auto',
          background: '#fff',
          borderRadius: '14px',
          boxShadow: '0 24px 60px rgba(15, 31, 56, 0.22)',
        }}
      >
        <div
          style={{
            padding: '22px 24px',
            borderBottom: '1px solid #e7ebf1',
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: '20px',
          }}
        >
          <div>
            <h2
              style={{
                margin: '0 0 5px',
                color: '#10213f',
                fontSize: '20px',
              }}
            >
              {title}
            </h2>

            {subtitle && (
              <p
                style={{
                  margin: 0,
                  color: '#7b8799',
                  fontSize: '13px',
                }}
              >
                {subtitle}
              </p>
            )}
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Kapat"
            style={{
              width: '34px',
              height: '34px',
              border: 'none',
              borderRadius: '8px',
              background: '#f4f6f9',
              color: '#647188',
              fontSize: '18px',
              lineHeight: 1,
              cursor: 'pointer',
            }}
          >
            ×
          </button>
        </div>

        <div
          style={{
            padding: '24px',
            display: 'grid',
            gap: '18px',
          }}
        >
          {children}
        </div>

        <div
          style={{
            padding: '18px 24px',
            borderTop: '1px solid #e7ebf1',
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '10px',
          }}
        >
          {footer}
        </div>
      </div>
    </div>
  )
}

export function formatMoney(
  value: string | number | null | undefined,
  currency: string
): string {
  const amount = Number(value ?? 0)

  return new Intl.NumberFormat('tr-TR', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number.isFinite(amount) ? amount : 0)
}

export function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('tr-TR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}
