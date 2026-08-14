import { motion } from 'framer-motion'
import { FiCheckCircle } from 'react-icons/fi'

const benefits = [
  'Real, portfolio-ready projects — not toy exercises',
  'Weekly live mentor sessions with direct feedback',
  'Verified certificate on successful completion',
  'Flexible remote schedule around your college hours',
  'Peer community to build and debug alongside',
  'Resume-ready project writeups for interviews',
]

export default function Benefits() {
  return (
    <section className="section-pad">
      <div className="container-page grid lg:grid-cols-2 gap-14 items-center">
        <div>
          <span className="eyebrow">Internship Benefits</span>
          <h2 className="text-3xl sm:text-4xl font-bold mt-3 max-w-md">
            What you actually walk away with
          </h2>
          <p className="text-ink-400 mt-4 max-w-md leading-relaxed">
            Every program is built to leave you with proof of work, not just a line on your resume.
          </p>
        </div>
        <ul className="grid sm:grid-cols-2 gap-x-8 gap-y-5">
          {benefits.map((benefit, i) => (
            <motion.li
              key={benefit}
              initial={{ opacity: 0, x: 16 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.07 }}
              className="flex items-start gap-3"
            >
              <FiCheckCircle className="text-brand-500 shrink-0 mt-0.5" size={18} />
              <span className="text-sm text-ink-800">{benefit}</span>
            </motion.li>
          ))}
        </ul>
      </div>
    </section>
  )
}
