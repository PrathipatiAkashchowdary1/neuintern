import { useState } from 'react'
import { FiDownload, FiAward, FiLoader } from 'react-icons/fi'
import { downloadOfferLetterPdf } from '../../api/enrollments'

export default function OfferLetter({ offerLetter, enrollmentId }) {
  const [downloading, setDownloading] = useState(false)

  if (!offerLetter) return null

  const formatDate = (iso) =>
    new Date(iso).toLocaleDateString('en-IN', { year: 'numeric', month: 'long', day: 'numeric' })

  const handleDownload = async () => {
    setDownloading(true)
    try {
      await downloadOfferLetterPdf(enrollmentId)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-lg">Your Offer Letter</h3>
        <button onClick={handleDownload} disabled={downloading} className="btn-secondary !py-2 !px-4 text-sm">
          {downloading ? <FiLoader className="animate-spin" size={14} /> : <FiDownload size={14} />}
          {downloading ? 'Preparing…' : 'Download PDF'}
        </button>
      </div>

      <div className="rounded-3xl bg-white border border-ink-900/10 shadow-card p-8 sm:p-12">
        <div className="flex items-center justify-between border-b border-ink-900/10 pb-6">
          <div className="flex items-center gap-2 font-display font-bold text-lg">
            <span className="w-9 h-9 rounded-xl bg-brand-gradient text-white flex items-center justify-center text-sm">
              NI
            </span>
            NeuIntern
          </div>
          <FiAward className="text-brand-600" size={26} />
        </div>

        <div className="flex items-center justify-between mt-8 text-sm font-semibold text-ink-400">
          <span>Date: {formatDate(offerLetter.startDate)}</span>
          <span>ID: {offerLetter.referenceId}</span>
        </div>

        <h2 className="text-2xl font-bold mt-6">Internship Offer Letter</h2>

        <p className="mt-6 leading-relaxed text-ink-800">
          Dear <span className="font-semibold">{offerLetter.studentName}</span>,
        </p>
        <p className="mt-4 leading-relaxed text-ink-800 text-justify">
          We are delighted to congratulate you on being selected for the{' '}
          <span className="font-semibold">{offerLetter.programTitle}</span> virtual internship position with
          NeuIntern. We are excited to welcome you to our team.
        </p>
        <p className="mt-4 leading-relaxed text-ink-800 text-justify">
          The internship will run for 1 month, from <span className="font-medium">{formatDate(offerLetter.startDate)}</span>{' '}
          to <span className="font-medium">{formatDate(offerLetter.endDate)}</span>. This program is designed as an
          educational opportunity, with the primary focus on learning, skill development, and gaining hands-on
          experience. We believe you will approach all assigned tasks and projects with dedication.
        </p>
        <p className="mt-4 leading-relaxed text-ink-800">As an intern, we expect you to:</p>
        <ul className="mt-2 space-y-1.5 list-disc pl-6 text-ink-800">
          <li>Perform all assigned tasks to the best of your ability.</li>
          <li>Follow all lawful and reasonable instructions provided to you.</li>
        </ul>
        <p className="mt-4 leading-relaxed text-ink-800 text-justify">
          We are confident that this internship will be a valuable experience and will contribute meaningfully to
          your career growth. We look forward to working with you and supporting you in achieving your professional
          goals.
        </p>
        <p className="mt-4 leading-relaxed text-ink-800 text-justify">
          By accepting this offer, you commit to executing assigned tasks diligently and striving for excellence in
          all aspects of your work.
        </p>
        <p className="mt-4 leading-relaxed text-ink-800">Best of luck, and welcome aboard!</p>

        <p className="mt-8 font-semibold text-ink-900">Thank you,</p>
        <p className="font-semibold text-ink-900">Team NeuIntern</p>
        <p className="mt-8 font-semibold text-ink-900">Founder</p>

        <div className="flex items-center justify-between mt-10 pt-6 border-t border-ink-900/10 text-xs text-ink-400 font-mono uppercase tracking-wider">
          <span>Ref: {offerLetter.referenceId}</span>
          <span>NeuIntern Programs Team</span>
        </div>
      </div>
    </div>
  )
}