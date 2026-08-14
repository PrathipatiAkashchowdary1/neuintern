import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FiLogIn, FiAlertCircle } from 'react-icons/fi'
import Seo from '../seo/Seo'
import { useAuth } from '../context/AuthContext'


export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [serverError, setServerError] = useState('')

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm()

  const onSubmit = async (formData) => {
    setServerError('')
    try {
      const user = await login(formData)
      const redirectTo = location.state?.from || (user.role === 'admin' ? '/admin' : '/dashboard')
      navigate(redirectTo, { replace: true })
    } catch (err) {
      setServerError(err.message || 'Invalid email or password')
    }
  }

  return (
    <>
      <Seo title="Log In" path="/login" description="Log in to your NeuIntern student dashboard." />
      <section className="min-h-screen flex items-center justify-center pt-32 pb-20 px-4 bg-brand-gradient-soft">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md rounded-3xl bg-white border border-ink-900/5 shadow-glass-lg p-8"
        >
          <span className="eyebrow">Welcome back</span>
          <h1 className="text-2xl font-bold mt-2">Log in to NeuIntern</h1>
          <p className="text-sm text-ink-400 mt-1">Access your dashboard, task submissions, and certificate.</p>

          {serverError && (
            <div className="flex items-start gap-2 bg-red-50 text-red-700 text-sm rounded-xl p-3 mt-5">
              <FiAlertCircle className="shrink-0 mt-0.5" size={16} />
              <span>{serverError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-6" noValidate>
            <div>
              <label htmlFor="email" className="text-sm font-medium text-ink-800">Email</label>
              <input
                id="email"
                type="email"
                {...register('email', { required: 'Email is required' })}
                className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
                placeholder="you@email.com"
              />
              {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>}
            </div>
            <div>
              <div className="flex items-center justify-between">
                <label htmlFor="password" className="text-sm font-medium text-ink-800">Password</label>
                <Link to="/forgot-password" className="text-xs text-brand-600 font-medium hover:underline">
                  Forgot password?
                </Link>
              </div>
              <input
                id="password"
                type="password"
                {...register('password', { required: 'Password is required' })}
                className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
                placeholder="••••••••"
              />
              {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>}
            </div>
            <button type="submit" disabled={isSubmitting} className="btn-primary w-full">
              {isSubmitting ? 'Logging in…' : <>Log In <FiLogIn /></>}
            </button>
          </form>

          <p className="text-sm text-ink-400 text-center mt-6">
            New to NeuIntern?{' '}
            <Link to="/register" className="text-brand-600 font-semibold hover:underline">
              Create an account
            </Link>
          </p>
        </motion.div>
      </section>
    </>
  )
}
