import { useState } from 'react'

export default function FormField({ label, id, error, hint, type, ...inputProps }) {
  const [revealed, setRevealed] = useState(false)
  const isPassword = type === 'password'
  const inputType = isPassword && revealed ? 'text' : type

  return (
    <div className="text-left">
      <label htmlFor={id} className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          name={id}
          type={inputType}
          className={`w-full rounded-lg border bg-white dark:bg-slate-900 px-3 py-2 text-slate-900 dark:text-slate-100 shadow-xs transition-shadow focus:outline-none focus:border-brand focus:shadow-[0_0_0_4px_var(--color-brand-light)] ${
            isPassword ? 'pr-16' : ''
          } ${error ? 'border-danger focus:shadow-[0_0_0_4px_var(--color-danger-light)]' : 'border-slate-300 dark:border-slate-600'}`}
          aria-invalid={Boolean(error)}
          {...inputProps}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setRevealed((prev) => !prev)}
            className="absolute inset-y-0 right-0 px-3 text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
          >
            {revealed ? 'Masquer' : 'Afficher'}
          </button>
        )}
      </div>
      {hint && !error && <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{hint}</p>}
      {error && <p className="mt-1 text-xs text-danger">{error}</p>}
    </div>
  )
}
