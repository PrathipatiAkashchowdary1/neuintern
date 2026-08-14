import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FiArrowRight } from 'react-icons/fi'

export default function CTA({
  eyebrow = 'Ready when you are',
  title = 'Your 4-week internship starts here',
  subtitle = 'Pick a program, commit to a month, walk away with a project and a certificate.',
  primaryLabel = 'Apply Now',
  primaryTo = '/programs',
  secondaryLabel = 'Explore Programs',
  secondaryTo = '/programs',
}) {
  return (
    <section className="section-pad">
      <div className="container-page">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="relative overflow-hidden rounded-3xl bg-ink-gradient px-8 py-16 sm:px-16 text-center"
        >
          <div className="absolute -top-24 -right-24 w-72 h-72 bg-brand-500/30 rounded-full blur-3xl" />
          <div className="absolute -bottom-24 -left-24 w-72 h-72 bg-violet-500/20 rounded-full blur-3xl" />
          <div className="relative">
            <span className="eyebrow text-violet-300">{eyebrow}</span>
            <h2 className="text-3xl sm:text-4xl font-bold text-white mt-4 max-w-2xl mx-auto">{title}</h2>
            <p className="text-ink-100/70 mt-4 max-w-xl mx-auto">{subtitle}</p>
            <div className="flex flex-wrap items-center justify-center gap-4 mt-8">
              <Link to={primaryTo} className="btn-primary">
                {primaryLabel} <FiArrowRight />
              </Link>
              <Link
                to={secondaryTo}
                className="inline-flex items-center gap-2 rounded-full border-2 border-white/20 text-white font-semibold px-6 py-3 hover:bg-white/10 transition-colors duration-300"
              >
                {secondaryLabel}
              </Link>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
