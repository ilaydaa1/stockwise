import { Link } from 'react-router-dom'
import ConnectionStatus from '../components/ConnectionStatus'

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 px-4">
      <div className="text-center max-w-md">
        <h1 className="text-5xl font-bold text-blue-900 mb-2">StockWise</h1>
        <p className="text-lg text-gray-600 mb-8">
          Satış, stok ve karar destek platformu
        </p>
        <div className="flex gap-4 mb-8">
          <Link
            to="/login"
            className="flex-1 py-3 px-4 bg-blue-800 text-white rounded-lg hover:bg-blue-900 transition-colors font-medium"
          >
            Giriş Yap
          </Link>
          <Link
            to="/register"
            className="flex-1 py-3 px-4 bg-white text-blue-800 border-2 border-blue-800 rounded-lg hover:bg-blue-50 transition-colors font-medium"
          >
            Kayıt Ol
          </Link>
        </div>
        <ConnectionStatus />
      </div>
    </div>
  )
}
