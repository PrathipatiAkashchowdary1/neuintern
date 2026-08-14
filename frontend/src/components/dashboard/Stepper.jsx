import { FiCheck } from 'react-icons/fi'
import { cn } from '../../utils/cn'

const STEPS = [
  { key: 'enrolled', label: 'Enrolled' },
  { key: 'offer', label: 'Offer Letter' },
  { key: 'task', label: 'Task Submission' },
  { key: 'payment', label: 'Payment' },
  { key: 'certificate', label: 'Certificate' },
]

// The backend reports a single `stage` string telling us which step the
// student is currently working on ('task' | 'payment' | 'certificate').
// Everything before that step index is complete; that step itself is
// "current" (except 'certificate', which means fully done).
const STAGE_TO_CURRENT_INDEX = { task: 2, payment: 3, certificate: 4 }

export default function Stepper({ stage }) {
  const currentIndex = STAGE_TO_CURRENT_INDEX[stage] ?? 2
  const allDone = stage === 'certificate'

  return (
    <ol className="flex flex-wrap items-center gap-x-2 gap-y-4">
      {STEPS.map((step, i) => {
        const done = i < currentIndex || allDone
        const isCurrent = i === currentIndex && !allDone
        const isLast = i === STEPS.length - 1
        return (
          <li key={step.key} className="flex items-center gap-2">
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold shrink-0 transition-colors',
                  done && 'bg-brand-gradient text-white shadow-card',
                  isCurrent && 'bg-white border-2 border-brand-500 text-brand-600',
                  !done && !isCurrent && 'bg-white border border-ink-900/10 text-ink-400'
                )}
              >
                {done ? <FiCheck size={14} /> : i + 1}
              </span>
              <span className={cn('text-xs font-medium whitespace-nowrap', done || isCurrent ? 'text-ink-900' : 'text-ink-400')}>
                {step.label}
              </span>
            </div>
            {!isLast && <span className={cn('w-6 sm:w-10 h-0.5 mx-1', done ? 'bg-brand-500' : 'bg-ink-900/10')} />}
          </li>
        )
      })}
    </ol>
  )
}
