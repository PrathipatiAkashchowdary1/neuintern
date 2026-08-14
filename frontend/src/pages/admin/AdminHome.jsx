import { useEffect, useState, useCallback } from 'react'
import Seo from '../../seo/Seo'
import AnalyticsPanel from '../../components/admin/AnalyticsPanel'
import ErrorState from '../../components/admin/common/ErrorState'
import { fetchAnalytics } from '../../api/admin'
import { cn } from '../../utils/cn'

function SkeletonCards() {
  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="rounded-2xl bg-white dark:bg-ink-800 border border-ink-900/10 dark:border-white/10 p-5 h-28">
          <div className="w-11 h-11 rounded-xl bg-ink-900/5 dark:bg-white/10" />
          <div className="h-5 w-16 bg-ink-900/10 dark:bg-white/10 rounded mt-4" />
          <div className="h-3 w-24 bg-ink-900/5 dark:bg-white/5 rounded mt-2" />
        </div>
      ))}
    </div>
  )
}

export default function AdminHome() {
  const [analytics, setAnalytics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    fetchAnalytics()
      .then(setAnalytics)
      .catch((err) => setError(err.message || 'Could not load dashboard data.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <>
      <Seo title="Admin Dashboard" path="/admin" noindex />
      <div className={cn('space-y-1 mb-6')}>
        <h1 className="text-2xl font-bold text-ink-900 dark:text-white">Dashboard</h1>
        <p className="text-sm text-ink-400 dark:text-white/50">An overview of students, revenue, and program activity.</p>
      </div>

      {loading && <SkeletonCards />}
      {!loading && error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && <AnalyticsPanel analytics={analytics} />}
    </>
  )
}
