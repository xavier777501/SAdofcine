export default function PageHeader({ label, title, subtitle, action }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-1.5 text-xs text-slate-400 dark:text-slate-500">
        <span>Accueil</span>
        <span>›</span>
        <span className="font-medium text-slate-600 dark:text-slate-300">{label}</span>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">{title}</h1>
          {subtitle && <p className="mt-1 text-slate-500 dark:text-slate-400 text-sm">{subtitle}</p>}
        </div>
        {action}
      </div>
    </div>
  )
}
