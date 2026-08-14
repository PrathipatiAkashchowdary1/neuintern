import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { motion } from 'framer-motion'
import { FiX, FiAlertCircle } from 'react-icons/fi'

const CATEGORIES = ['Development', 'Data & AI', 'Security & Cloud', 'Design & Marketing']

export default function ProgramEditorModal({ program, onClose, onSave }) {
  const isNew = !program
  const [serverError, setServerError] = useState('')

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    defaultValues: {
      slug: program?.slug || '',
      title: program?.title || '',
      category: program?.category || CATEGORIES[0],
      tagline: program?.tagline || '',
      price: program?.price ?? 1499,
      duration: program?.duration || '4 Weeks',
      is_active: program?.isActive ?? true,
    },
  })

  const onSubmit = async (formData) => {
    setServerError('')
    try {
      await onSave({
        ...formData,
        price: Number(formData.price),
        is_active: formData.is_active === true || formData.is_active === 'true',
      })
      onClose()
    } catch (err) {
      setServerError(err.message || 'Could not save this program.')
    }
  }

  return (
    <div
      className="fixed inset-0 z-[100] bg-ink-900/50 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-3xl w-full max-w-lg p-7 relative shadow-glass-lg max-h-[90vh] overflow-y-auto"
      >
        <button
          onClick={onClose}
          aria-label="Close"
          className="absolute top-5 right-5 w-9 h-9 rounded-full flex items-center justify-center text-ink-400 hover:bg-cloud-200 transition-colors"
        >
          <FiX size={18} />
        </button>

        <h3 className="text-xl font-bold">{isNew ? 'Add Program' : `Edit ${program.title}`}</h3>

        {serverError && (
          <div className="flex items-start gap-2 bg-red-50 text-red-700 text-sm rounded-xl p-3 mt-4">
            <FiAlertCircle className="shrink-0 mt-0.5" size={16} />
            <span>{serverError}</span>
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-5" noValidate>
          {isNew && (
            <div>
              <label className="text-sm font-medium text-ink-800">Slug</label>
              <input
                {...register('slug', { required: 'Slug is required' })}
                className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-2.5 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
                placeholder="blockchain-development"
              />
              {errors.slug && <p className="text-red-500 text-xs mt-1">{errors.slug.message}</p>}
            </div>
          )}
          <div>
            <label className="text-sm font-medium text-ink-800">Title</label>
            <input
              {...register('title', { required: 'Title is required' })}
              className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-2.5 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
            />
            {errors.title && <p className="text-red-500 text-xs mt-1">{errors.title.message}</p>}
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-ink-800">Category</label>
              <select
                {...register('category')}
                className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-2.5 text-sm bg-white focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-ink-800">Price (₹)</label>
              <input
                type="number"
                {...register('price', { required: true, min: 0 })}
                className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-2.5 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
              />
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-ink-800">Tagline</label>
            <textarea
              rows={2}
              {...register('tagline')}
              className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-2.5 text-sm resize-none focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
            />
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="is_active" {...register('is_active')} className="w-4 h-4 accent-brand-600" />
            <label htmlFor="is_active" className="text-sm text-ink-800">Active (visible in public catalog)</label>
          </div>

          <button type="submit" disabled={isSubmitting} className="btn-primary w-full">
            {isSubmitting ? 'Saving…' : isNew ? 'Create Program' : 'Save Changes'}
          </button>
        </form>
      </motion.div>
    </div>
  )
}
