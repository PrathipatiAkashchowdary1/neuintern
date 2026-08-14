import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FiClock, FiMonitor, FiAward, FiArrowUpRight } from 'react-icons/fi'
import SprintTrack from '../common/SprintTrack'

export default function ProgramCard({ program, index = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay: (index % 6) * 0.06 }}
      className="group rounded-3xl bg-white border border-ink-900/5 shadow-card hover:shadow-glass-lg hover:-translate-y-1.5 transition-all duration-300 overflow-hidden flex flex-col"
    >
      <div className="relative h-44 overflow-hidden">
        <img
          src={program.image}
          alt={`${program.title} internship`}
          loading="lazy"
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-ink-900/50 to-transparent" />
        <span className="absolute top-3 left-3 text-[11px] font-mono uppercase tracking-wider bg-white/90 text-ink-800 px-2.5 py-1 rounded-full">
          {program.category}
        </span>
      </div>

      <div className="p-6 flex flex-col flex-1">
        <h3 className="text-lg font-semibold">{program.title}</h3>
        <p className="text-sm text-ink-400 mt-1.5 leading-relaxed line-clamp-2">{program.tagline}</p>

        <SprintTrack activeWeek={4} size="sm" className="mt-4" />

        <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-4 text-xs text-ink-400">
          <span className="flex items-center gap-1.5">
            <FiClock size={13} /> {program.duration}
          </span>
          <span className="flex items-center gap-1.5">
            <FiMonitor size={13} /> {program.mode}
          </span>
          {program.certificate && (
            <span className="flex items-center gap-1.5">
              <FiAward size={13} /> Certificate
            </span>
          )}
        </div>

        <div className="flex flex-wrap gap-1.5 mt-4">
          {program.skills.slice(0, 3).map((skill) => (
            <span key={skill} className="text-[11px] bg-brand-50 text-brand-700 px-2.5 py-1 rounded-full font-medium">
              {skill}
            </span>
          ))}
        </div>

        <div className="flex items-center justify-between mt-6">
          {program.price ? (
            <span className="text-lg font-bold text-ink-900">₹{program.price.toLocaleString('en-IN')}</span>
          ) : (
            <span />
          )}
          <Link
            to={`/programs/${program.slug}`}
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-600 group-hover:gap-2.5 transition-all duration-300"
          >
            View Details <FiArrowUpRight size={16} />
          </Link>
        </div>
      </div>
    </motion.div>
  )
}
