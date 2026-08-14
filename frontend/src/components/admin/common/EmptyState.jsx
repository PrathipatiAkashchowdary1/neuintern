export default function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="text-center py-16 px-6">
      {Icon && (
        <div className="w-12 h-12 rounded-2xl bg-brand-50 dark:bg-white/5 text-brand-500 flex items-center justify-center mx-auto mb-4">
          <Icon size={22} />
        </div>
      )}
      <p className="font-semibold text-ink-900 dark:text-white">{title}</p>
      {description && <p className="text-sm text-ink-400 dark:text-white/50 mt-1.5 max-w-sm mx-auto">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
