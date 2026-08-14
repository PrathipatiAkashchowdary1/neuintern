import { useState } from 'react'
import { FiAward, FiDownload, FiLoader } from 'react-icons/fi'
import { downloadCertificatePdf } from '../../api/enrollments'

export default function CertificateView({ certificate, enrollmentId }) {
  const [downloading, setDownloading] = useState(false)
  if (!certificate) return null

  const issuedDate = certificate.issuedOn
    ? new Date(certificate.issuedOn).toLocaleDateString('en-IN', { year: 'numeric', month: 'long', day: 'numeric' })
    : ''
    const handleDownload = async () => {
    setDownloading(true)
    try {
      await downloadCertificatePdf(enrollmentId, certificate.certificateId)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4 ">
        <h3 className="font-semibold text-lg">Your Certificate</h3>
        <button onClick={handleDownload} disabled={downloading} className="btn-secondary !py-2 !px-4 text-sm">
          {downloading ? <FiLoader className="animate-spin" size={14} /> : <FiDownload size={14} />}
          {downloading ? 'Preparing…' : 'Download PDF'}
        </button>
      </div>

      <div className="relative rounded-3xl bg-white border border-ink-900/10 shadow-glass-lg p-10 sm:p-14 overflow-hidden ">
        <div className="absolute inset-0 bg-brand-gradient-soft" />
        <div className="absolute top-0 left-0 w-full h-2 bg-brand-gradient" />
        <div className="relative text-center">
          <div className="w-14 h-14 rounded-2xl bg-brand-gradient text-white flex items-center justify-center mx-auto shadow-card">
            <FiAward size={26} />
          </div>
          <p className="eyebrow mt-6">Certificate of Completion</p>
          <h3 className="text-2xl sm:text-3xl font-bold mt-3">{certificate.studentName}</h3>
          <p className="text-ink-400 mt-2">
            has successfully completed the 4-week{' '}
            <span className="text-ink-900 font-medium">{certificate.programTitle}</span> internship program
            at NeuIntern
          </p>
          <div className="flex flex-wrap items-center justify-center gap-6 sm:gap-10 mt-8 text-xs text-ink-400 font-mono uppercase tracking-wider">
            <span>Verified ID: {certificate.certificateId}</span>
            {issuedDate && <span>Issued: {issuedDate}</span>}
          </div>
        </div>
      </div>
    </div>
  )
}
