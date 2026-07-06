const VARIANTS = {
  brand: 'bg-brand-light dark:bg-brand/10 text-brand-dark dark:text-brand border-brand/30',
  danger: 'bg-danger-light dark:bg-danger/10 text-danger border-danger/30',
  critical: 'bg-critical-light dark:bg-critical/10 text-critical border-critical/30',
  warning: 'bg-warning-light dark:bg-warning/10 text-warning border-warning/30',
  info: 'bg-info-light dark:bg-info/10 text-info border-info/30',
  neutral: 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 border-slate-300 dark:border-slate-600',
}

/** Pastille de statut avec point coloré — pour rupture/critique/à commander/etc. */
export default function Badge({ variant = 'neutral', dot = true, children }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-[var(--radius-full)] border px-2.5 py-1 text-xs font-medium ${VARIANTS[variant]}`}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  )
}
