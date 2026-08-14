import { motion, AnimatePresence } from 'framer-motion'
import { FiAlertTriangle, FiX } from 'react-icons/fi'

export default function ConfirmDialog({
  open,
  title = 'Are you sure?',
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  destructive = true,
  loading = false,
  onConfirm,
  onCancel,
}) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[110] bg-ink-900/50 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={onCancel}
          role="alertdialog"
          aria-modal="true"
        >
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.97 }}
            onClick={(e) => e.stopPropagation()}
            className="bg-white dark:bg-ink-800 rounded-3xl w-full max-w-sm p-6 relative shadow-glass-lg"
          >
            <button
              onClick={onCancel}
              aria-label="Close"
              className="absolute top-4 right-4 w-8 h-8 rounded-full flex items-center justify-center text-ink-400 hover:bg-cloud-200 dark:hover:bg-white/10 transition-colors"
            >
              <FiX size={16} />
            </button>

            <div
              className={`w-11 h-11 rounded-2xl flex items-center justify-center ${
                destructive ? 'bg-red-50 text-red-600 dark:bg-red-500/10' : 'bg-brand-50 text-brand-600 dark:bg-white/5'
              }`}
            >
              <FiAlertTriangle size={20} />
            </div>
            <h3 className="font-semibold text-lg mt-4 text-ink-900 dark:text-white">{title}</h3>
            {description && <p className="text-sm text-ink-400 dark:text-white/50 mt-1.5">{description}</p>}

            <div className="flex gap-3 mt-6">
              <button
                onClick={onCancel}
                className="flex-1 rounded-xl border border-ink-900/10 dark:border-white/10 text-ink-800 dark:text-white font-medium text-sm py-2.5 hover:bg-cloud-200 dark:hover:bg-white/5 transition-colors"
              >
                {cancelLabel}
              </button>
              <button
                onClick={onConfirm}
                disabled={loading}
                className={`flex-1 rounded-xl font-medium text-sm py-2.5 text-white transition-colors disabled:opacity-60 ${
                  destructive ? 'bg-red-600 hover:bg-red-700' : 'bg-brand-gradient'
                }`}
              >
                {loading ? 'Please wait…' : confirmLabel}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
