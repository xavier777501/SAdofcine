export default function AuthLayout({ title, subtitle, children }) {
  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white">SAD OFFICINE</h1>
          <p className="text-slate-400 text-sm mt-1">Pilotage de stock pour pharmacies</p>
        </div>
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h2 className="text-xl font-semibold text-slate-900 mb-1 text-center">{title}</h2>
          {subtitle && <p className="text-sm text-slate-500 text-center mb-6">{subtitle}</p>}
          {children}
        </div>
      </div>
    </div>
  )
}
