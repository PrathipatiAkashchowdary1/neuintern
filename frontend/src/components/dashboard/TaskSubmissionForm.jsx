import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { FiGithub, FiLinkedin, FiCheckCircle, FiAlertCircle } from 'react-icons/fi'
import { submitTask } from '../../api/enrollments'

export default function TaskSubmissionForm({ enrollment, onSubmitted }) {
  const [serverError, setServerError] = useState('')
  const alreadySubmitted = enrollment.taskSubmitted

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    defaultValues: {
      githubLink: enrollment.githubLink || '',
      linkedinLink: enrollment.linkedinLink || '',
    },
  })

  const onSubmit = async (formData) => {
    setServerError('')
    try {
      const updated = await submitTask(enrollment.id, formData)
      onSubmitted(updated)
    } catch (err) {
      setServerError(err.message || 'Could not submit your task links. Please try again.')
    }
  }

  return (
    <div className="rounded-3xl bg-white border border-ink-900/10 shadow-card p-7">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-lg">Task Completion</h3>
        {alreadySubmitted && (
          <span className="flex items-center gap-1.5 text-xs font-semibold text-brand-600 bg-brand-50 px-3 py-1.5 rounded-full">
            <FiCheckCircle size={13} /> Submitted
          </span>
        )}
      </div>
      <p className="text-sm text-ink-400 mt-2">
        Share your project's GitHub repository and your LinkedIn profile to complete this step.
        {alreadySubmitted && ' You can update these links any time before payment.'}
      </p>

      {serverError && (
        <div className="flex items-start gap-2 bg-red-50 text-red-700 text-sm rounded-xl p-3 mt-4">
          <FiAlertCircle className="shrink-0 mt-0.5" size={16} />
          <span>{serverError}</span>
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-5" noValidate>
        <div>
          <label htmlFor="githubLink" className="text-sm font-medium text-ink-800 flex items-center gap-1.5">
            <FiGithub size={14} /> GitHub repository link
          </label>
          <input
            id="githubLink"
            {...register('githubLink', {
              required: 'GitHub link is required',
              pattern: { value: /^https?:\/\/.+/i, message: 'Enter a valid URL starting with http(s)://' },
            })}
            className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
            placeholder="https://github.com/yourname/project"
          />
          {errors.githubLink && <p className="text-red-500 text-xs mt-1">{errors.githubLink.message}</p>}
        </div>
        <div>
          <label htmlFor="linkedinLink" className="text-sm font-medium text-ink-800 flex items-center gap-1.5">
            <FiLinkedin size={14} /> LinkedIn profile link
          </label>
          <input
            id="linkedinLink"
            {...register('linkedinLink', {
              required: 'LinkedIn link is required',
              pattern: { value: /^https?:\/\/.+/i, message: 'Enter a valid URL starting with http(s)://' },
            })}
            className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
            placeholder="https://linkedin.com/in/yourname"
          />
          {errors.linkedinLink && <p className="text-red-500 text-xs mt-1">{errors.linkedinLink.message}</p>}
        </div>
        <button type="submit" disabled={isSubmitting} className="btn-primary w-full sm:w-auto">
          {isSubmitting ? 'Saving…' : alreadySubmitted ? 'Update Links' : 'Submit Task'}
        </button>
      </form>
    </div>
  )
}
