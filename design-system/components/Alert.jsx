const VARIANTS = {
  brand: { style: 'bg-brand-light dark:bg-brand/10 border-brand/30 text-brand-dark dark:text-brand', icon: '✓' },
  danger: { style: 'bg-danger-light dark:bg-danger/10 border-danger/30 text-danger', icon: '!' },
  info: { style: 'bg-info-light dark:bg-info/10 border-info/30 text-info', icon: 'i' },
  warning: { style: 'bg-warning-light dark:bg-warning/10 border-warning/30 text-warning', icon: '!' },
}

/** Bannière d'information/erreur avec icône, coins plus généreux que par défaut. */
export default function Alert({ variant = 'info', children }) {
  if (!children) return null
  const { style, icon } = VARIANTS[variant]

  return (
    <div role="alert" className={`flex items-start gap-3 rounded-[var(--radius-lg)] border px-4 py-3 text-sm ${style}`}>
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-current/15 text-[11px] font-bold">
        {icon}
      </span>
      <span className="pt-0.5">{children}</span>
    </div>
  )
}
