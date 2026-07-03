export default function ErrorBanner({ message }) {
  if (!message) return null
  return (
    <div
      role="alert"
      className="rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 text-left"
    >
      {message}
    </div>
  )
}
