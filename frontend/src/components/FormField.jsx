export default function FormField({ label, id, error, hint, ...inputProps }) {
  return (
    <div className="text-left">
      <label htmlFor={id} className="block text-sm font-medium text-slate-700 mb-1">
        {label}
      </label>
      <input
        id={id}
        name={id}
        className={`w-full rounded-lg border px-3 py-2 text-slate-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-amber-500 ${
          error ? 'border-red-400' : 'border-slate-300'
        }`}
        aria-invalid={Boolean(error)}
        {...inputProps}
      />
      {hint && !error && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  )
}
