import Logo from './Logo'
import ThemeToggle from './ThemeToggle'
import fondImage from '../assets/images/fond.jpg'

export default function AuthLayout({ title, children, footer }) {
  return (
    <div className="min-h-screen flex bg-white dark:bg-slate-900">
      {/* Panneau gauche — illustration, masqué sur petit écran */}
      <div className="hidden lg:flex lg:w-1/2 flex-col bg-brand-light/40 dark:bg-slate-800/60 px-12 py-10 relative overflow-hidden">
        <div className="flex items-center gap-2.5">
          <Logo className="h-10 w-10 rounded-xl shadow-md" />
          <span className="brand-name text-2xl text-slate-900 dark:text-slate-100">StockAid</span>
        </div>

        <div className="flex-1 flex items-center justify-center py-6">
          <img
            src={fondImage}
            alt=""
            className="max-h-[42vh] w-auto object-contain drop-shadow-xl"
          />
        </div>

        <div className="max-w-sm">
          <h1 className="text-4xl xl:text-5xl font-extrabold leading-tight text-slate-900 dark:text-slate-100">
            Gérez votre stock, <span className="text-brand">sans y penser.</span>
          </h1>
          <p className="mt-4 text-base text-slate-600 dark:text-slate-300">
            Ruptures anticipées, commandes suggérées : StockAid s'occupe des calculs, vous gardez la main.
          </p>
        </div>
      </div>

      {/* Panneau droit — formulaire */}
      <div className="flex-1 relative flex flex-col items-center justify-center px-6 py-10 bg-white dark:bg-slate-900">
        <ThemeToggle className="absolute top-4 right-4" />
        <div className="w-full max-w-sm">
          <div className="lg:hidden text-center mb-8">
            <Logo className="h-12 w-12 mx-auto mb-3 rounded-xl shadow-md" />
            <h1 className="brand-name text-3xl text-slate-900 dark:text-slate-100">StockAid</h1>
          </div>

          <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-5">{title}</h2>

          {children}
          {footer}

          <div className="mt-10 flex justify-center">
            <Logo className="h-6 w-6 rounded-md opacity-50" />
          </div>
        </div>
      </div>
    </div>
  )
}
