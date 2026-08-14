import { motion } from 'framer-motion'

export default function FeatureCard({ icon: Icon, title, description, index = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay: index * 0.08 }}
      className="group rounded-3xl bg-white border border-ink-900/5 p-7 shadow-card hover:shadow-glass-lg hover:-translate-y-1 transition-all duration-300"
    >
      <div className="w-12 h-12 rounded-2xl bg-brand-gradient-soft flex items-center justify-center text-brand-600 group-hover:bg-brand-gradient group-hover:text-white transition-colors duration-300">
        <Icon size={22} />
      </div>
      <h3 className="text-lg font-semibold mt-5">{title}</h3>
      <p className="text-ink-400 text-sm mt-2 leading-relaxed">{description}</p>
    </motion.div>
  )
}
