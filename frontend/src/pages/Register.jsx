import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FiUserPlus, FiAlertCircle, FiMail, FiCheckCircle, FiArrowRight } from 'react-icons/fi'
import Seo from '../seo/Seo'
import { useAuth } from '../context/AuthContext'
import { sendOtp, verifyOtp } from '../api/auth'

const DEGREES = ['B.Tech', 'B.E.', 'BCA', 'B.Sc', 'M.Tech', 'MCA', 'M.Sc', 'Other']
const YEARS = ['1st Year', '2nd Year', '3rd Year', '4th Year', 'Final Year', 'Graduated']

export default function Register() {
  const { register: registerUser } = useAuth()
  const navigate = useNavigate()
  const [serverError, setServerError] = useState('')

  // Steps: 'email' -> enter + send code, 'otp' -> verify code, 'details' -> rest of the form
  const [step, setStep] = useState('email')
  const [email, setEmail] = useState('')
  const [devOtp, setDevOtp] = useState('') // only ever set when SMTP isn't configured server-side

  return (
    <>
      <Seo title="Create Account" path="/register" description="Register for a NeuIntern student account to enroll in a 4-week internship." />
      <section className="min-h-screen flex items-center justify-center pt-32 pb-20 px-4 bg-brand-gradient-soft">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-xl rounded-3xl bg-white border border-ink-900/5 shadow-glass-lg p-8"
        >
          <span className="eyebrow">Join NeuIntern</span>
          <h1 className="text-2xl font-bold mt-2">Create your student account</h1>
          <p className="text-sm text-ink-400 mt-1">
            {step === 'email' && "First, let's verify your email address."}
            {step === 'otp' && `Enter the code we sent to ${email}.`}
            {step === 'details' && 'Email verified — just a few more details.'}
          </p>

          {serverError && (
            <div className="flex items-start gap-2 bg-red-50 text-red-700 text-sm rounded-xl p-3 mt-5">
              <FiAlertCircle className="shrink-0 mt-0.5" size={16} />
              <span>{serverError}</span>
            </div>
          )}

          {step === 'email' && (
            <EmailStep
              onSent={(sentEmail, otp) => {
                setEmail(sentEmail)
                setDevOtp(otp || '')
                setStep('otp')
              }}
              onError={setServerError}
              clearError={() => setServerError('')}
            />
          )}

          {step === 'otp' && (
            <OtpStep
              email={email}
              devOtp={devOtp}
              onVerified={() => setStep('details')}
              onBack={() => setStep('email')}
              onError={setServerError}
              clearError={() => setServerError('')}
            />
          )}

          {step === 'details' && (
            <DetailsStep
              email={email}
              onSubmitted={() => navigate('/dashboard', { replace: true })}
              onError={setServerError}
              clearError={() => setServerError('')}
              registerUser={registerUser}
            />
          )}

          <p className="text-sm text-ink-400 text-center mt-6">
            Already have an account?{' '}
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
      const result = await sendOtp(email, 'register')
      onSent(email, result.devOtp)
    } catch (err) {
      onError(err.message || 'Could not send a verification code. Please try again.')
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-6" noValidate>
      <div>
        <label htmlFor="reg-email" className="text-sm font-medium text-ink-800">Email</label>
        <input
          id="reg-email"
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
        {isSubmitting ? 'Sending code…' : <>Send Verification Code <FiMail /></>}
      </button>
    </form>
  )
}

function OtpStep({ email, devOtp, onVerified, onBack, onError, clearError }) {
  const [resending, setResending] = useState(false)
  const [resendMessage, setResendMessage] = useState('')
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ defaultValues: { otp: devOtp || '' } })

  const onSubmit = async ({ otp }) => {
    clearError()
    try {
      await verifyOtp(email, otp, 'register')
      onVerified()
    } catch (err) {
      onError(err.message || 'Invalid or expired code. Please try again.')
    }
  }

  const handleResend = async () => {
    setResending(true)
    setResendMessage('')
    try {
      await sendOtp(email, 'register')
      setResendMessage('A new code has been sent.')
    } catch (err) {
      onError(err.message || 'Could not resend the code.')
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
        <label htmlFor="reg-otp" className="text-sm font-medium text-ink-800">Verification code</label>
        <input
          id="reg-otp"
          inputMode="numeric"
          maxLength={6}
          {...register('otp', { required: 'Enter the code we sent you' })}
          className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm tracking-[0.3em] text-center focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
          placeholder="000000"
        />
        {errors.otp && <p className="text-red-500 text-xs mt-1">{errors.otp.message}</p>}
      </div>
      <button type="submit" disabled={isSubmitting} className="btn-primary w-full">
        {isSubmitting ? 'Verifying…' : <>Verify Email <FiArrowRight /></>}
      </button>
      <div className="flex items-center justify-between text-sm">
        <button type="button" onClick={onBack} className="text-ink-400 hover:text-ink-800">
          Use a different email
        </button>
        <button type="button" onClick={handleResend} disabled={resending} className="text-brand-600 font-medium hover:underline">
          {resending ? 'Resending…' : 'Resend code'}
        </button>
      </div>
      {resendMessage && <p className="text-xs text-ink-400 text-center">{resendMessage}</p>}
    </form>
  )
}

function DetailsStep({ email, onSubmitted, onError, clearError, registerUser }) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm()

  const onSubmit = async (formData) => {
    clearError()
    try {
      await registerUser({
        fullName: formData.fullName,
        email,
        phone: formData.phone,
        degree: formData.degree,
        branch: formData.branch,
        currentYear: formData.currentYear,
        password: formData.password,
      })
      onSubmitted()
    } catch (err) {
      onError(err.message || 'Could not create your account. Please try again.')
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-6" noValidate>
      <div className="flex items-center gap-2 bg-brand-50 text-brand-700 text-sm rounded-xl p-3">
        <FiCheckCircle className="shrink-0" size={16} />
        <span>{email} verified</span>
      </div>

      <div>
        <label htmlFor="fullName" className="text-sm font-medium text-ink-800">Full name</label>
        <input
          id="fullName"
          {...register('fullName', { required: 'Full name is required' })}
          className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
          placeholder="Jane Doe"
        />
        {errors.fullName && <p className="text-red-500 text-xs mt-1">{errors.fullName.message}</p>}
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <div>
          <label htmlFor="phone" className="text-sm font-medium text-ink-800">Phone number</label>
          <input
            id="phone"
            type="tel"
            {...register('phone', {
              required: 'Phone number is required',
              validate: (value) => {
                const cleaned = value.replace(/[\s\-()]/g, '')
                const digits = cleaned.startsWith('+91')
                  ? cleaned.slice(3)
                  : cleaned.startsWith('91') && cleaned.length === 12
                    ? cleaned.slice(2)
                    : cleaned.startsWith('0') && cleaned.length === 11
                      ? cleaned.slice(1)
                      : cleaned
                return /^[6-9]\d{9}$/.test(digits) || 'Enter a valid 10-digit Indian mobile number'
              },
            })}
            className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
            placeholder="+91 90000 00000"
          />
          {errors.phone && <p className="text-red-500 text-xs mt-1">{errors.phone.message}</p>}
        </div>
        <div>
          <label htmlFor="degree" className="text-sm font-medium text-ink-800">Degree</label>
          <select
            id="degree"
            {...register('degree', { required: 'Please select your degree' })}
            className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100 bg-white"
            defaultValue=""
          >
            <option value="" disabled>Select degree</option>
            {DEGREES.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
          {errors.degree && <p className="text-red-500 text-xs mt-1">{errors.degree.message}</p>}
        </div>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        <div>
          <label htmlFor="branch" className="text-sm font-medium text-ink-800">Branch / Stream</label>
          <input
            id="branch"
            {...register('branch', { required: 'Branch is required' })}
            className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
            placeholder="Computer Science"
          />
          {errors.branch && <p className="text-red-500 text-xs mt-1">{errors.branch.message}</p>}
        </div>
        <div>
          <label htmlFor="currentYear" className="text-sm font-medium text-ink-800">Current year</label>
          <select
            id="currentYear"
            {...register('currentYear', { required: 'Please select your current year' })}
            className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100 bg-white"
            defaultValue=""
          >
            <option value="" disabled>Select year</option>
            {YEARS.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
          {errors.currentYear && <p className="text-red-500 text-xs mt-1">{errors.currentYear.message}</p>}
        </div>
      </div>

      <div>
        <label htmlFor="password" className="text-sm font-medium text-ink-800">Password</label>
        <input
          id="password"
          type="password"
          {...register('password', {
            required: 'Password is required',
            minLength: { value: 6, message: 'Password must be at least 6 characters' },
          })}
          className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
          placeholder="At least 6 characters"
        />
        {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>}
      </div>

      <button type="submit" disabled={isSubmitting} className="btn-primary w-full">
        {isSubmitting ? 'Creating account…' : <>Create Account <FiUserPlus /></>}
      </button>
    </form>
  )
}