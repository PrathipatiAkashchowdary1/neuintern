import { useEffect, useState, useCallback } from 'react'
import Seo from '../../seo/Seo'
import ProgramsManager from '../../components/admin/ProgramsManager'
import TableSkeleton from '../../components/admin/common/TableSkeleton'
import ErrorState from '../../components/admin/common/ErrorState'
import { fetchAdminPrograms } from '../../api/admin'

export default function AdminPrograms() {
  const [programs, setPrograms] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    fetchAdminPrograms()
      .then(setPrograms)
      .catch((err) => setError(err.message || 'Could not load programs.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <>
      <Seo title="Manage Programs" path="/admin/programs" noindex />
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-ink-900 dark:text-white">Courses</h1>
        <p className="text-sm text-ink-400 dark:text-white/50">Edit pricing, details, and visibility for every program.</p>
      </div>

      {loading && (
        <div className="rounded-3xl bg-white dark:bg-ink-800 border border-ink-900/10 dark:border-white/10 overflow-hidden">
          <TableSkeleton rows={5} cols={5} />
        </div>
      )}
      {!loading && error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && <ProgramsManager programs={programs} onChanged={load} />}
    </>
  )
}
