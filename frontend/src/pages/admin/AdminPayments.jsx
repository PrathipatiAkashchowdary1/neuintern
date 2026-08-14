import { useEffect, useState, useCallback, useMemo } from 'react'
import { FiDownload, FiCreditCard, FiLoader } from 'react-icons/fi'
import toast from 'react-hot-toast'
import Seo from '../../seo/Seo'
import TableSkeleton from '../../components/admin/common/TableSkeleton'
import EmptyState from '../../components/admin/common/EmptyState'
import ErrorState from '../../components/admin/common/ErrorState'
import Search from '../../components/common/Search'
import { fetchAllEnrollments } from '../../api/admin'
import { downloadInvoicePdf } from '../../api/enrollments'
import { downloadCsv } from '../../utils/csv'
import { cn } from '../../utils/cn'

const STATUS_STYLES = {
  paid: 'bg-brand-50 text-brand-700 dark:bg-brand-500/10 dark:text-brand-400',
  pending: 'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400',
  unpaid: 'bg-ink-50 text-ink-500 dark:bg-white/5 dark:text-white/40',
  failed: 'bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400',
}

const CSV_COLUMNS = [
  { key: 'razorpayPaymentId', label: 'Transaction ID' },
  { key: 'name', label: 'Student' },
  { key: 'email', label: 'Email' },
  { key: 'programTitle', label: 'Program' },
  { key: 'amount', label: 'Amount' },
  { key: 'currency', label: 'Currency' },
  { key: 'paymentStatus', label: 'Status' },
  { key: 'paidAt', label: 'Paid At' },
]

export default function AdminPayments() {
  const [enrollments, setEnrollments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [downloadingId, setDownloadingId] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    fetchAllEnrollments()
      .then(setEnrollments)
      .catch((err) => setError(err.message || 'Could not load payments.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const filtered = useMemo(() => {
    if (!search) return enrollments
    const q = search.toLowerCase()
    return enrollments.filter((e) => e.name.toLowerCase().includes(q) || e.email.toLowerCase().includes(q))
  }, [enrollments, search])

  const totalRevenue = useMemo(
    () => enrollments.filter((e) => e.paymentStatus === 'paid').reduce((sum, e) => sum + e.amount, 0),
    [enrollments]
  )
  const paidCount = enrollments.filter((e) => e.paymentStatus === 'paid').length
  const pendingCount = enrollments.filter((e) => e.paymentStatus === 'pending').length

  const handleExport = () => {
    const paidOnly = filtered.filter((e) => e.paymentStatus === 'paid')
    if (paidOnly.length === 0) {
      toast.error('No paid transactions to export.')
      return
    }
    downloadCsv(`neuintern-payments-${new Date().toISOString().slice(0, 10)}.csv`, paidOnly, CSV_COLUMNS)
    toast.success(`Exported ${paidOnly.length} payment${paidOnly.length === 1 ? '' : 's'} to CSV.`)
  }

  const handleDownloadInvoice = async (enrollment) => {
    setDownloadingId(enrollment.id)
    try {
      await downloadInvoicePdf(enrollment.id)
    } catch (err) {
      toast.error(err.message || 'Could not download invoice.')
    } finally {
      setDownloadingId(null)
    }
  }

  return (
    <>
      <Seo title="Payments" path="/admin/payments" noindex />
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-ink-900 dark:text-white">Payments</h1>
          <p className="text-sm text-ink-400 dark:text-white/50">Certificate fee transactions across all students.</p>
        </div>
        <button onClick={handleExport} className="btn-secondary !py-2 !px-4 text-sm">
          <FiDownload size={14} /> Export CSV
        </button>
      </div>

      {!loading && !error && (
        <div className="grid sm:grid-cols-3 gap-4 mb-6">
          <div className="rounded-2xl bg-white dark:bg-ink-800 border border-ink-900/10 dark:border-white/10 p-5">
            <p className="text-xl font-bold text-ink-900 dark:text-white">₹{totalRevenue.toLocaleString('en-IN')}</p>
            <p className="text-xs text-ink-400 dark:text-white/50 mt-0.5">Total Revenue</p>
          </div>
          <div className="rounded-2xl bg-white dark:bg-ink-800 border border-ink-900/10 dark:border-white/10 p-5">
            <p className="text-xl font-bold text-ink-900 dark:text-white">{paidCount}</p>
            <p className="text-xs text-ink-400 dark:text-white/50 mt-0.5">Successful Payments</p>
          </div>
          <div className="rounded-2xl bg-white dark:bg-ink-800 border border-ink-900/10 dark:border-white/10 p-5">
            <p className="text-xl font-bold text-ink-900 dark:text-white">{pendingCount}</p>
            <p className="text-xs text-ink-400 dark:text-white/50 mt-0.5">Pending / Incomplete</p>
          </div>
        </div>
      )}

      {loading && (
        <div className="rounded-3xl bg-white dark:bg-ink-800 border border-ink-900/10 dark:border-white/10 overflow-hidden">
          <TableSkeleton rows={6} cols={5} />
        </div>
      )}
      {!loading && error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && enrollments.length === 0 && (
        <EmptyState icon={FiCreditCard} title="No transactions yet" description="Payments will appear here once students pay the certificate fee." />
      )}
      {!loading && !error && enrollments.length > 0 && (
        <div className="rounded-3xl bg-white dark:bg-ink-800 border border-ink-900/10 dark:border-white/10 shadow-card overflow-hidden">
          <div className="p-5 border-b border-ink-900/5 dark:border-white/5">
            <Search value={search} onChange={setSearch} placeholder="Search by student name or email…" />
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-ink-400 dark:text-white/40 uppercase tracking-wide border-b border-ink-900/5 dark:border-white/5">
                  <th className="px-5 py-3 font-medium">Transaction</th>
                  <th className="px-5 py-3 font-medium">Student</th>
                  <th className="px-5 py-3 font-medium">Amount</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium text-right">Invoice</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-900/5 dark:divide-white/5">
                {filtered.map((e) => (
                  <tr key={e.id} className="hover:bg-cloud-200/60 dark:hover:bg-white/5 transition-colors">
                    <td className="px-5 py-4">
                      <p className="font-mono text-xs text-ink-800 dark:text-white/80">{e.razorpayPaymentId || '—'}</p>
                      <p className="text-xs text-ink-400 dark:text-white/40 mt-0.5">
                        {e.paidAt ? new Date(e.paidAt).toLocaleDateString('en-IN') : '—'}
                      </p>
                    </td>
                    <td className="px-5 py-4">
                      <p className="font-medium text-ink-900 dark:text-white">{e.name}</p>
                      <p className="text-xs text-ink-400 dark:text-white/40">{e.email}</p>
                    </td>
                    <td className="px-5 py-4 text-ink-800 dark:text-white/80">
                      ₹{e.amount} <span className="text-xs text-ink-400 dark:text-white/40">{e.currency}</span>
                    </td>
                    <td className="px-5 py-4">
                      <span className={cn('text-xs font-semibold px-2.5 py-1 rounded-full capitalize', STATUS_STYLES[e.paymentStatus])}>
                        {e.paymentStatus}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-right">
                      {e.paymentStatus === 'paid' ? (
                        <button
                          onClick={() => handleDownloadInvoice(e)}
                          disabled={downloadingId === e.id}
                          className="inline-flex items-center gap-1.5 text-brand-600 dark:text-brand-400 text-xs font-semibold hover:underline disabled:opacity-50"
                        >
                          {downloadingId === e.id ? <FiLoader className="animate-spin" size={12} /> : <FiDownload size={12} />}
                          Download
                        </button>
                      ) : (
                        <span className="text-xs text-ink-400 dark:text-white/40">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  )
}
