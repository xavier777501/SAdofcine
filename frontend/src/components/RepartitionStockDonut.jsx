import { useState } from 'react'

const TAILLE = 160
const RAYON = 62
const EPAISSEUR = 20
const CIRCONFERENCE = 2 * Math.PI * RAYON
const ESPACE = 3 // gap en px entre segments, dans le sens de la circonférence

/**
 * Anneau de répartition du stock (rupture / à commander / OK), avec le total
 * au centre. Jamais de couleur seule : chaque segment a un point + un
 * libellé + une valeur dans la légende, et se met en évidence au survol.
 */
export default function RepartitionStockDonut({ nbRupture, nbACommander, nbReferences }) {
  const [survole, setSurvole] = useState(null)

  const aCommanderSeul = Math.max(0, nbACommander - nbRupture)
  const ok = Math.max(0, nbReferences - nbACommander)
  const total = nbReferences || 1

  const segments = [
    { cle: 'rupture', label: 'En rupture', valeur: nbRupture, classeCouleur: 'text-danger' },
    { cle: 'commander', label: 'À commander', valeur: aCommanderSeul, classeCouleur: 'text-orange-600 dark:text-orange-400' },
    { cle: 'ok', label: 'Stock OK', valeur: ok, classeCouleur: 'text-brand' },
  ]

  let cumul = 0
  const arcs = segments.map((s) => {
    const longueur = (s.valeur / total) * CIRCONFERENCE
    const longueurVisible = s.valeur > 0 ? Math.max(0, longueur - ESPACE) : 0
    const offset = -(cumul + ESPACE / 2)
    cumul += longueur
    return { ...s, longueurVisible, offset, pourcentage: Math.round((s.valeur / total) * 100) }
  })

  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200/70 dark:border-slate-700/70 px-6 py-5 flex flex-col sm:flex-row items-center gap-6 transition-all duration-200 hover:shadow-md hover:-translate-y-1">
      <div className="relative shrink-0" style={{ width: TAILLE, height: TAILLE }}>
        <svg width={TAILLE} height={TAILLE} viewBox={`0 0 ${TAILLE} ${TAILLE}`} role="img" aria-label="Répartition du stock par statut">
          <circle
            cx={TAILLE / 2}
            cy={TAILLE / 2}
            r={RAYON}
            fill="none"
            strokeWidth={EPAISSEUR}
            className="stroke-slate-100 dark:stroke-slate-700"
          />
          {arcs.map((a) =>
            a.valeur > 0 ? (
              <circle
                key={a.cle}
                cx={TAILLE / 2}
                cy={TAILLE / 2}
                r={RAYON}
                fill="none"
                strokeWidth={survole === a.cle ? EPAISSEUR + 4 : EPAISSEUR}
                strokeLinecap="round"
                strokeDasharray={`${a.longueurVisible} ${CIRCONFERENCE - a.longueurVisible}`}
                strokeDashoffset={a.offset}
                transform={`rotate(-90 ${TAILLE / 2} ${TAILLE / 2})`}
                className={`${a.classeCouleur} transition-[stroke-width] duration-150 cursor-pointer`}
                stroke="currentColor"
                tabIndex={0}
                role="img"
                aria-label={`${a.label} : ${a.valeur} référence${a.valeur > 1 ? 's' : ''} (${a.pourcentage} %)`}
                onMouseEnter={() => setSurvole(a.cle)}
                onMouseLeave={() => setSurvole(null)}
                onFocus={() => setSurvole(a.cle)}
                onBlur={() => setSurvole(null)}
              >
                <title>{`${a.label} : ${a.valeur} (${a.pourcentage} %)`}</title>
              </circle>
            ) : null,
          )}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">{nbReferences}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400">références</p>
        </div>
      </div>

      <div className="flex-1 w-full space-y-2.5">
        <p className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1">Répartition du stock</p>
        {arcs.map((a) => (
          <div
            key={a.cle}
            className={`flex items-center justify-between rounded-lg px-2 py-1.5 -mx-2 transition-colors ${
              survole === a.cle ? 'bg-slate-50 dark:bg-slate-700/50' : ''
            }`}
            onMouseEnter={() => setSurvole(a.cle)}
            onMouseLeave={() => setSurvole(null)}
          >
            <span className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
              <span className={`h-2.5 w-2.5 rounded-full bg-current ${a.classeCouleur}`} />
              {a.label}
            </span>
            <span className="text-sm font-semibold text-slate-900 dark:text-slate-100 tabular-nums">
              {a.valeur} <span className="font-normal text-slate-400 dark:text-slate-500">({a.pourcentage}%)</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
