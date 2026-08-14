import { FiSearch } from 'react-icons/fi'

export default function Search({ value, onChange, placeholder = 'Search programs…' }) {
  return (
    <div className="relative">
      <FiSearch className="absolute left-4 top-1/2 -translate-y-1/2 text-ink-400" size={18} />
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label="Search programs"
        className="w-full rounded-full border border-ink-900/10 bg-white pl-11 pr-5 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100 transition-shadow"
      />
    </div>
  )
}
