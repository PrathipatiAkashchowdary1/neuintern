import { useEffect, useState } from 'react'

const SCRIPT_SRC = 'https://checkout.razorpay.com/v1/checkout.js'

// Loads the Razorpay Checkout script once and reuses it across mounts.
export default function useRazorpayScript() {
  const [ready, setReady] = useState(typeof window !== 'undefined' && Boolean(window.Razorpay))

  useEffect(() => {
    if (ready) return
    const existing = document.querySelector(`script[src="${SCRIPT_SRC}"]`)
    if (existing) {
      existing.addEventListener('load', () => setReady(true))
      if (window.Razorpay) setReady(true)
      return
    }
    const script = document.createElement('script')
    script.src = SCRIPT_SRC
    script.async = true
    script.onload = () => setReady(true)
    script.onerror = () => setReady(false)
    document.body.appendChild(script)
  }, [ready])

  return ready
}
