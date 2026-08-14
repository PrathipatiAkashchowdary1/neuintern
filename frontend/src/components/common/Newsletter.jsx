import { useState } from 'react'
import { FiSend, FiCheck } from 'react-icons/fi'

export default function Newsletter() {
  const [email, setEmail] = useState('')
  const [subscribed, setSubscribed] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!email) return
    // Phase 2: wire to a real newsletter/backend endpoint
    setSubscribed(true)
    setEmail('')
  }

  return (
    <div>
      <h4 className="font-semibold text-white">Stay in the loop</h4>
      <p className="text-ink-100/60 text-sm mt-2">New cohorts and career tips, once or twice a month.</p>
      {subscribed ? (
        <p className="flex items-center gap-2 text-sm text-brand-200 mt-4">
          <FiCheck /> Subscribed — welcome aboard.
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="flex mt-4 gap-2">
          <label htmlFor="newsletter-email" className="sr-only">
            Email address
          </label>
          <input
            id="newsletter-email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@email.com"
            className="min-w-0 flex-1 rounded-full bg-white/10 border border-white/15 px-4 py-2.5 text-sm text-white placeholder:text-white/40 focus:outline-none focus:border-brand-400"
          />
          <button
            type="submit"
            aria-label="Subscribe"
            className="shrink-0 w-10 h-10 rounded-full bg-brand-gradient text-white flex items-center justify-center hover:-translate-y-0.5 transition-transform duration-300"
          >
            <FiSend size={16} />
          </button>
        </form>
      )}
    </div>
  )
}
