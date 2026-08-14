import { Link } from 'react-router-dom'
import { FiChevronRight } from 'react-icons/fi'

export default function Breadcrumb({ items }) {
  // items: [{ name, path }] — last item renders as plain text (current page)
  return (
    <nav aria-label="Breadcrumb" className="text-sm">
      <ol className="flex flex-wrap items-center gap-1.5 text-ink-400">
        {items.map((item, i) => {
          const isLast = i === items.length - 1
          return (
            <li key={item.path} className="flex items-center gap-1.5">
              {isLast ? (
                <span className="text-ink-900 font-medium" aria-current="page">
                  {item.name}
                </span>
              ) : (
                <Link to={item.path} className="hover:text-brand-600 transition-colors">
                  {item.name}
                </Link>
              )}
              {!isLast && <FiChevronRight size={14} />}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
