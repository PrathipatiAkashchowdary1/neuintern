import { useEffect, useState, useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { FiDownload, FiUsers } from 'react-icons/fi'
import toast from 'react-hot-toast'
import Seo from '../../seo/Seo'
import EnrollmentsTable from '../../components/admin/EnrollmentsTable'
import TableSkeleton from '../../components/admin/common/TableSkeleton'
import EmptyState from '../../components/admin/common/EmptyState'
import ErrorState from '../../components/admin/common/ErrorState'
import { fetchAllEnrollments } from '../../api/admin'
import { downloadCsv } from '../../utils/csv'

const CSV_COLUMNS = [
  { key: 'name', label: 'Name' },
  { key: 'email', label: 'Email' },
  { key: 'phone', label: 'Phone' },
  { key: 'degree', label: 'Degree' },
  { key: 'branch', label: 'Branch' },
  { key: 'currentYear', label: 'Year' },
  { key: 'programTitle', label: 'Program' },
  { key: 'paymentStatus', label: 'Payment Status' },
  { key: 'amount', label: 'Amount' },
  { key: 'certificateId', label: 'Certificate ID' },
  { key: 'enrolledAt', label: 'Enrolled At' },
]

export default function AdminStudents() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [enrollments, setEnrollments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const search = searchParams.get('search') || ''

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    fetchAllEnrollments()
      .then(setEnrollments)
      .catch((err) => setError(err.message || 'Could not load students.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const filtered = useMemo(() => {
    if (!search) return enrollments
    const q = search.toLowerCase()
    return enrollments.filter(
      (e) => e.name.toLowerCase().includes(q) || e.email.toLowerCase().includes(q) || e.programTitle.toLowerCase().includes(q)
    )
  }, [enrollments, search])

  const handleSearchChange = (value) => {
    const next = new URLSearchParams(searchParams)
    if (value) next.set('search', value)
    else next.delete('search')
    setSearchParams(next)
  }

  const handleExport = () => {
    if (filtered.length === 0) {
      toast.error('Nothing to export.')
      return
    }
    downloadCsv(`neuintern-students-${new Date().toISOString().slice(0, 10)}.csv`, filtered, CSV_COLUMNS)
    toast.success(`Exported ${filtered.length} student${filtered.length === 1 ? '' : 's'} to CSV.`)
  }

  return (
    <>
      <Seo title="Students" path="/admin/students" noindex />
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-ink-900 dark:text-white">Students</h1>
          <p className="text-sm text-ink-400 dark:text-white/50">Everyone enrolled across all programs.</p>
        </div>
        <button onClick={handleExport} className="btn-secondary !py-2 !px-4 text-sm">
          <FiDownload size={14} /> Export CSV
        </button>
      </div>

      {loading && (
        <div className="rounded-3xl bg-white dark:bg-ink-800 border border-ink-900/10 dark:border-white/10 overflow-hidden">
          <TableSkeleton rows={6} cols={6} />
        </div>
      )}
      {!loading && error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && enrollments.length === 0 && (
        <EmptyState icon={FiUsers} title="No students yet" description="Once students enroll in a program, they'll show up here." />
      )}
      {!loading && !error && enrollments.length > 0 && (
        <EnrollmentsTable enrollments={filtered} search={search} onSearchChange={handleSearchChange} />
      )}
    </>
  )
}
