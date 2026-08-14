import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { motion, AnimatePresence } from 'framer-motion'
import { FiX, FiCheckCircle, FiAlertCircle, FiLock } from 'react-icons/fi'
import useRazorpayScript from '../../hooks/useRazorpayScript'
import { createOrder, verifyPayment } from '../../api/payments'

export default function EnrollModal({ program, onClose }) {
  const razorpayReady = useRazorpayScript()
  const [step, setStep] = useState('form') // form | processing | success | error
  const [errorMessage, setErrorMessage] = useState('')

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm()

  const openCheckout = async (applicant) => {
    setStep('processing')
    setErrorMessage('')

    try {
      const order = await createOrder({
        programSlug: program.slug,
        name: applicant.name,
        email: applicant.email,
        phone: applicant.phone,
      })

      if (!razorpayReady || !window.Razorpay) {
        throw new Error('Payment gateway failed to load. Please check your connection and try again.')
      }

      const rzp = new window.Razorpay({
        key: order.keyId,
        amount: order.amount,
        currency: order.currency,
        name: 'NeuIntern',
        description: `${order.programTitle} — 4-Week Internship`,
        order_id: order.orderId,
        prefill: { name: applicant.name, email: applicant.email, contact: applicant.phone },
        theme: { color: '#4F46E5' },
        handler: async (response) => {
          try {
            await verifyPayment({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
              enrollmentId: order.enrollmentId,
            })
            setStep('success')
          } catch (err) {
            setErrorMessage(err.message || 'Payment succeeded but verification failed. Contact support with your payment ID.')
            setStep('error')
          }
        },
        modal: {
          ondismiss: () => setStep('form'),
        },
      })

      rzp.on('payment.failed', (resp) => {
        setErrorMessage(resp.error?.description || 'Payment failed. Please try again.')
        setStep('error')
      })

      rzp.open()
    } catch (err) {
      setErrorMessage(err.message || 'Could not start checkout. Please try again shortly.')
      setStep('error')
    }
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[100] bg-ink-900/50 backdrop-blur-sm flex items-center justify-center p-4"
        onClick={onClose}
        role="dialog"
        aria-modal="true"
        aria-label={`Enroll in ${program.title}`}
      >
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.97 }}
          transition={{ duration: 0.25 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-white rounded-3xl w-full max-w-md p-7 relative shadow-glass-lg max-h-[90vh] overflow-y-auto"
        >
          <button
            onClick={onClose}
            aria-label="Close"
            className="absolute top-5 right-5 w-9 h-9 rounded-full flex items-center justify-center text-ink-400 hover:bg-cloud-200 transition-colors"
          >
            <FiX size={18} />
          </button>

          {step === 'success' ? (
            <div className="text-center py-8">
              <FiCheckCircle className="text-brand-500 mx-auto" size={44} />
              <h3 className="text-xl font-bold mt-4">You&apos;re enrolled!</h3>
              <p className="text-ink-400 mt-2 text-sm">
                Payment confirmed for <span className="font-medium text-ink-800">{program.title}</span>. We&apos;ve sent
                joining details to your email.
              </p>
              <button onClick={onClose} className="btn-primary mt-6">
                Done
              </button>
            </div>
          ) : (
            <>
              <span className="eyebrow">Enroll Now</span>
              <h3 className="text-xl font-bold mt-2">{program.title}</h3>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-2xl font-bold text-brand-600">₹{program.price?.toLocaleString('en-IN')}</span>
                <span className="text-xs text-ink-400">one-time · {program.duration}</span>
              </div>

              {step === 'error' && (
                <div className="flex items-start gap-2 bg-red-50 text-red-700 text-sm rounded-xl p-3 mt-5">
                  <FiAlertCircle className="shrink-0 mt-0.5" size={16} />
                  <span>{errorMessage}</span>
                </div>
              )}

              <form onSubmit={handleSubmit(openCheckout)} className="space-y-4 mt-6" noValidate>
                <div>
                  <label htmlFor="enroll-name" className="text-sm font-medium text-ink-800">Full name</label>
                  <input
                    id="enroll-name"
                    {...register('name', { required: 'Please enter your name' })}
                    className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
                    placeholder="Jane Doe"
                  />
                  {errors.name && <p className="text-red-500 text-xs mt-1">{errors.name.message}</p>}
                </div>
                <div>
                  <label htmlFor="enroll-email" className="text-sm font-medium text-ink-800">Email</label>
                  <input
                    id="enroll-email"
                    type="email"
                    {...register('email', {
                      required: 'Please enter your email',
                      pattern: { value: /^\S+@\S+\.\S+$/, message: 'Enter a valid email' },
                    })}
                    className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
                    placeholder="jane@email.com"
                  />
                  {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>}
                </div>
                <div>
                  <label htmlFor="enroll-phone" className="text-sm font-medium text-ink-800">Phone number</label>
                  <input
                    id="enroll-phone"
                    type="tel"
                    {...register('phone', {
                      required: 'Please enter your phone number',
                      minLength: { value: 8, message: 'Enter a valid phone number' },
                    })}
                    className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
                    placeholder="+91 90000 00000"
                  />
                  {errors.phone && <p className="text-red-500 text-xs mt-1">{errors.phone.message}</p>}
                </div>

                <button type="submit" disabled={step === 'processing'} className="btn-primary w-full">
                  {step === 'processing' ? 'Opening secure checkout…' : `Pay ₹${program.price?.toLocaleString('en-IN')} & Enroll`}
                </button>
                <p className="flex items-center justify-center gap-1.5 text-xs text-ink-400">
                  <FiLock size={12} /> Payments secured by Razorpay
                </p>
              </form>
            </>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
