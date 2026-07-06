const ACCENT_COLORS = {
  brand: 'before:bg-brand',
  danger: 'before:bg-danger',
  info: 'before:bg-info',
  critical: 'before:bg-critical',
  warning: 'before:bg-warning',
}

/**
 * Carte "premium" : ombre à deux couches (voir --shadow-md), coins plus
 * généreux, et deux options pour se démarquer d'une carte plate :
 * - `hoverable` : légère élévation au survol (pour les cartes cliquables)
 * - `accent`    : liseré coloré sur le bord gauche (pour catégoriser visuellement)
 */
export default function Card({ hoverable = false, accent, className = '', children, ...props }) {
  return (
    <div
      className={`
        relative bg-white dark:bg-slate-800 rounded-[var(--radius-lg)]
        border border-slate-200/70 dark:border-slate-700/70
        shadow-[var(--shadow-sm)]
        ${hoverable ? 'transition-all duration-[var(--duration-base)] ease-[var(--ease-standard)] hover:shadow-[var(--shadow-md)] hover:-translate-y-1 cursor-pointer' : ''}
        ${accent ? `pl-5 before:absolute before:left-0 before:top-3 before:bottom-3 before:w-1 before:rounded-full ${ACCENT_COLORS[accent]}` : ''}
        ${className}
      `}
      {...props}
    >
      {children}
    </div>
  )
}
