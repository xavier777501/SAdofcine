export default function SubmitButton({ loading, children }) {
  return (
    <button
      type="submit"
      disabled={loading}
      className="w-full rounded-lg bg-amber-500 px-4 py-2.5 font-semibold text-slate-900 transition hover:bg-amber-400 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {loading ? 'Veuillez patienter…' : children}
    </button>
  )
}
