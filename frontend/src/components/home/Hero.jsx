import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FiArrowRight, FiPlayCircle } from 'react-icons/fi'
import SprintTrack from '../common/SprintTrack'
import useCountUp from '../../hooks/useCountUp'

function Stat({ value, suffix = '', label }) {
  const [ref, count] = useCountUp(value)
  return (
    <div ref={ref}>
      <p className="text-2xl font-bold font-display text-ink-900">
        {count}
        {suffix}
      </p>
      <p className="text-xs text-ink-400 mt-0.5">{label}</p>
    </div>
  )
}

export default function Hero() {
  return (
    <section className="relative overflow-hidden pt-32 pb-20 sm:pt-40 sm:pb-28">
      <div className="absolute inset-0 bg-brand-gradient-soft" />
      <div className="absolute top-10 -left-32 w-96 h-96 bg-brand-200/40 rounded-full blur-3xl" />
      <div className="absolute bottom-0 -right-32 w-96 h-96 bg-violet-400/20 rounded-full blur-3xl" />

      <div className="container-page relative grid lg:grid-cols-2 gap-16 items-center">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
        >
          <span className="eyebrow">
            <span className="w-2 h-2 rounded-full bg-brand-500 animate-pulse" /> Applications open for the next cohort
          </span>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-[1.08] mt-5">
            Launch Your Career with{' '}
            <span className="bg-brand-gradient bg-clip-text text-transparent">NeuIntern</span>
          </h1>
          <p className="text-ink-400 text-lg mt-6 max-w-lg leading-relaxed">
            Gain real-world experience through industry-focused internships designed to help students
            become job-ready — in one focused month.
          </p>
          <div className="flex flex-wrap gap-4 mt-9">
            <Link to="/programs" className="btn-primary">
              Apply Now <FiArrowRight />
            </Link>
            <Link to="/programs" className="btn-secondary">
              <FiPlayCircle /> Explore Programs
            </Link>
          </div>

          <div className="grid grid-cols-3 gap-6 mt-14 max-w-md">
            <Stat value={16} suffix="+" label="Programs" />
            <Stat value={4200} suffix="+" label="Interns trained" />
            <Stat value={4} label="Weeks per program" />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.15 }}
          className="relative hidden lg:block"
        >
          <div className="glass rounded-3xl p-7 max-w-sm ml-auto animate-float">
            <p className="eyebrow">Cohort Progress</p>
            <h3 className="font-semibold text-lg mt-2">React Development</h3>
            <p className="text-sm text-ink-400 mt-1">Batch #24 · 128 interns</p>
            <SprintTrack activeWeek={3} className="mt-6" />
            <div className="flex items-center justify-between mt-6 pt-6 border-t border-ink-900/5">
              <div>
                <p className="text-xs text-ink-400">Currently in</p>
                <p className="font-semibold text-ink-900">Week 3 · Routing & Data</p>
              </div>
              <div className="w-11 h-11 rounded-full bg-brand-gradient text-white flex items-center justify-center font-mono text-xs font-bold">
                75%
              </div>
            </div>
          </div>

          <div className="glass rounded-2xl p-4 absolute -bottom-8 -left-6 max-w-[220px] animate-float" style={{ animationDelay: '1.5s' }}>
            <p className="text-xs text-ink-400">Certificate issued to</p>
            <p className="text-sm font-semibold mt-0.5">Ananya Sharma</p>
            <p className="text-[11px] text-brand-600 mt-0.5">Full Stack Development</p>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
