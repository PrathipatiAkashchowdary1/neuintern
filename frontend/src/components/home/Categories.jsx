import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FiCode, FiDatabase, FiShield, FiPenTool } from 'react-icons/fi'

const categories = [
  { icon: FiCode, name: 'Development', count: 5, to: '/programs?category=Development' },
  { icon: FiDatabase, name: 'Data & AI', count: 4, to: '/programs?category=Data+%26+AI' },
  { icon: FiShield, name: 'Security & Cloud', count: 3, to: '/programs?category=Security+%26+Cloud' },
  { icon: FiPenTool, name: 'Design & Marketing', count: 2, to: '/programs?category=Design+%26+Marketing' },
]

export default function Categories() {
  return (
    <section className="section-pad bg-cloud-200">
      <div className="container-page">
        <div className="flex flex-wrap items-end justify-between gap-4 mb-14">
          <div>
            <span className="eyebrow">Internship Categories</span>
            <h2 className="text-3xl sm:text-4xl font-bold mt-3">Find your track</h2>
          </div>
          <Link to="/programs" className="text-brand-600 font-semibold text-sm hover:underline">
            View all 16 programs →
          </Link>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {categories.map((cat, i) => (
            <motion.div
              key={cat.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08 }}
            >
              <Link
                to={cat.to}
                className="group block rounded-3xl bg-white border border-ink-900/5 p-7 shadow-card hover:shadow-glass-lg hover:-translate-y-1 transition-all duration-300"
              >
                <div className="w-12 h-12 rounded-2xl bg-brand-gradient-soft flex items-center justify-center text-brand-600 group-hover:bg-brand-gradient group-hover:text-white transition-colors duration-300">
                  <cat.icon size={22} />
                </div>
                <h3 className="font-semibold mt-5">{cat.name}</h3>
                <p className="text-sm text-ink-400 mt-1">{cat.count} programs</p>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
