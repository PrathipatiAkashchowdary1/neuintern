import { useCallback, useEffect, useState } from 'react'
import { FiRefreshCw, FiRotateCw } from 'react-icons/fi'
import Seo from '../../seo/Seo'
import TableSkeleton from '../../components/admin/common/TableSkeleton'
import ErrorState from '../../components/admin/common/ErrorState'
import EmptyState from '../../components/admin/common/EmptyState'
import { cn } from '../../utils/cn'
import { fetchEmailOutbox, retryEmail } from '../../api/admin'

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'failed', label: 'Failed' },
  { key: 'pending', label: 'Waiting to retry' },
  { key: 'sent', label: 'Sent' },
]

const KIND_LABEL = {
  invoice: 'Payment receipt',
  certificate: 'Certificate',
  offer_letter: 'Offer letter',
  contact: 'Contact form',
}

const STATUS_STYLE = {
  sent: 'bg-brand-50 text-brand-700',
  pending: 'bg-amber-50 text-amber-700',
  failed: 'bg-red-50 text-red-700',
}
const STATUS_LABEL = { sent: 'Sent', pending: 'Waiting', failed: 'Failed' }

const when = (iso) =>
  iso
    ? new Date(iso + 'Z').toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
    : '—'

export default function AdminEmails() {
  const [filter, setFilter] = useState('all')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [busyId, setBusyId] = useState(null)
  const [notice, setNotice] = useState('')

  const load = useCallback(
    (quiet = false) => {
      if (!quiet) setLoading(true)
      setError(null)
      fetchEmailOutbox(filter)
        .then(setData)
        .catch((err) => setError(err.message || 'Could not load the email queue.'))
        .finally(() => setLoading(false))
    },
    [filter]
  )

  useEffect(() => {
    load()
  }, [load])

  const handleRetry = async (id) => {
    setBusyId(id)
    setNotice('')
    try {
      await retryEmail(id)
      setNotice('Retrying now. Refresh in a few seconds to see the result.')
      load(true)
    } catch (err) {
      setNotice(err.message || 'Could not retry that email.')
    } finally {
      setBusyId(null)
    }
  }

  const counts = data?.counts

  return (
    <>
      <Seo title="Email Queue" path="/admin/emails" noindex />
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-ink-900 dark:text-white">Emails</h1>
          <p className="text-sm text-ink-400 dark:text-white/50">
            Receipts, certificates, offer letters and contact messages. If sending fails, we keep retrying automatically.
          </p>
        </div>
        <button onClick={() => load()} className="btn-secondary !py-2 !px-4 text-sm inline-flex items-center gap-2">
          <FiRefreshCw size={14} /> Refresh
        </button>
      </div>

      {counts && (
        <div className="grid grid-cols-3 gap-3 mb-5 max-w-xl">
          {['failed', 'pending', 'sent'].map((k) => (
            <div key={k} className="rounded-2xl bg-white border border-ink-900/10 shadow-card px-4 py-3">
              <p className="text-xs text-ink-400">{k === 'pending' ? 'Waiting to retry' : STATUS_LABEL[k]}</p>
              <p className={cn('text-2xl font-bold', k === 'failed' && counts.failed > 0 ? 'text-red-600' : 'text-ink-900')}>
                {counts[k]}
              </p>
            </div>
          ))}
        </div>
      )}

      <div className="flex flex-wrap gap-2 mb-4" role="tablist" aria-label="Filter emails">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            role="tab"
            aria-selected={filter === f.key}
            onClick={() => setFilter(f.key)}
            className={cn(
              'px-4 py-1.5 rounded-full text-sm font-medium border transition-colors',
              filter === f.key ? 'bg-brand-gradient text-white border-transparent' : 'border-ink-900/10 text-ink-600 hover:border-brand-400 bg-white'
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {notice && (
        <p role="status" className="text-sm text-ink-600 bg-brand-50 rounded-xl px-4 py-2.5 mb-4">
          {notice}
        </p>
      )}

      {loading && (
        <div className="rounded-3xl bg-white border border-ink-900/10 overflow-hidden">
          <TableSkeleton rows={6} cols={5} />
        </div>
      )}
      {!loading && error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && data?.items.length === 0 && <EmptyState title="Nothing here" description="No emails match this filter." />}

      {!loading && !error && data?.items.length > 0 && (
        <div className="rounded-3xl bg-white border border-ink-900/10 shadow-card overflow-x-auto">
          <table className="w-full min-w-[46rem] text-sm">
            <thead>
              <tr className="text-left text-xs text-ink-400 uppercase tracking-wide border-b border-ink-900/5">
                <th className="px-5 py-3 font-medium">Email</th>
                <th className="px-5 py-3 font-medium">To</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">When</th>
                <th className="px-5 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-900/5">
              {data.items.map((e) => (
                <tr key={e.id} className="align-top hover:bg-cloud-200/60 transition-colors">
                  <td className="px-5 py-4">
                    <p className="font-medium text-ink-900">{KIND_LABEL[e.kind] || e.kind}</p>
                    <p className="text-xs text-ink-400 mt-0.5 max-w-xs truncate" title={e.subject}>{e.subject}</p>
                  </td>
                  <td className="px-5 py-4 text-ink-600 min-w-[11rem] break-words">{e.to}</td>
                  <td className="px-5 py-4">
                    <span className={cn('text-xs font-semibold px-2.5 py-1 rounded-full', STATUS_STYLE[e.status])}>
                      {STATUS_LABEL[e.status]}
                    </span>
                    {e.status !== 'sent' && e.attempts > 0 && (
                      <p className="text-xs text-ink-400 mt-1.5">
                        {e.attempts} {e.attempts === 1 ? 'attempt' : 'attempts'}
                      </p>
                    )}
                    {e.lastError && e.status !== 'sent' && (
                      <p className="text-xs text-red-600 mt-1 max-w-[16rem] break-words">{e.lastError}</p>
                    )}
                  </td>
                  <td className="px-5 py-4 text-ink-600 whitespace-nowrap">
                    {e.status === 'sent' && <>Sent {when(e.sentAt)}</>}
                    {e.status === 'pending' && <>Next try {when(e.nextAttemptAt)}</>}
                    {e.status === 'failed' && <>Queued {when(e.createdAt)}</>}
                  </td>
                  <td className="px-5 py-4 text-right">
                    {e.status !== 'sent' && (
                      <button
                        onClick={() => handleRetry(e.id)}
                        disabled={busyId === e.id}
                        aria-label={`Retry sending to ${e.to}`}
                        className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-600 hover:underline disabled:opacity-50"
                      >
                        <FiRotateCw size={14} /> {busyId === e.id ? 'Retrying…' : 'Retry now'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
