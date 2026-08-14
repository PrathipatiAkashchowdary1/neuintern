import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FiAlertCircle, FiCheckCircle, FiMail, FiArrowRight } from 'react-icons/fi'
import Seo from '../seo/Seo'
import { forgotPassword, resetPassword } from '../api/auth'

export default function ForgotPassword() {
  const navigate = useNavigate()
  const [step, setStep] = useState('email') // 'email' -> 'reset' -> done (redirects)
  const [email, setEmail] = useState('')
  const [devOtp, setDevOtp] = useState('')
  const [serverError, setServerError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  return (
    <>
      <Seo title="Forgot Password" path="/forgot-password" noindex />
      <section className="min-h-screen flex items-center justify-center pt-32 pb-20 px-4 bg-brand-gradient-soft">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md rounded-3xl bg-white border border-ink-900/5 shadow-glass-lg p-8"
        >
          <span className="eyebrow">Reset password</span>
          <h1 className="text-2xl font-bold mt-2">
            {step === 'email' ? 'Forgot your password?' : 'Enter your new password'}
          </h1>
          <p className="text-sm text-ink-400 mt-1">
            {step === 'email'
              ? "We'll send a reset code to your email."
              : `Enter the code we sent to ${email} along with your new password.`}
          </p>

          {serverError && (
            <div className="flex items-start gap-2 bg-red-50 text-red-700 text-sm rounded-xl p-3 mt-5">
              <FiAlertCircle className="shrink-0 mt-0.5" size={16} />
              <span>{serverError}</span>
            </div>
          )}
          {successMessage && (
            <div className="flex items-start gap-2 bg-brand-50 text-brand-700 text-sm rounded-xl p-3 mt-5">
              <FiCheckCircle className="shrink-0 mt-0.5" size={16} />
              <span>{successMessage}</span>
            </div>
          )}

          {step === 'email' && (
            <EmailStep
              onSent={(sentEmail, otp) => {
                setEmail(sentEmail)
                setDevOtp(otp || '')
                setStep('reset')
              }}
              onError={setServerError}
              clearError={() => setServerError('')}
            />
          )}

          {step === 'reset' && (
            <ResetStep
              email={email}
              devOtp={devOtp}
              onDone={() => {
                setSuccessMessage('Password updated — redirecting to login…')
                setTimeout(() => navigate('/login', { replace: true }), 1500)
              }}
              onResend={async () => {
                setServerError('')
                try {
                  const result = await forgotPassword(email)
                  setDevOtp(result.devOtp || '')
                } catch (err) {
                  setServerError(err.message || 'Could not resend the code.')
                }
              }}
              onError={setServerError}
              clearError={() => setServerError('')}
            />
          )}

          <p className="text-sm text-ink-400 text-center mt-6">
            Remembered your password?{' '}
            <Link to="/login" className="text-brand-600 font-semibold hover:underline">
              Log in
            </Link>
          </p>
        </motion.div>
      </section>
    </>
  )
}

function EmailStep({ onSent, onError, clearError }) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm()

  const onSubmit = async ({ email }) => {
    clearError()
    try {
      const result = await forgotPassword(email)
      onSent(email, result.devOtp)
    } catch (err) {
      onError(err.message || 'Could not send a reset code. Please try again.')
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-6" noValidate>
      <div>
        <label htmlFor="forgot-email" className="text-sm font-medium text-ink-800">Email</label>
        <input
          id="forgot-email"
          type="email"
          {...register('email', {
            required: 'Email is required',
            pattern: { value: /^\S+@\S+\.\S+$/, message: 'Enter a valid email' },
          })}
          className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
          placeholder="jane@email.com"
        />
        {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>}
      </div>
      <button type="submit" disabled={isSubmitting} className="btn-primary w-full">
        {isSubmitting ? 'Sending code…' : <>Send Reset Code <FiMail /></>}
      </button>
    </form>
  )
}

function ResetStep({ email, devOtp, onDone, onResend, onError, clearError }) {
  const [resending, setResending] = useState(false)
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm({ defaultValues: { otp: devOtp || '' } })

  const onSubmit = async ({ otp, newPassword }) => {
    clearError()
    try {
      await resetPassword(email, otp, newPassword)
      onDone()
    } catch (err) {
      onError(err.message || 'Invalid or expired code. Please try again.')
    }
  }

  const handleResend = async () => {
    setResending(true)
    try {
      await onResend()
    } finally {
      setResending(false)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-6" noValidate>
      {devOtp && (
        <div className="flex items-start gap-2 bg-brand-50 text-brand-700 text-sm rounded-xl p-3">
          <FiCheckCircle className="shrink-0 mt-0.5" size={16} />
          <span>Dev mode (no email configured yet): your code is <strong>{devOtp}</strong>.</span>
        </div>
      )}
      <div>
        <label htmlFor="reset-otp" className="text-sm font-medium text-ink-800">Reset code</label>
        <input
          id="reset-otp"
          inputMode="numeric"
          maxLength={6}
          {...register('otp', { required: 'Enter the code we sent you' })}
          className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm tracking-[0.3em] text-center focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
          placeholder="000000"
        />
        {errors.otp && <p className="text-red-500 text-xs mt-1">{errors.otp.message}</p>}
      </div>
      <div>
        <label htmlFor="newPassword" className="text-sm font-medium text-ink-800">New password</label>
        <input
          id="newPassword"
          type="password"
          {...register('newPassword', {
            required: 'Please enter a new password',
            minLength: { value: 6, message: 'Password must be at least 6 characters' },
          })}
          className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
          placeholder="At least 6 characters"
        />
        {errors.newPassword && <p className="text-red-500 text-xs mt-1">{errors.newPassword.message}</p>}
      </div>
      <div>
        <label htmlFor="confirmPassword" className="text-sm font-medium text-ink-800">Confirm new password</label>
        <input
          id="confirmPassword"
          type="password"
          {...register('confirmPassword', {
            required: 'Please confirm your new password',
            validate: (value) => value === watch('newPassword') || 'Passwords do not match',
          })}
          className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
          placeholder="Re-enter your new password"
        />
        {errors.confirmPassword && <p className="text-red-500 text-xs mt-1">{errors.confirmPassword.message}</p>}
      </div>
      <button type="submit" disabled={isSubmitting} className="btn-primary w-full">
        {isSubmitting ? 'Updating…' : <>Reset Password <FiArrowRight /></>}
      </button>
      <button type="button" onClick={handleResend} disabled={resending} className="text-sm text-brand-600 font-medium hover:underline w-full text-center">
        {resending ? 'Resending…' : 'Resend code'}
      </button>
    </form>
  )
}