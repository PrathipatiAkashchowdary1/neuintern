import { FiArrowUp, FiArrowDown, FiMinus } from 'react-icons/fi'
import { cn } from '../../../utils/cn'

export default function StatCard({ icon: Icon, label, value, trendPct }) {
  const hasTrend = trendPct !== null && trendPct !== undefined
  const isUp = hasTrend && trendPct > 0
  const isFlat = hasTrend && trendPct === 0

  return (
    <div className="rounded-2xl bg-white dark:bg-ink-800 border border-ink-900/10 dark:border-white/10 shadow-card p-5">
      <div className="flex items-start justify-between">
        <div className="w-11 h-11 rounded-xl bg-brand-gradient-soft dark:bg-white/5 text-brand-600 dark:text-brand-400 flex items-center justify-center shrink-0">
          <Icon size={18} />
        </div>
        {hasTrend && (
          <span
            className={cn(
              'flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-full',
              isFlat
                ? 'bg-ink-50 text-ink-400 dark:bg-white/5 dark:text-white/40'
                : isUp
                  ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400'
                  : 'bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-400'
            )}
          >
            {isFlat ? <FiMinus size={11} /> : isUp ? <FiArrowUp size={11} /> : <FiArrowDown size={11} />}
            {Math.abs(trendPct)}%
          </span>
        )}
      </div>
      <p className="text-xl font-bold text-ink-900 dark:text-white mt-4">{value}</p>
      <p className="text-xs text-ink-400 dark:text-white/50 mt-0.5">{label}</p>
    </div>
  )
}
