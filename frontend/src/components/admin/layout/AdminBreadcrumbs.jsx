import { Link, useLocation } from 'react-router-dom'
import { FiChevronRight } from 'react-icons/fi'

const LABELS = {
  admin: 'Dashboard',
  students: 'Students',
  programs: 'Courses',
  payments: 'Payments',
  messages: 'Messages',
  analytics: 'Analytics',
}

export default function AdminBreadcrumbs() {
  const { pathname } = useLocation()
  const segments = pathname.split('/').filter(Boolean) // e.g. ['admin', 'students']

  const crumbs = segments.map((seg, i) => ({
    label: LABELS[seg] || seg,
    path: '/' + segments.slice(0, i + 1).join('/'),
  }))

  return (
    <nav aria-label="Breadcrumb" className="text-sm mb-1">
      <ol className="flex items-center gap-1.5 text-ink-400 dark:text-white/40">
        {crumbs.map((c, i) => {
          const isLast = i === crumbs.length - 1
          return (
            <li key={c.path} className="flex items-center gap-1.5">
              {isLast ? (
                <span className="text-ink-900 dark:text-white font-medium">{c.label}</span>
              ) : (
                <Link to={c.path} className="hover:text-brand-600 dark:hover:text-brand-400 transition-colors">
                  {c.label}
                </Link>
              )}
              {!isLast && <FiChevronRight size={13} />}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
