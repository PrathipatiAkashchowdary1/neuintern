import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FiAlertCircle, FiCheckCircle, FiMail } from 'react-icons/fi'
import Seo from '../seo/Seo'
import { unsubscribe, resubscribe } from '../api/unsubscribe'

export default function Unsubscribe() {
  const [params] = useSearchParams()
  const token = params.get('token')
  const [status, setStatus] = useState('idle') // idle | working | done | undone | error
  const [error, setError] = useState('')

  const run = async (action, nextStatus) => {
    setStatus('working')
    setError('')
    try {
      await action(token)
      setStatus(nextStatus)
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.')
      setStatus('error')
    }
  }

  return (
    <>
      <Seo title="Unsubscribe" path="/unsubscribe" noindex />
      <section className="min-h-screen flex items-center justify-center pt-32 pb-20 px-4 bg-brand-gradient-soft">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md rounded-3xl bg-white border border-ink-900/5 shadow-glass-lg p-8"
        >
          <span className="eyebrow">Email preferences</span>

          {!token ? (
            <>
              <h1 className="text-2xl font-bold mt-2">This link isn&apos;t valid</h1>
              <p className="text-sm text-ink-400 mt-1">
                Open the unsubscribe link from the bottom of one of our emails, or contact us and we&apos;ll sort it out.
              </p>
              <Link to="/contact" className="btn-primary mt-6 inline-flex">Contact us</Link>
            </>
          ) : status === 'done' ? (
            <>
              <div className="flex items-start gap-2 bg-green-50 text-green-700 text-sm rounded-xl p-3 mt-5" role="status">
                <FiCheckCircle className="shrink-0 mt-0.5" size={16} />
                <span>You&apos;ve been unsubscribed from reminder emails.</span>
              </div>
              <p className="text-sm text-ink-400 mt-4">
                You won&apos;t get any more reminders. Emails about your own enrollment, such as your offer letter,
                receipt and certificate, will still arrive.
              </p>
              <div className="flex flex-wrap gap-3 mt-6">
                <Link to="/" className="btn-primary inline-flex">Back to Home</Link>
                <button type="button" onClick={() => run(resubscribe, 'undone')} className="btn-secondary">
                  Undo
                </button>
              </div>
            </>
          ) : status === 'undone' ? (
            <>
              <div className="flex items-start gap-2 bg-green-50 text-green-700 text-sm rounded-xl p-3 mt-5" role="status">
                <FiCheckCircle className="shrink-0 mt-0.5" size={16} />
                <span>Reminder emails are back on.</span>
              </div>
              <Link to="/" className="btn-primary mt-6 inline-flex">Back to Home</Link>
            </>
          ) : (
            <>
              <h1 className="text-2xl font-bold mt-2">Unsubscribe from reminders?</h1>
              <p className="text-sm text-ink-400 mt-1">
                We&apos;ll stop emailing you nudges to finish your task or pay for your certificate.
              </p>

              {status === 'error' && (
                <div className="flex items-start gap-2 bg-red-50 text-red-700 text-sm rounded-xl p-3 mt-5" role="alert">
                  <FiAlertCircle className="shrink-0 mt-0.5" size={16} />
                  <span>{error}</span>
                </div>
              )}

              <button
                type="button"
                onClick={() => run(unsubscribe, 'done')}
                disabled={status === 'working'}
                className="btn-primary mt-6 inline-flex items-center gap-2"
              >
                <FiMail /> {status === 'working' ? 'Working…' : 'Yes, unsubscribe me'}
              </button>
            </>
          )}
        </motion.div>
      </section>
    </>
  )
}
