import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

// Scrolls to top on every route change (SPA navigation doesn't reset scroll by default)
export default function useScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' in window ? 'instant' : 'auto' })
  }, [pathname])
}
