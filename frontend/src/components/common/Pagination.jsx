import { FiChevronLeft, FiChevronRight } from 'react-icons/fi'
import { cn } from '../../utils/cn'

export default function Pagination({ page, totalPages, onChange }) {
  if (totalPages <= 1) return null

  return (
    <nav className="flex items-center justify-center gap-2 mt-12" aria-label="Pagination">
      <button
        onClick={() => onChange(Math.max(1, page - 1))}
        disabled={page === 1}
        className="w-10 h-10 rounded-full border border-ink-900/10 flex items-center justify-center disabled:opacity-30 hover:border-brand-400 transition-colors"
        aria-label="Previous page"
      >
        <FiChevronLeft />
      </button>
      {Array.from({ length: totalPages }).map((_, i) => (
        <button
          key={i}
          onClick={() => onChange(i + 1)}
          aria-current={page === i + 1 ? 'page' : undefined}
          className={cn(
            'w-10 h-10 rounded-full text-sm font-medium transition-colors',
            page === i + 1 ? 'bg-brand-gradient text-white' : 'border border-ink-900/10 hover:border-brand-400'
          )}
        >
          {i + 1}
        </button>
      ))}
      <button
        onClick={() => onChange(Math.min(totalPages, page + 1))}
        disabled={page === totalPages}
        className="w-10 h-10 rounded-full border border-ink-900/10 flex items-center justify-center disabled:opacity-30 hover:border-brand-400 transition-colors"
        aria-label="Next page"
      >
        <FiChevronRight />
      </button>
    </nav>
  )
}
