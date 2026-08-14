import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FiUser, FiMail, FiPhone, FiBookOpen } from 'react-icons/fi'
import Seo from '../seo/Seo'
import Loader from '../components/common/Loader'
import Stepper from '../components/dashboard/Stepper'
import OfferLetter from '../components/dashboard/OfferLetter'
import TaskSubmissionForm from '../components/dashboard/TaskSubmissionForm'
import CertificatePayment from '../components/dashboard/CertificatePayment'
import CertificateView from '../components/dashboard/CertificateView'
import { useAuth } from '../context/AuthContext'
import { fetchMyEnrollments, fetchOfferLetter, fetchCertificate } from '../api/enrollments'
import { fetchPrograms } from '../api/programs'
import { enrollInProgram } from '../api/enrollments'

export default function Dashboard() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [enrollments, setEnrollments] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [offerLetter, setOfferLetter] = useState(null)
  const [certificate, setCertificate] = useState(null)

  const [programs, setPrograms] = useState([])
  const [enrolling, setEnrolling] = useState(null)

  const activeEnrollment = enrollments.find((e) => e.id === activeId) || null

  const loadEnrollments = useCallback(async () => {
    const data = await fetchMyEnrollments()
    setEnrollments(data)
    if (data.length > 0) setActiveId((prev) => prev || data[0].id)
    return data
  }, [])

  useEffect(() => {
    setLoading(true)
    loadEnrollments()
      .then((data) => {
        if (data.length === 0) {
          return fetchPrograms({ limit: 100 }).then(setPrograms)
        }
      })
      .finally(() => setLoading(false))
  }, [loadEnrollments])

  useEffect(() => {
    if (!activeEnrollment) return
    setOfferLetter(null)
    setCertificate(null)
    fetchOfferLetter(activeEnrollment.id).then(setOfferLetter)
    if (activeEnrollment.certificateUnlocked) {
      fetchCertificate(activeEnrollment.id).then(setCertificate)
    }
  }, [activeEnrollment?.id, activeEnrollment?.certificateUnlocked])

  const handleEnroll = async (slug) => {
    setEnrolling(slug)
    try {
      const enrollment = await enrollInProgram(slug)
      const data = await loadEnrollments()
      setActiveId(enrollment.id)
      if (data.length > 0) setPrograms([])
    } finally {
      setEnrolling(null)
    }
  }

  const handleTaskSubmitted = (updated) => {
    setEnrollments((prev) => prev.map((e) => (e.id === updated.id ? updated : e)))
  }

  const handlePaid = (updated) => {
    setEnrollments((prev) => prev.map((e) => (e.id === updated.id ? updated : e)))
  }

  if (loading) return <Loader label="Loading your dashboard" />

  return (
    <>
      <Seo title="Dashboard" path="/dashboard" noindex />
      <section className="pt-28 pb-20 min-h-screen">
        <div className="container-page">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
            <div>
              <span className="eyebrow">Student Dashboard</span>
              <h1 className="text-3xl font-bold mt-2">Welcome, {user?.fullName?.split(' ')[0]}</h1>
            </div>
          </div>

          <div className="grid lg:grid-cols-4 gap-8">
            {/* Profile sidebar */}
            <aside className="lg:col-span-1 order-2 lg:order-1">
              <div className="rounded-3xl bg-white border border-ink-900/10 shadow-card p-6 space-y-4 lg:sticky lg:top-28">
                <h3 className="font-semibold">Your Profile</h3>
                <div className="space-y-3 text-sm text-ink-800">
                  <p className="flex items-center gap-2"><FiUser className="text-brand-600" size={15} /> {user?.fullName}</p>
                  <p className="flex items-center gap-2"><FiMail className="text-brand-600" size={15} /> {user?.email}</p>
                  <p className="flex items-center gap-2"><FiPhone className="text-brand-600" size={15} /> {user?.phone}</p>
                  <p className="flex items-center gap-2"><FiBookOpen className="text-brand-600" size={15} /> {user?.degree} · {user?.branch} · {user?.currentYear}</p>
                </div>

                {enrollments.length > 1 && (
                  <div className="pt-4 border-t border-ink-900/5">
                    <p className="text-xs font-semibold text-ink-400 uppercase tracking-wide mb-2">My Programs</p>
                    <div className="space-y-1.5">
                      {enrollments.map((e) => (
                        <button
                          key={e.id}
                          onClick={() => setActiveId(e.id)}
                          className={`w-full text-left text-sm px-3 py-2 rounded-xl transition-colors ${
                            e.id === activeId ? 'bg-brand-50 text-brand-700 font-medium' : 'hover:bg-cloud-200 text-ink-600'
                          }`}
                        >
                          {e.programTitle}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </aside>

            {/* Main content */}
            <div className="lg:col-span-3 order-1 lg:order-2 space-y-8">
              {!activeEnrollment ? (
                <div className="rounded-3xl bg-white border border-ink-900/10 shadow-card p-8">
                  <h3 className="font-semibold text-lg">You're not enrolled in a program yet</h3>
                  <p className="text-sm text-ink-400 mt-2">Pick a 4-week program below to get started — enrollment is free.</p>
                  <div className="grid sm:grid-cols-2 gap-4 mt-6">
                    {programs.slice(0, 6).map((p) => (
                      <div key={p.slug} className="rounded-2xl border border-ink-900/10 p-5">
                        <p className="font-semibold text-sm">{p.title}</p>
                        <p className="text-xs text-ink-400 mt-1">{p.category} · {p.duration}</p>
                        <button
                          onClick={() => handleEnroll(p.slug)}
                          disabled={enrolling === p.slug}
                          className="btn-primary !py-2 !px-4 text-xs mt-4"
                        >
                          {enrolling === p.slug ? 'Enrolling…' : 'Enroll Now'}
                        </button>
                      </div>
                    ))}
                  </div>
                  <Link to="/programs" className="text-brand-600 font-semibold text-sm hover:underline mt-6 inline-block">
                    Browse all programs →
                  </Link>
                </div>
              ) : (
                <>
                  <div className="rounded-3xl bg-white border border-ink-900/10 shadow-card p-6">
                    <h2 className="font-semibold text-lg mb-5">{activeEnrollment.programTitle}</h2>
                    <Stepper stage={activeEnrollment.stage} />
                  </div>

                  <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
                    <OfferLetter offerLetter={offerLetter} enrollmentId={activeEnrollment.id} />
                  </motion.div>

                  <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
                    <TaskSubmissionForm enrollment={activeEnrollment} onSubmitted={handleTaskSubmitted} />
                  </motion.div>

                  {activeEnrollment.taskSubmitted && !activeEnrollment.certificateUnlocked && (
                    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
                      <CertificatePayment enrollment={activeEnrollment} onPaid={handlePaid} />
                    </motion.div>
                  )}

                  {activeEnrollment.certificateUnlocked && (
                    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
                      <CertificateView certificate={certificate} enrollmentId={activeEnrollment.id} />
                    </motion.div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </section>
    </>
  )
}
