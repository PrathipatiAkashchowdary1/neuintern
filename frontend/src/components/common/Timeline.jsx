import { motion } from 'framer-motion'

// A weekly curriculum timeline — order genuinely carries information here
// (this is a real 4-week sequence), so numbering is appropriate.
export default function Timeline({ steps }) {
  return (
    <ol className="relative border-l-2 border-ink-900/10 ml-4">
      {steps.map((step, i) => (
        <motion.li
          key={step.week}
          initial={{ opacity: 0, x: -16 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: i * 0.1 }}
          className="mb-10 ml-8 last:mb-0"
        >
          <span className="absolute -left-[19px] flex items-center justify-center w-9 h-9 rounded-full bg-brand-gradient text-white font-mono text-xs font-semibold shadow-card">
            W{i + 1}
          </span>
          <p className="eyebrow">{step.week}</p>
          <h4 className="text-lg font-semibold mt-1">{step.title}</h4>
          <ul className="mt-3 space-y-1.5">
            {step.points.map((point) => (
              <li key={point} className="text-sm text-ink-400 flex gap-2">
                <span className="text-brand-500 mt-1">—</span>
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </motion.li>
      ))}
    </ol>
  )
}
