import { useState } from 'react'
import { FiLock, FiAlertCircle, FiCreditCard } from 'react-icons/fi'
import useRazorpayScript from '../../hooks/useRazorpayScript'
import { createCertificateOrder, verifyCertificatePayment } from '../../api/enrollments'

export default function CertificatePayment({ enrollment, onPaid }) {
  const razorpayReady = useRazorpayScript()
  const [status, setStatus] = useState('idle') // idle | processing | error
  const [errorMessage, setErrorMessage] = useState('')

  const startPayment = async () => {
    setStatus('processing')
    setErrorMessage('')

    try {
      const order = await createCertificateOrder(enrollment.id)

      if (!razorpayReady || !window.Razorpay) {
        throw new Error('Payment gateway failed to load. Please check your connection and try again.')
      }

      const rzp = new window.Razorpay({
        key: order.keyId,
        amount: order.amount,
        currency: order.currency,
        name: 'NeuIntern',
        description: `Certificate fee — ${enrollment.programTitle}`,
        order_id: order.orderId,
        prefill: { name: enrollment.name, email: enrollment.email, contact: enrollment.phone },
        theme: { color: '#00ABBC' },
        handler: async (response) => {
          try {
            const result = await verifyCertificatePayment(enrollment.id, {
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
              enrollmentId: order.enrollmentId,
            })
            onPaid(result.data)
          } catch (err) {
            setErrorMessage(err.message || 'Payment succeeded but verification failed. Contact support with your payment ID.')
            setStatus('error')
          }
        },
        modal: { ondismiss: () => setStatus('idle') },
      })

      rzp.on('payment.failed', (resp) => {
        setErrorMessage(resp.error?.description || 'Payment failed. Please try again.')
        setStatus('error')
      })

      rzp.open()
    } catch (err) {
      setErrorMessage(err.message || 'Could not start checkout. Please try again shortly.')
      setStatus('error')
    }
  }

  return (
    <div className="rounded-3xl bg-white border border-ink-900/10 shadow-card p-7">
      <h3 className="font-semibold text-lg">Certificate Fee</h3>
      <p className="text-sm text-ink-400 mt-2">
        A one-time ₹150 processing fee unlocks your verified completion certificate.
      </p>

      {status === 'error' && (
        <div className="flex items-start gap-2 bg-red-50 text-red-700 text-sm rounded-xl p-3 mt-4">
          <FiAlertCircle className="shrink-0 mt-0.5" size={16} />
          <span>{errorMessage}</span>
        </div>
      )}

      <div className="flex items-baseline gap-2 mt-5">
        <span className="text-3xl font-bold text-brand-600">₹150</span>
        <span className="text-xs text-ink-400">one-time</span>
      </div>

      <button
        onClick={startPayment}
        disabled={status === 'processing'}
        className="btn-primary w-full sm:w-auto mt-5"
      >
        {status === 'processing' ? 'Opening secure checkout…' : (
          <>
            <FiCreditCard /> Pay ₹150 & Unlock Certificate
          </>
        )}
      </button>
      <p className="flex items-center gap-1.5 text-xs text-ink-400 mt-3">
        <FiLock size={12} /> Payments secured by Razorpay
      </p>
    </div>
  )
}
