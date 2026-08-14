import { FiGithub, FiLinkedin, FiSearch } from 'react-icons/fi'
import Search from '../common/Search'
import { cn } from '../../utils/cn'

const STATUS_STYLES = {
  paid: 'bg-brand-50 text-brand-700 dark:bg-brand-500/10 dark:text-brand-400',
  pending: 'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400',
  unpaid: 'bg-ink-50 text-ink-500 dark:bg-white/5 dark:text-white/40',
  failed: 'bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400',
}

export default function EnrollmentsTable({ enrollments, search, onSearchChange }) {
  return (
    <div className="rounded-3xl bg-white dark:bg-ink-800 border border-ink-900/10 dark:border-white/10 shadow-card overflow-hidden">
      <div className="p-5 border-b border-ink-900/5 dark:border-white/5">
        <Search value={search} onChange={onSearchChange} placeholder="Search by name, email, or program…" />
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-ink-400 dark:text-white/40 uppercase tracking-wide border-b border-ink-900/5 dark:border-white/5">
              <th className="px-5 py-3 font-medium">Student</th>
              <th className="px-5 py-3 font-medium">Program</th>
              <th className="px-5 py-3 font-medium">Profile</th>
              <th className="px-5 py-3 font-medium">Task Links</th>
              <th className="px-5 py-3 font-medium">Payment</th>
              <th className="px-5 py-3 font-medium">Certificate</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-900/5 dark:divide-white/5">
            {enrollments.map((e) => (
              <tr key={e.id} className="hover:bg-cloud-200/60 dark:hover:bg-white/5 transition-colors">
                <td className="px-5 py-4">
                  <p className="font-medium text-ink-900 dark:text-white">{e.name}</p>
                  <p className="text-xs text-ink-400 dark:text-white/40">{e.email}</p>
                  <p className="text-xs text-ink-400 dark:text-white/40">{e.phone}</p>
                </td>
                <td className="px-5 py-4 text-ink-800 dark:text-white/80">{e.programTitle}</td>
                <td className="px-5 py-4 text-xs text-ink-400 dark:text-white/40">
                  {e.degree} · {e.branch}
                  <br />
                  {e.currentYear}
                </td>
                <td className="px-5 py-4">
                  {e.githubLink || e.linkedinLink ? (
                    <div className="flex gap-2">
                      {e.githubLink && (
                        <a href={e.githubLink} target="_blank" rel="noopener noreferrer" className="text-ink-600 dark:text-white/60 hover:text-brand-600 dark:hover:text-brand-400">
                          <FiGithub size={16} />
                        </a>
                      )}
                      {e.linkedinLink && (
                        <a href={e.linkedinLink} target="_blank" rel="noopener noreferrer" className="text-ink-600 dark:text-white/60 hover:text-brand-600 dark:hover:text-brand-400">
                          <FiLinkedin size={16} />
                        </a>
                      )}
                    </div>
                  ) : (
                    <span className="text-xs text-ink-400 dark:text-white/40">Not submitted</span>
                  )}
                </td>
                <td className="px-5 py-4">
                  <span className={cn('text-xs font-semibold px-2.5 py-1 rounded-full capitalize', STATUS_STYLES[e.paymentStatus])}>
                    {e.paymentStatus}
                  </span>
                  <p className="text-xs text-ink-400 dark:text-white/40 mt-1">₹{e.amount}</p>
                </td>
                <td className="px-5 py-4">
                  {e.certificateUnlocked ? (
                    <span className="text-xs font-semibold text-brand-700 dark:text-brand-400 bg-brand-50 dark:bg-brand-500/10 px-2.5 py-1 rounded-full">
                      {e.certificateId}
                    </span>
                  ) : (
                    <span className="text-xs text-ink-400 dark:text-white/40">Locked</span>
                  )}
                </td>
              </tr>
            ))}
            {enrollments.length === 0 && (
              <tr>
                <td colSpan={6} className="px-5 py-10 text-center text-ink-400 dark:text-white/40 text-sm">
                  <FiSearch className="mx-auto mb-2" size={20} />
                  No enrollments match your search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
