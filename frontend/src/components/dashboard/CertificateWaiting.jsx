import { FiClock, FiCheckCircle } from 'react-icons/fi'

export default function CertificateWaiting({ enrollment }) {
  const completionDate = enrollment.completionDate
    ? new Date(enrollment.completionDate).toLocaleDateString('en-IN', { year: 'numeric', month: 'long', day: 'numeric' })
    : null

  return (
    <div className="rounded-3xl bg-white border border-ink-900/10 shadow-card p-7">
      <div className="flex items-center gap-2">
        <FiCheckCircle className="text-brand-600" size={18} />
        <h3 className="font-semibold text-lg">Payment received</h3>
      </div>
      <p className="text-sm text-ink-400 mt-2">
        Thanks — your ₹150 certificate fee is confirmed and your receipt is on its way to your inbox.
      </p>

      <div className="flex items-start gap-3 bg-cloud-200 rounded-2xl p-4 mt-5">
        <FiClock className="text-brand-600 shrink-0 mt-0.5" size={18} />
        <div>
          <p className="text-sm font-medium text-ink-900">
            Your certificate unlocks on {completionDate || 'the course completion date'}
          </p>
          <p className="text-xs text-ink-400 mt-1">
            Certificates are issued once the 4-week program is actually complete, not just once it's paid
            for. We'll email it to you automatically the moment it's ready — no need to check back.
          </p>
        </div>
      </div>
    </div>
  )
}