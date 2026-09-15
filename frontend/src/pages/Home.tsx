import ConnectionStatus from '../components/ConnectionStatus'

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 px-4">
      <div className="text-center max-w-md">
        <h1 className="text-5xl font-bold text-blue-900 mb-2">StockWise</h1>
        <p className="text-lg text-gray-600 mb-8">
          Satış, stok ve karar destek platformu
        </p>
        <ConnectionStatus />
      </div>
    </div>
  )
}
