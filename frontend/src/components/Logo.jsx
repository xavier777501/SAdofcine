export default function Logo({ className = 'h-9 w-9' }) {
  return (
    <svg viewBox="0 0 48 48" className={className} aria-hidden="true">
      <rect width="48" height="48" rx="10" fill="#09a57e" />
      <path d="M20 12h8v8h8v8h-8v8h-8v-8h-8v-8h8z" fill="#ffffff" />
    </svg>
  )
}
