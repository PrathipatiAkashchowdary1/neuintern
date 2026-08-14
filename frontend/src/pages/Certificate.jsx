import { useState } from 'react'
import { motion } from 'framer-motion'
import { FiSearch, FiShield, FiShare2, FiBriefcase } from 'react-icons/fi'
import Seo from '../seo/Seo'
import { breadcrumbSchema } from '../seo/schema'
import Breadcrumb from '../components/common/Breadcrumb'
import CertificateCard from '../components/common/CertificateCard'
import CTA from '../components/common/CTA'
import { verifyCertificate } from '../api/certificate'

const benefits = [
  { icon: FiShield, title: 'Verifiable', text: 'Each certificate carries a unique ID for future verification.' },
  { icon: FiShare2, title: 'Shareable', text: 'Add it directly to LinkedIn or your portfolio site.' },
  { icon: FiBriefcase, title: 'Recruiter-ready', text: 'Backed by a real project you can walk through in interviews.' },
]

export default function Certificate() {
  const [certId, setCertId] = useState('')
  const [result, setResult] = useState(null)
  const [checking, setChecking] = useState(false)

  const handleVerify = async (e) => {
    e.preventDefault()
    if (!certId) return
    setChecking(true)
    const res = await verifyCertificate(certId)
    setResult(res)
    setChecking(false)
  }

  return (
    <>
      <Seo
        title="Certificate"
        description="See what a NeuIntern completion certificate looks like and how verification will work."
        path="/certificate"
        structuredData={breadcrumbSchema([{ name: 'Home', path: '/' }, { name: 'Certificate', path: '/certificate' }])}
      />

      <section className="pt-32 pb-16">
        <div className="container-page">
          <Breadcrumb items={[{ name: 'Home', path: '/' }, { name: 'Certificate', path: '/certificate' }]} />
          <div className="max-w-2xl mt-8">
            <span className="eyebrow">Certificate</span>
            <h1 className="text-4xl sm:text-5xl font-bold mt-4">A certificate backed by real work</h1>
            <p className="text-ink-400 mt-4 leading-relaxed">
              Complete your program's final project review and receive a certificate the same week —
              not weeks later.
            </p>
          </div>
        </div>
      </section>

      <section className="section-pad pt-0">
        <div className="container-page max-w-2xl">
          <CertificateCard />
        </div>
      </section>

      <section className="section-pad bg-cloud-200">
        <div className="container-page grid sm:grid-cols-3 gap-6">
          {benefits.map((b, i) => (
            <motion.div
              key={b.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="rounded-3xl bg-white border border-ink-900/5 p-7 shadow-card"
            >
              <div className="w-12 h-12 rounded-2xl bg-brand-gradient-soft flex items-center justify-center text-brand-600">
                <b.icon size={20} />
              </div>
              <h3 className="font-semibold mt-5">{b.title}</h3>
              <p className="text-sm text-ink-400 mt-2 leading-relaxed">{b.text}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="section-pad">
        <div className="container-page max-w-lg text-center">
          <span className="eyebrow">Verification</span>
          <h2 className="text-3xl font-bold mt-3">Verify a certificate</h2>
          <p className="text-ink-400 mt-3">Certificate verification is launching soon. Try the form below for a preview.</p>
          <form onSubmit={handleVerify} className="flex gap-2 mt-6">
            <div className="relative flex-1">
              <FiSearch className="absolute left-4 top-1/2 -translate-y-1/2 text-ink-400" />
              <input
                value={certId}
                onChange={(e) => setCertId(e.target.value)}
                placeholder="Enter certificate ID (e.g. NI-2026-0000)"
                className="w-full rounded-full border border-ink-900/10 pl-11 pr-4 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
              />
            </div>
            <button type="submit" className="btn-primary shrink-0" disabled={checking}>
              {checking ? 'Checking…' : 'Verify'}
            </button>
          </form>
          {result && (
  <div className="mt-4 bg-white border border-ink-900/10 rounded-2xl p-4">
    <p className="font-semibold">{result.message}</p>

    {result.success && result.data && (
      <div className="mt-3 space-y-2 text-left">
        <p>
          <strong>Certificate ID:</strong> {result.data.certificateId}
        </p>
        <p>
          <strong>Student Name:</strong> {result.data.studentName}
        </p>
        <p>
          <strong>Program:</strong> {result.data.program}
        </p>
        <p>
          <strong>Issued On:</strong> {result.data.issuedOn}
        </p>
      </div>
    )}
  </div>
)}

        </div>
      </section>

      <CTA />
    </>
  )
}
