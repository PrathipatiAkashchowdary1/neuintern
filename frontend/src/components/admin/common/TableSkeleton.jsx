export default function TableSkeleton({ rows = 6, cols = 5 }) {
  return (
    <div className="animate-pulse">
      <div className="grid gap-4 px-5 py-3" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
        {Array.from({ length: cols }).map((_, i) => (
          <div key={i} className="h-3 bg-ink-900/10 dark:bg-white/10 rounded" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div
          key={r}
          className="grid gap-4 px-5 py-4 border-t border-ink-900/5 dark:border-white/5"
          style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}
        >
          {Array.from({ length: cols }).map((_, c) => (
            <div key={c} className="h-3 bg-ink-900/5 dark:bg-white/5 rounded" style={{ width: `${60 + ((c * 13) % 30)}%` }} />
          ))}
        </div>
      ))}
    </div>
  )
}
