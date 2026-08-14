import { cn } from '../../utils/cn'

/**
 * The visual signature of NeuIntern: every program compresses into exactly
 * 4 weeks, so the site uses this segmented tracker everywhere a program's
 * timeline needs representing — instead of a generic numbered list.
 */
export default function SprintTrack({ activeWeek = 0, size = 'md', className }) {
  const weeks = [1, 2, 3, 4]
  const isCompact = size === 'sm'

  return (
    <div className={cn('flex items-center gap-1.5', className)} aria-label="4-week program timeline">
      {weeks.map((week, i) => (
        <div key={week} className="flex items-center gap-1.5">
          <div
            className={cn(
              'rounded-full font-mono font-semibold flex items-center justify-center transition-colors duration-300',
              isCompact ? 'w-6 h-6 text-[10px]' : 'w-9 h-9 text-xs',
              activeWeek >= week
                ? 'bg-brand-gradient text-white shadow-card'
                : 'bg-white text-ink-400 border border-ink-900/10'
            )}
          >
            W{week}
          </div>
          {i < weeks.length - 1 && (
            <div
              className={cn(
                'rounded-full transition-colors duration-300',
                isCompact ? 'w-3 h-0.5' : 'w-5 h-0.5',
                activeWeek > week ? 'bg-brand-500' : 'bg-ink-900/10'
              )}
            />
          )}
        </div>
      ))}
    </div>
  )
}
