import { motion } from 'framer-motion'
import Seo from '../seo/Seo'
import { breadcrumbSchema } from '../seo/schema'
import Breadcrumb from '../components/common/Breadcrumb'
import ReviewCard from '../components/common/ReviewCard'
import CTA from '../components/common/CTA'
import { testimonials } from '../data/testimonials'

export default function Reviews() {
  return (
    <>
      <Seo
        title="Student Reviews"
        description="Read what NeuIntern students say about their 4-week internship experience."
        path="/reviews"
        structuredData={breadcrumbSchema([{ name: 'Home', path: '/' }, { name: 'Reviews', path: '/reviews' }])}
      />

      <section className="pt-32 pb-16">
        <div className="container-page">
          <Breadcrumb items={[{ name: 'Home', path: '/' }, { name: 'Reviews', path: '/reviews' }]} />
          <div className="max-w-2xl mt-8">
            <span className="eyebrow">Student Reviews</span>
            <h1 className="text-4xl sm:text-5xl font-bold mt-4">What interns say about NeuIntern</h1>
          </div>
        </div>
      </section>

      <section className="pb-24">
        <div className="container-page grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {testimonials.map((review, i) => (
            <motion.div
              key={review.id}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: (i % 6) * 0.08 }}
            >
              <ReviewCard review={review} />
            </motion.div>
          ))}
        </div>
      </section>

      <CTA />
    </>
  )
}
