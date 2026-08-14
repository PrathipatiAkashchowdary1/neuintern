import { Link } from 'react-router-dom'
import { FiArrowLeft } from 'react-icons/fi'
import Seo from '../seo/Seo'

export default function NotFound() {
  return (
    <>
      <Seo title="Page Not Found" path="/404" noindex />
      <section className="min-h-[70vh] flex items-center justify-center pt-24">
        <div className="container-page text-center">
          <p className="font-mono text-brand-600 font-semibold tracking-widest">ERROR 404</p>
          <h1 className="text-4xl sm:text-5xl font-bold mt-4">This page didn&apos;t make the cut</h1>
          <p className="text-ink-400 mt-4 max-w-md mx-auto">
            The page you're looking for may have moved or doesn't exist. Let's get you back on track.
          </p>
          <Link to="/" className="btn-primary mt-8 inline-flex">
            <FiArrowLeft /> Back to Home
          </Link>
        </div>
      </section>
    </>
  )
}
