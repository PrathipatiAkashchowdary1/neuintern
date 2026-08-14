import { motion } from 'framer-motion'
import { FiTarget, FiCompass, FiTrendingUp } from 'react-icons/fi'
import Seo from '../seo/Seo'
import { breadcrumbSchema } from '../seo/schema'
import Breadcrumb from '../components/common/Breadcrumb'
import Timeline from '../components/common/Timeline'
import CTA from '../components/common/CTA'

const process = [
  { week: 'Step 1', title: 'Curriculum design', points: ['Mentors scope one real project per program', 'Weekly milestones map to hiring-relevant skills'] },
  { week: 'Step 2', title: 'Cohort onboarding', points: ['Students pick a track and get a 4-week schedule', 'Kickoff session sets expectations and tools'] },
  { week: 'Step 3', title: 'Guided building', points: ['Weekly live sessions plus async mentor feedback', 'Progress tracked against the program timeline'] },
  { week: 'Step 4', title: 'Review & certify', points: ['Final project reviewed by a mentor', 'Certificate issued on successful completion'] },
]

const team = [
  { name: 'Meera Kapoor', role: 'Founder & Curriculum Lead', photo: 'https://i.pravatar.cc/200?img=44' },
  { name: 'Aditya Rao', role: 'Head of Mentorship', photo: 'https://i.pravatar.cc/200?img=13' },
  { name: 'Ishita Bose', role: 'Program Design', photo: 'https://i.pravatar.cc/200?img=30' },
  { name: 'Farhan Sheikh', role: 'Partnerships', photo: 'https://i.pravatar.cc/200?img=14' },
]

export default function About() {
  return (
    <>
      <Seo
        title="About Us"
        description="Learn about NeuIntern's mission to make internships focused, real, and finishable in four weeks."
        path="/about"
        structuredData={breadcrumbSchema([{ name: 'Home', path: '/' }, { name: 'About', path: '/about' }])}
      />

      <section className="pt-32 pb-16">
        <div className="container-page">
          <Breadcrumb items={[{ name: 'Home', path: '/' }, { name: 'About', path: '/about' }]} />
          <div className="max-w-2xl mt-8">
            <span className="eyebrow">About NeuIntern</span>
            <h1 className="text-4xl sm:text-5xl font-bold mt-4">
              Internships built to actually get finished
            </h1>
            <p className="text-ink-400 mt-5 leading-relaxed">
              NeuIntern started from a simple observation: most student internships are either too long
              to commit to, or too shallow to matter on a resume. We build every program around a single
              real project, scoped to exactly four weeks, so students finish with something they can
              show — not just a certificate for showing up.
            </p>
          </div>
        </div>
      </section>

      <section className="section-pad pt-0">
        <div className="container-page grid sm:grid-cols-3 gap-6">
          {[
            { icon: FiTarget, title: 'Our Mission', text: 'Make real-world, skill-building internships accessible to every student, regardless of college or city.' },
            { icon: FiCompass, title: 'Our Vision', text: 'Become the most trusted 4-week bridge between classroom learning and industry-ready skills.' },
            { icon: FiTrendingUp, title: 'Future Goals', text: 'Expand into dashboards, live classes, and placement partnerships as we grow beyond Phase 1.' },
          ].map((item, i) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="rounded-3xl bg-white border border-ink-900/5 p-8 shadow-card"
            >
              <div className="w-12 h-12 rounded-2xl bg-brand-gradient-soft flex items-center justify-center text-brand-600">
                <item.icon size={22} />
              </div>
              <h3 className="font-semibold text-lg mt-5">{item.title}</h3>
              <p className="text-sm text-ink-400 mt-2 leading-relaxed">{item.text}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="section-pad bg-cloud-200">
        <div className="container-page">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <span className="eyebrow">Why NeuIntern</span>
            <h2 className="text-3xl sm:text-4xl font-bold mt-3">Our process, week by week</h2>
          </div>
          <div className="max-w-2xl mx-auto">
            <Timeline steps={process} />
          </div>
        </div>
      </section>

      <section className="section-pad">
        <div className="container-page">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <span className="eyebrow">Team</span>
            <h2 className="text-3xl sm:text-4xl font-bold mt-3">The people behind the programs</h2>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {team.map((member) => (
              <div key={member.name} className="text-center rounded-3xl bg-white border border-ink-900/5 p-7 shadow-card">
                <img
                  src={member.photo}
                  alt={member.name}
                  loading="lazy"
                  className="w-20 h-20 rounded-full object-cover mx-auto"
                  width={80}
                  height={80}
                />
                <h3 className="font-semibold mt-4">{member.name}</h3>
                <p className="text-xs text-ink-400 mt-1">{member.role}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <CTA />
    </>
  )
}
