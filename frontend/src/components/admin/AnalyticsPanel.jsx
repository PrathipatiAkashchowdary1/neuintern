import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'
import { FiUsers, FiDollarSign, FiCheckSquare, FiAward } from 'react-icons/fi'
import StatCard from './common/StatCard'

function formatShortDate(iso) {
  const d = new Date(iso)
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}

export default function AnalyticsPanel({ analytics }) {
  if (!analytics) return null

  const funnelData = [
    { stage: 'Enrolled', count: analytics.funnel.enrolled },
    { stage: 'Task Submitted', count: analytics.funnel.taskSubmitted },
    { stage: 'Paid', count: analytics.funnel.paid },
    { stage: 'Certified', count: analytics.funnel.certified },
  ]

  const registrations = (analytics.registrationsByDay || []).map((d) => ({ ...d, label: formatShortDate(d.date) }))
  const revenue = (analytics.revenueByDay || []).map((d) => ({ ...d, label: formatShortDate(d.date) }))

  return (
    <div className="space-y-6">
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={FiUsers} label="Total Students" value={analytics.totalStudents} trendPct={analytics.trends?.studentsPct} />
        <StatCard icon={FiCheckSquare} label="Total Enrollments" value={analytics.totalEnrollments} />
        <StatCard
          icon={FiDollarSign}
          label="Total Revenue"
          value={`₹${analytics.totalRevenue.toLocaleString('en-IN')}`}
          trendPct={analytics.trends?.revenuePct}
        />
        <StatCard icon={FiAward} label="Certificates Issued" value={analytics.funnel.certified} />
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="rounded-3xl bg-white dark:bg-ink-800 border border-ink-900/10 dark:border-white/10 shadow-card p-6">
          <h3 className="font-semibold text-ink-900 dark:text-white mb-4">Student Registrations (30 days)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={registrations}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E9E4F5" />
              <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={4} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} width={28} />
              <Tooltip />
              <Line type="monotone" dataKey="count" stroke="#7C3AED" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-3xl bg-white dark:bg-ink-800 border border-ink-900/10 dark:border-white/10 shadow-card p-6">
          <h3 className="font-semibold text-ink-900 dark:text-white mb-4">Revenue (30 days)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={revenue}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E9E4F5" />
              <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={4} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} width={36} />
              <Tooltip formatter={(v) => [`₹${v}`, 'Revenue']} />
              <Line type="monotone" dataKey="amount" stroke="#EC4899" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="rounded-3xl bg-white dark:bg-ink-800 border border-ink-900/10 dark:border-white/10 shadow-card p-6">
          <h3 className="font-semibold text-ink-900 dark:text-white mb-4">Completion Funnel</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={funnelData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E9E4F5" />
              <XAxis dataKey="stage" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#7C3AED" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-3xl bg-white dark:bg-ink-800 border border-ink-900/10 dark:border-white/10 shadow-card p-6">
          <h3 className="font-semibold text-ink-900 dark:text-white mb-4">Enrollments by Program</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={analytics.enrollmentsByProgram} layout="vertical" margin={{ left: 24 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E9E4F5" />
              <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} />
              <YAxis dataKey="program" type="category" width={140} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#EC4899" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
