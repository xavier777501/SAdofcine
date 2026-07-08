export default function SubmitButton({ loading, loadingLabel, children }) {
  return (
    <button
      type="submit"
      disabled={loading}
      className="tg-tap w-full rounded-lg bg-brand-gradient px-4 py-2.5 font-semibold text-white shadow-sm transition-all hover:shadow-brand hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0 disabled:hover:shadow-sm"
    >
      {loading ? (loadingLabel || 'Veuillez patienter…') : children}
    </button>
  )
}
