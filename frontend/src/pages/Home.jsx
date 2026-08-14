import Seo from '../seo/Seo'
import { organizationSchema, websiteSchema } from '../seo/schema'
import Hero from '../components/home/Hero'
import WhyChoose from '../components/home/WhyChoose'
import Categories from '../components/home/Categories'
import Benefits from '../components/home/Benefits'
import HowItWorks from '../components/home/HowItWorks'
import SuccessStories from '../components/home/SuccessStories'
import CertificatePreview from '../components/home/CertificatePreview'
import FAQ from '../components/common/FAQ'
import CTA from '../components/common/CTA'
import { generalFaqs } from '../data/faqs'

export default function Home() {
  return (
    <>
      <Seo
        title="4-Week Internship Programs for Students"
        description="NeuIntern offers focused 4-week internship programs in web development, AI, data science, cloud, cyber security and more — real projects, verified certificates."
        keywords="internship, 4 week internship, student internship, web development internship, AI internship, NeuIntern"
        path="/"
        structuredData={[organizationSchema, websiteSchema]}
      />
      <Hero />
      <WhyChoose />
      <Categories />
      <Benefits />
      <HowItWorks />
      <SuccessStories />
      <CertificatePreview />
      <FAQ items={generalFaqs} />
      <CTA />
    </>
  )
}
