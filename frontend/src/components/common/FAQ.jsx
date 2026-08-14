import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FiPlus } from 'react-icons/fi'

export default function FAQ({ items, title = 'Frequently Asked Questions', subtitle }) {
  const [openIndex, setOpenIndex] = useState(0)

  return (
    <section className="section-pad">
      <div className="container-page max-w-3xl">
        <div className="text-center mb-12">
          <span className="eyebrow">FAQs</span>
          <h2 className="text-3xl sm:text-4xl font-bold mt-3">{title}</h2>
          {subtitle && <p className="text-ink-400 mt-3">{subtitle}</p>}
        </div>
        <div className="space-y-3">
          {items.map((item, i) => {
            const isOpen = openIndex === i
            return (
              <div key={item.q} className="rounded-2xl border border-ink-900/10 bg-white overflow-hidden">
                <button
                  className="w-full flex items-center justify-between gap-4 px-6 py-5 text-left"
                  onClick={() => setOpenIndex(isOpen ? -1 : i)}
                  aria-expanded={isOpen}
                >
                  <span className="font-semibold text-ink-900">{item.q}</span>
                  <FiPlus
                    className={`shrink-0 text-brand-600 transition-transform duration-300 ${isOpen ? 'rotate-45' : ''}`}
                  />
                </button>
                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3 }}
                    >
                      <p className="px-6 pb-5 text-ink-400 text-sm leading-relaxed">{item.a}</p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
