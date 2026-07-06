import Logo from './Logo'
import ThemeToggle from './ThemeToggle'
import fondImage from '../assets/images/fond.jpg'

export default function AuthLayout({ title, subtitle, children }) {
  return (
    <div className="min-h-screen flex">
      <div className="hidden lg:flex lg:w-1/2 items-center justify-center bg-brand-light dark:bg-slate-800 p-12">
        <img src={fondImage} alt="" className="max-h-[70vh] w-full object-contain drop-shadow-xl" />
      </div>
      <div className="flex-1 relative flex items-center justify-center bg-surface dark:bg-slate-900 px-4 py-10">
        <ThemeToggle className="absolute top-4 right-4" />
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <Logo className="h-12 w-12 mx-auto mb-3 rounded-xl shadow-md" />
            <h1 className="brand-name text-3xl text-slate-900 dark:text-slate-100">StockAid</h1>
            <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Pilotage de stock pour pharmacies</p>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-md border border-slate-200 dark:border-slate-700 p-8">
            <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-1 text-center">{title}</h2>
            {subtitle && <p className="text-sm text-slate-500 dark:text-slate-400 text-center mb-6">{subtitle}</p>}
            {children}
          </div>
        </div>
      </div>
    </div>
  )
}
