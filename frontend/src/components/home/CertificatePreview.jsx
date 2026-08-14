import { Link } from 'react-router-dom'
import CertificateCard from '../common/CertificateCard'

export default function CertificatePreview() {
  return (
    <section className="section-pad bg-cloud-200">
      <div className="container-page">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <span className="eyebrow">Certificate Preview</span>
          <h2 className="text-3xl sm:text-4xl font-bold mt-3">Proof you can put to work</h2>
          <p className="text-ink-400 mt-4">
            A shareable certificate issued the moment you complete your final project review.
          </p>
        </div>
        <div className="max-w-2xl mx-auto">
          <CertificateCard />
        </div>
        <div className="text-center mt-8">
          <Link to="/certificate" className="text-brand-600 font-semibold text-sm hover:underline">
            Learn more about certification →
          </Link>
        </div>
      </div>
    </section>
  )
}
