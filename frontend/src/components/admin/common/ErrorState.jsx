import { FiAlertTriangle, FiRefreshCw } from 'react-icons/fi'

export default function ErrorState({ message, onRetry }) {
  return (
    <div className="text-center py-16 px-6">
      <div className="w-12 h-12 rounded-2xl bg-red-50 dark:bg-red-500/10 text-red-500 flex items-center justify-center mx-auto mb-4">
        <FiAlertTriangle size={22} />
      </div>
      <p className="font-semibold text-ink-900 dark:text-white">Something went wrong</p>
      <p className="text-sm text-ink-400 dark:text-white/50 mt-1.5">{message || 'Please try again.'}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 text-sm font-medium text-brand-600 dark:text-brand-400 hover:underline mt-4"
        >
          <FiRefreshCw size={14} /> Retry
        </button>
      )}
    </div>
  )
}
