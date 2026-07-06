export default function ErrorBanner({ message }) {
  if (!message) return null
  return (
    <div
      role="alert"
      className="rounded-lg bg-danger-light dark:bg-danger/10 border border-danger/30 text-danger text-sm px-4 py-3 text-left"
    >
      {message}
    </div>
  )
}
