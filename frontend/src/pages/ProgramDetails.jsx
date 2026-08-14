import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FiClock, FiMonitor, FiAward, FiArrowRight, FiCheckCircle } from 'react-icons/fi'
import Seo from '../seo/Seo'
import { breadcrumbSchema, courseSchema } from '../seo/schema'
import Breadcrumb from '../components/common/Breadcrumb'
import Timeline from '../components/common/Timeline'
import SprintTrack from '../components/common/SprintTrack'
import FAQ from '../components/common/FAQ'
import CTA from '../components/common/CTA'
import Loader from '../components/common/Loader'
import NotFound from './NotFound'
import { fetchProgramBySlug } from '../api/programs'
import { enrollInProgram } from '../api/enrollments'
import { useAuth } from '../context/AuthContext'

const programFaqTemplate = (program) => [
  { q: `Who can apply for the ${program.title} internship?`, a: program.eligibility },
  { q: 'Is this program remote?', a: `Yes, this program runs fully ${program.mode.toLowerCase()} over ${program.duration}.` },
  { q: 'Will I get a certificate?', a: program.certificate ? 'Yes, a certificate is issued after your final project review.' : 'This program does not currently include a certificate.' },
]

export default function ProgramDetails() {
  const { slug } = useParams()
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const [program, setProgram] = useState(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [enrolling, setEnrolling] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setNotFound(false)
    fetchProgramBySlug(slug)
      .then((data) => !cancelled && setProgram(data))
      .catch(() => !cancelled && setNotFound(true))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [slug])

  const handleEnroll = async () => {
    if (!isAuthenticated) {
      navigate('/login', { state: { from: `/programs/${slug}` } })
      return
    }
    setEnrolling(true)
    try {
      await enrollInProgram(slug)
      navigate('/dashboard')
    } finally {
      setEnrolling(false)
    }
  }

  if (loading) return <Loader label="Loading program" />
  if (notFound || !program) return <NotFound />

  return (
    <>
      <Seo
        title={program.title}
        description={program.tagline}
        path={`/programs/${program.slug}`}
        keywords={program.skills.join(', ')}
        structuredData={[
          breadcrumbSchema([
            { name: 'Home', path: '/' },
            { name: 'Programs', path: '/programs' },
            { name: program.title, path: `/programs/${program.slug}` },
          ]),
          courseSchema(program),
        ]}
      />

      <section className="relative pt-32 pb-16 overflow-hidden">
        <div className="absolute inset-0 bg-brand-gradient-soft" />
        <div className="container-page relative">
          <Breadcrumb
            items={[
              { name: 'Home', path: '/' },
              { name: 'Programs', path: '/programs' },
              { name: program.title, path: `/programs/${program.slug}` },
            ]}
          />
          <div className="grid lg:grid-cols-3 gap-10 mt-8 items-start">
            <div className="lg:col-span-2">
              <span className="eyebrow">{program.category}</span>
              <h1 className="text-4xl sm:text-5xl font-bold mt-4">{program.title}</h1>
              <p className="text-ink-400 mt-4 text-lg leading-relaxed max-w-xl">{program.tagline}</p>
              <SprintTrack activeWeek={4} className="mt-8" />
              <div className="flex flex-wrap gap-2 mt-6">
                {program.skills.map((s) => (
                  <span key={s} className="text-xs bg-white text-ink-800 border border-ink-900/10 px-3 py-1.5 rounded-full font-medium">
                    {s}
                  </span>
                ))}
              </div>
            </div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="glass rounded-3xl p-7"
            >
              <img
                src={program.image}
                alt={`${program.title} internship banner`}
                className="rounded-2xl w-full h-40 object-cover mb-6"
                loading="lazy"
              />
              <ul className="space-y-3 text-sm">
                <li className="flex items-center gap-2 text-ink-800">
                  <FiClock className="text-brand-600" /> {program.duration}
                </li>
                <li className="flex items-center gap-2 text-ink-800">
                  <FiMonitor className="text-brand-600" /> {program.mode}
                </li>
                <li className="flex items-center gap-2 text-ink-800">
                  <FiAward className="text-brand-600" /> {program.certificate ? 'Certificate included' : 'No certificate'}
                </li>
                <li className="flex items-center gap-2 text-ink-800">
                  <FiCheckCircle className="text-brand-600" /> {program.liveProjects} live project{program.liveProjects > 1 ? 's' : ''}
                </li>
              </ul>
              <div className="mt-6 pt-6 border-t border-ink-900/5 text-sm text-ink-400">
                Free to enroll · <span className="text-ink-900 font-medium">₹150</span> certificate fee after task completion
              </div>
              <button onClick={handleEnroll} disabled={enrolling} className="btn-primary w-full mt-4">
                {enrolling ? 'Enrolling…' : <>Enroll Now <FiArrowRight /></>}
              </button>
            </motion.div>
          </div>
        </div>
      </section>

      <section className="section-pad pt-0">
        <div className="container-page grid lg:grid-cols-3 gap-14">
          <div className="lg:col-span-2 space-y-16">
            <div>
              <h2 className="text-2xl font-bold mb-4">Overview</h2>
              <p className="text-ink-400 leading-relaxed">
                This 4-week {program.title.toLowerCase()} internship takes you from fundamentals to a working
                project through weekly milestones, live mentor sessions, and hands-on practice with{' '}
                {program.tools.join(', ')}.
              </p>
            </div>

            <div>
              <h2 className="text-2xl font-bold mb-6">Curriculum</h2>
              <Timeline steps={program.curriculum} />
            </div>

            <div>
              <h2 className="text-2xl font-bold mb-4">Learning Outcomes</h2>
              <ul className="grid sm:grid-cols-2 gap-3">
                {program.outcomes.map((o) => (
                  <li key={o} className="flex items-start gap-2 text-sm text-ink-800">
                    <FiCheckCircle className="text-brand-500 shrink-0 mt-0.5" />
                    {o}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <aside className="space-y-8">
            <div className="rounded-3xl bg-white border border-ink-900/5 p-6 shadow-card">
              <h3 className="font-semibold">Tools Used</h3>
              <div className="flex flex-wrap gap-2 mt-3">
                {program.tools.map((t) => (
                  <span key={t} className="text-xs bg-cloud-200 text-ink-800 px-3 py-1.5 rounded-full">
                    {t}
                  </span>
                ))}
              </div>
            </div>
            <div className="rounded-3xl bg-white border border-ink-900/5 p-6 shadow-card">
              <h3 className="font-semibold">Eligibility</h3>
              <p className="text-sm text-ink-400 mt-2 leading-relaxed">{program.eligibility}</p>
            </div>
            <div className="rounded-3xl bg-brand-gradient text-white p-6 shadow-card">
              <h3 className="font-semibold">Ready to start?</h3>
              <p className="text-sm text-white/80 mt-2">Free to enroll. Seats open now.</p>
              <button
                onClick={handleEnroll}
                disabled={enrolling}
                className="inline-flex items-center gap-2 bg-white text-brand-700 font-semibold rounded-full px-5 py-2.5 mt-4 text-sm hover:-translate-y-0.5 transition-transform"
              >
                {enrolling ? 'Enrolling…' : <>Enroll Now <FiArrowRight size={14} /></>}
              </button>
            </div>
          </aside>
        </div>
      </section>

      <FAQ items={programFaqTemplate(program)} title="Program FAQs" />
      <CTA
        title={`Join the next ${program.title} cohort`}
        subtitle="Seats are limited to keep mentor feedback meaningful."
      />
    </>
  )
}
