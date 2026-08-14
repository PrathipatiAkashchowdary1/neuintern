import { FiTarget, FiUsers, FiAward, FiTrendingUp } from 'react-icons/fi'
import FeatureCard from '../common/FeatureCard'

const features = [
  {
    icon: FiTarget,
    title: 'Outcome-first curriculum',
    description: 'Every week builds toward one real project — no filler modules, no busywork.',
  },
  {
    icon: FiUsers,
    title: 'Mentor-led sessions',
    description: 'Live weekly sessions with practitioners who review your actual work.',
  },
  {
    icon: FiAward,
    title: 'Verifiable certificate',
    description: 'Complete the program and earn a certificate you can add to your resume today.',
  },
  {
    icon: FiTrendingUp,
    title: 'Built for momentum',
    description: 'Four weeks is long enough to learn deeply and short enough to actually finish.',
  },
]

export default function WhyChoose() {
  return (
    <section className="section-pad">
      <div className="container-page">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <span className="eyebrow">Why NeuIntern</span>
          <h2 className="text-3xl sm:text-4xl font-bold mt-3">Built around one focused month</h2>
          <p className="text-ink-400 mt-4">
            No sprawling six-month tracks. Every NeuIntern program is scoped to four weeks so you commit,
            finish, and move forward with something real.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((f, i) => (
            <FeatureCard key={f.title} {...f} index={i} />
          ))}
        </div>
      </div>
    </section>
  )
}
