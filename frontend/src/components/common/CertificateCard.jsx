import { motion } from 'framer-motion'
import { FiAward } from 'react-icons/fi'

export default function CertificateCard({ programTitle = 'Web Development', studentName = 'Student Name' }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.96 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6 }}
      className="relative rounded-3xl bg-white border border-ink-900/10 shadow-glass-lg p-10 sm:p-14 overflow-hidden"
    >
      <div className="absolute inset-0 bg-brand-gradient-soft" />
      <div className="absolute top-0 left-0 w-full h-2 bg-brand-gradient" />
      <div className="relative text-center">
        <div className="w-14 h-14 rounded-2xl bg-brand-gradient text-white flex items-center justify-center mx-auto shadow-card">
          <FiAward size={26} />
        </div>
        <p className="eyebrow mt-6">Certificate of Completion</p>
        <h3 className="text-2xl sm:text-3xl font-bold mt-3">{studentName}</h3>
        <p className="text-ink-400 mt-2">
          has successfully completed the 4-week <span className="text-ink-900 font-medium">{programTitle}</span> internship
          program at NeuIntern
        </p>
        <div className="flex items-center justify-center gap-10 mt-8 text-xs text-ink-400 font-mono uppercase tracking-wider">
          <span>Verified ID: NI-2026-0000</span>
          <span>Issued: 2026</span>
        </div>
      </div>
    </motion.div>
  )
}
