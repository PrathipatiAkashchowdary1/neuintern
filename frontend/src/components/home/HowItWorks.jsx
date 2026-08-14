import { motion } from 'framer-motion'
import { FiSearch, FiEdit3, FiPlayCircle, FiAward } from 'react-icons/fi'

const steps = [
  { icon: FiSearch, title: 'Choose a program', description: 'Browse 16 tracks and pick the one that matches your goal.' },
  { icon: FiEdit3, title: 'Apply in minutes', description: 'Fill a short form — no lengthy shortlisting process.' },
  { icon: FiPlayCircle, title: 'Learn for 4 weeks', description: 'Attend weekly live sessions and build a real project.' },
  { icon: FiAward, title: 'Get certified', description: 'Submit your final project and receive your certificate.' },
]

export default function HowItWorks() {
  return (
    <section className="section-pad">
      <div className="container-page">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <span className="eyebrow">How It Works</span>
          <h2 className="text-3xl sm:text-4xl font-bold mt-3">From sign-up to certificate</h2>
        </div>
        <div className="relative grid sm:grid-cols-2 lg:grid-cols-4 gap-8">
          <div className="hidden lg:block absolute top-8 left-0 right-0 h-0.5 bg-ink-900/10" />
          {steps.map((step, i) => (
            <motion.div
              key={step.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="relative text-center"
            >
              <div className="relative z-10 w-16 h-16 rounded-2xl bg-brand-gradient text-white flex items-center justify-center mx-auto shadow-card">
                <step.icon size={24} />
              </div>
              <h3 className="font-semibold mt-5">{step.title}</h3>
              <p className="text-sm text-ink-400 mt-2 max-w-[220px] mx-auto leading-relaxed">{step.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
