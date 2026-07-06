const VARIANTS = {
  primary: `
    text-white bg-[image:var(--color-brand-gradient)]
    shadow-[var(--shadow-sm)]
    hover:shadow-[var(--shadow-brand)] hover:-translate-y-0.5
  `,
  secondary: `
    text-brand bg-white dark:bg-slate-800 border border-brand/40
    shadow-[var(--shadow-xs)]
    hover:bg-brand-light dark:hover:bg-brand/10 hover:border-brand
  `,
  ghost: `
    text-slate-600 dark:text-slate-300
    hover:bg-slate-100 dark:hover:bg-slate-800
  `,
  danger: `
    text-white bg-danger
    shadow-[var(--shadow-xs)]
    hover:shadow-[var(--shadow-danger)] hover:-translate-y-0.5
  `,
}

const SIZES = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2.5 text-sm',
  lg: 'px-6 py-3 text-base',
}

/**
 * Bouton "premium" : dégradé + ombre colorée qui apparaît au survol (au lieu
 * d'un simple changement de teinte plate), légère élévation, et le feedback
 * élastique au clic (.tg-tap, voir tokens/README) sur tous les variants.
 */
export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  className = '',
  children,
  ...props
}) {
  return (
    <button
      disabled={disabled || loading}
      className={`
        tg-tap inline-flex items-center justify-center gap-2 rounded-[var(--radius-md)]
        font-semibold transition-all duration-[var(--duration-base)] ease-[var(--ease-standard)]
        disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-none
        ${VARIANTS[variant]} ${SIZES[size]} ${className}
      `}
      {...props}
    >
      {loading && (
        <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" opacity="0.25" />
          <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
        </svg>
      )}
      {children}
    </button>
  )
}
