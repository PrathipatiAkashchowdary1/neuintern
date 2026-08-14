import { useEffect, useState, useCallback } from 'react'
import { useOutletContext } from 'react-router-dom'
import { FiMail, FiTrash2, FiCheck, FiExternalLink } from 'react-icons/fi'
import toast from 'react-hot-toast'
import Seo from '../../seo/Seo'
import TableSkeleton from '../../components/admin/common/TableSkeleton'
import EmptyState from '../../components/admin/common/EmptyState'
import ErrorState from '../../components/admin/common/ErrorState'
import ConfirmDialog from '../../components/admin/common/ConfirmDialog'
import { fetchAllMessages, markMessageRead, deleteMessage } from '../../api/admin'
import { cn } from '../../utils/cn'

export default function AdminMessages() {
  const { refreshUnread } = useOutletContext()
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expandedId, setExpandedId] = useState(null)
  const [pendingDelete, setPendingDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    fetchAllMessages()
      .then(setMessages)
      .catch((err) => setError(err.message || 'Could not load messages.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleExpand = async (message) => {
    const opening = expandedId !== message.id
    setExpandedId(opening ? message.id : null)

    if (opening && !message.isRead) {
      try {
        await markMessageRead(message.id)
        setMessages((prev) => prev.map((m) => (m.id === message.id ? { ...m, isRead: true } : m)))
        refreshUnread()
      } catch {
        // Non-critical — the message still opens even if the read-flag fails to save
      }
    }
  }

  const handleDelete = async () => {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      await deleteMessage(pendingDelete.id)
      setMessages((prev) => prev.filter((m) => m.id !== pendingDelete.id))
      toast.success('Message deleted.')
      refreshUnread()
    } catch (err) {
      toast.error(err.message || 'Could not delete message.')
    } finally {
      setDeleting(false)
      setPendingDelete(null)
    }
  }

  return (
    <>
      <Seo title="Contact Messages" path="/admin/messages" noindex />
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-ink-900 dark:text-white">Contact Messages</h1>
        <p className="text-sm text-ink-400 dark:text-white/50">Submissions from the site's contact form.</p>
      </div>

      {loading && (
        <div className="rounded-3xl bg-white dark:bg-ink-800 border border-ink-900/10 dark:border-white/10 overflow-hidden">
          <TableSkeleton rows={5} cols={4} />
        </div>
      )}
      {!loading && error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && messages.length === 0 && (
        <EmptyState icon={FiMail} title="No messages yet" description="Contact form submissions will show up here." />
      )}
      {!loading && !error && messages.length > 0 && (
        <div className="rounded-3xl bg-white dark:bg-ink-800 border border-ink-900/10 dark:border-white/10 shadow-card divide-y divide-ink-900/5 dark:divide-white/5 overflow-hidden">
          {messages.map((m) => {
            const isOpen = expandedId === m.id
            return (
              <div key={m.id}>
                <button
                  onClick={() => handleExpand(m)}
                  className="w-full text-left px-5 py-4 flex items-center gap-4 hover:bg-cloud-200/60 dark:hover:bg-white/5 transition-colors"
                >
                  {!m.isRead && <span className="w-2 h-2 rounded-full bg-brand-500 shrink-0" />}
                  <div className={cn('flex-1 min-w-0', m.isRead && 'pl-[14px]')}>
                    <div className="flex items-center gap-2">
                      <p className={cn('text-sm truncate', m.isRead ? 'text-ink-600 dark:text-white/60' : 'font-semibold text-ink-900 dark:text-white')}>
                        {m.name}
                      </p>
                      <span className="text-xs text-ink-400 dark:text-white/40 shrink-0">{m.email}</span>
                    </div>
                    <p className="text-xs text-ink-400 dark:text-white/40 truncate mt-0.5">{m.subject}</p>
                  </div>
                  <span className="text-xs text-ink-400 dark:text-white/40 shrink-0">
                    {new Date(m.createdAt).toLocaleDateString('en-IN')}
                  </span>
                </button>

                {isOpen && (
                  <div className="px-5 pb-5 pl-9">
                    <p className="text-sm text-ink-800 dark:text-white/80 whitespace-pre-wrap bg-cloud-200 dark:bg-white/5 rounded-2xl p-4">
                      {m.message}
                    </p>
                    <div className="flex items-center gap-4 mt-3">
                      <a
                        href={`mailto:${m.email}?subject=${encodeURIComponent('Re: ' + m.subject)}`}
                        className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand-600 dark:text-brand-400 hover:underline"
                      >
                        <FiExternalLink size={12} /> Reply by email
                      </a>
                      {m.isRead && (
                        <span className="inline-flex items-center gap-1.5 text-xs text-ink-400 dark:text-white/40">
                          <FiCheck size={12} /> Read
                        </span>
                      )}
                      <button
                        onClick={() => setPendingDelete(m)}
                        className="ml-auto inline-flex items-center gap-1.5 text-xs font-semibold text-red-600 hover:underline"
                      >
                        <FiTrash2 size={12} /> Delete
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Delete this message?"
        description={pendingDelete ? `From ${pendingDelete.name} — this can't be undone.` : ''}
        confirmLabel="Delete"
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </>
  )
}
