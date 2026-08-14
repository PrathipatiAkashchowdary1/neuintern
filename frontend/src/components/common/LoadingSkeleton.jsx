import { cn } from '../../utils/cn'

export function SkeletonCard() {
  return (
    <div className="rounded-3xl border border-ink-900/5 bg-white p-5 overflow-hidden">
      <div className="h-40 rounded-2xl bg-ink-50 relative overflow-hidden">
        <Shimmer />
      </div>
      <div className="h-4 w-3/4 bg-ink-50 rounded mt-5 relative overflow-hidden"><Shimmer /></div>
      <div className="h-3 w-1/2 bg-ink-50 rounded mt-3 relative overflow-hidden"><Shimmer /></div>
    </div>
  )
}

export function ProgramGridSkeleton({ count = 6 }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  )
}

function Shimmer({ className }) {
  return (
    <div
      className={cn(
        'absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/60 to-transparent',
        className
      )}
    />
  )
}
