import { useRef, useState } from 'react'
import { useFieldArray, useForm } from 'react-hook-form'
import { motion } from 'framer-motion'
import { FiX, FiAlertCircle, FiPlus, FiTrash2, FiUploadCloud, FiImage } from 'react-icons/fi'
import { uploadProgramImage } from '../../api/admin'

const DEFAULT_CATEGORIES = ['Development', 'Data & AI', 'Security & Cloud', 'Design & Marketing']
const MAX_IMAGE_MB = 3
const IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/webp']

const input =
  'w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-2.5 text-sm bg-white focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100'
const label = 'text-sm font-medium text-ink-800'
const hint = 'text-xs text-ink-400 mt-1'

const toLines = (items) => (items || []).join('\n')
const fromLines = (text) =>
  String(text || '')
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)

const slugify = (text) =>
  text
    .toLowerCase()
    .replace(/&/g, ' and ')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')

function Section({ title, children }) {
  return (
    <fieldset className="space-y-4 pt-5 border-t border-ink-900/5 first:border-0 first:pt-0">
      <legend className="text-xs font-semibold uppercase tracking-wider text-ink-400 mb-1">{title}</legend>
      {children}
    </fieldset>
  )
}

export default function ProgramEditorModal({ program, categories = [], onClose, onSave }) {
  const isNew = !program
  const [serverError, setServerError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [imageError, setImageError] = useState('')
  const [slugTouched, setSlugTouched] = useState(false)
  const fileRef = useRef(null)

  const categoryOptions = [...new Set([...DEFAULT_CATEGORIES, ...categories.filter((c) => c && c !== 'All')])]

  const {
    register,
    handleSubmit,
    control,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm({
    defaultValues: {
      slug: program?.slug || '',
      title: program?.title || '',
      category: program?.category || DEFAULT_CATEGORIES[0],
      tagline: program?.tagline || '',
      image: program?.image || '',
      duration: program?.duration || '4 Weeks',
      mode: program?.mode || 'Remote',
      liveProjects: program?.liveProjects ?? 1,
      certificate: program?.certificate ?? true,
      price: program?.price ?? 150,
      skills: toLines(program?.skills),
      tools: toLines(program?.tools),
      outcomes: toLines(program?.outcomes),
      eligibility: program?.eligibility || '',
      curriculum: (program?.curriculum || []).map((w) => ({
        week: w.week || '',
        title: w.title || '',
        points: toLines(w.points),
      })),
      is_active: program?.isActive ?? true,
    },
  })

  const { fields, append, remove } = useFieldArray({ control, name: 'curriculum' })
  const imageUrl = watch('image')

  // New programs: suggest the slug from the title until the admin edits it themselves.
  const titleField = register('title', { required: 'Title is required' })
  const slugField = register('slug', {
    required: 'Slug is required',
    pattern: { value: /^[a-z0-9]+(?:-[a-z0-9]+)*$/, message: 'Use lowercase letters, numbers and dashes only' },
  })

  const handleFile = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = '' // lets the same file be chosen again
    if (!file) return
    setImageError('')
    if (!IMAGE_TYPES.includes(file.type)) {
      setImageError('Please choose a PNG, JPEG or WebP image.')
      return
    }
    if (file.size > MAX_IMAGE_MB * 1024 * 1024) {
      setImageError(`That image is over ${MAX_IMAGE_MB} MB. Please choose a smaller one.`)
      return
    }
    setUploading(true)
    try {
      const url = await uploadProgramImage(file)
      setValue('image', url, { shouldDirty: true })
    } catch (err) {
      setImageError(err.message || 'Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  const onSubmit = async (form) => {
    setServerError('')
    const payload = {
      title: form.title.trim(),
      category: form.category.trim(),
      tagline: form.tagline.trim(),
      image: form.image.trim(),
      duration: form.duration.trim(),
      mode: form.mode.trim(),
      liveProjects: Number(form.liveProjects),
      certificate: Boolean(form.certificate),
      price: Number(form.price),
      skills: fromLines(form.skills),
      tools: fromLines(form.tools),
      outcomes: fromLines(form.outcomes),
      eligibility: form.eligibility.trim(),
      curriculum: form.curriculum
        .filter((w) => w.week.trim() || w.title.trim() || w.points.trim())
        .map((w) => ({ week: w.week.trim(), title: w.title.trim(), points: fromLines(w.points) })),
      is_active: Boolean(form.is_active),
    }
    if (isNew) payload.slug = form.slug.trim() // the slug is permanent, so it is only sent on create
    try {
      await onSave(payload)
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
      aria-label={isNew ? 'Add program' : `Edit ${program.title}`}
    >
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-3xl w-full max-w-3xl relative shadow-glass-lg max-h-[92vh] flex flex-col"
      >
        <div className="px-7 pt-7 pb-4 border-b border-ink-900/5">
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="absolute top-5 right-5 w-9 h-9 rounded-full flex items-center justify-center text-ink-400 hover:bg-cloud-200 transition-colors"
          >
            <FiX size={18} />
          </button>
          <h3 className="text-xl font-bold">{isNew ? 'Add Program' : `Edit ${program.title}`}</h3>
          <p className="text-sm text-ink-400 mt-1">
            Everything here appears on the public Programs pages as soon as you save.
          </p>
          {serverError && (
            <div className="flex items-start gap-2 bg-red-50 text-red-700 text-sm rounded-xl p-3 mt-4" role="alert">
              <FiAlertCircle className="shrink-0 mt-0.5" size={16} />
              <span>{serverError}</span>
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col min-h-0 flex-1">
          <div className="overflow-y-auto px-7 py-5 space-y-6 flex-1">
            <Section title="Basics">
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className={label} htmlFor="pe-title">Title</label>
                  <input
                    id="pe-title"
                    {...titleField}
                    onChange={(e) => {
                      titleField.onChange(e)
                      if (isNew && !slugTouched) setValue('slug', slugify(e.target.value), { shouldValidate: false })
                    }}
                    className={input}
                  />
                  {errors.title && <p className="text-red-500 text-xs mt-1">{errors.title.message}</p>}
                </div>
                <div>
                  <label className={label} htmlFor="pe-slug">Slug (web address)</label>
                  <input
                    id="pe-slug"
                    {...slugField}
                    onChange={(e) => {
                      setSlugTouched(true)
                      slugField.onChange(e)
                    }}
                    readOnly={!isNew}
                    className={`${input} ${!isNew ? 'bg-cloud-200 text-ink-400 cursor-not-allowed' : ''}`}
                    placeholder="blockchain-development"
                  />
                  {!isNew ? (
                    <p className={hint}>Can&apos;t be changed: enrollments, certificates and links use it.</p>
                  ) : (
                    errors.slug && <p className="text-red-500 text-xs mt-1">{errors.slug.message}</p>
                  )}
                </div>
              </div>

              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className={label} htmlFor="pe-category">Category</label>
                  <input
                    id="pe-category"
                    list="pe-categories"
                    {...register('category', { required: 'Category is required' })}
                    className={input}
                  />
                  <datalist id="pe-categories">
                    {categoryOptions.map((c) => (
                      <option key={c} value={c} />
                    ))}
                  </datalist>
                  <p className={hint}>Pick one, or type a new category to create it.</p>
                  {errors.category && <p className="text-red-500 text-xs mt-1">{errors.category.message}</p>}
                </div>
                <div>
                  <label className={label} htmlFor="pe-price">Certificate fee (₹)</label>
                  <input
                    id="pe-price"
                    type="number"
                    min={1}
                    step="any"
                    {...register('price', { required: 'Enter a fee of ₹1 or more', min: { value: 1, message: 'Minimum ₹1' } })}
                    className={input}
                  />
                  <p className={hint}>Charged at checkout and shown on the invoice. Paid invoices never change.</p>
                  {errors.price && <p className="text-red-500 text-xs mt-1">{errors.price.message}</p>}
                </div>
              </div>

              <div>
                <label className={label} htmlFor="pe-tagline">Tagline</label>
                <textarea id="pe-tagline" rows={2} {...register('tagline')} className={`${input} resize-none`} />
              </div>

              <div className="grid sm:grid-cols-3 gap-4">
                <div>
                  <label className={label} htmlFor="pe-duration">Duration</label>
                  <input id="pe-duration" {...register('duration', { required: true })} className={input} />
                </div>
                <div>
                  <label className={label} htmlFor="pe-mode">Mode</label>
                  <input id="pe-mode" list="pe-modes" {...register('mode', { required: true })} className={input} />
                  <datalist id="pe-modes">
                    <option value="Remote" />
                    <option value="Hybrid" />
                    <option value="On-site" />
                  </datalist>
                </div>
                <div>
                  <label className={label} htmlFor="pe-live">Live projects</label>
                  <input
                    id="pe-live"
                    type="number"
                    min={0}
                    max={50}
                    {...register('liveProjects', { min: 0, max: 50 })}
                    className={input}
                  />
                </div>
              </div>

              <div className="flex flex-wrap gap-x-8 gap-y-3">
                <label className="flex items-center gap-2 text-sm text-ink-800">
                  <input type="checkbox" {...register('certificate')} className="w-4 h-4 accent-brand-600" />
                  Includes a certificate
                </label>
                <label className="flex items-center gap-2 text-sm text-ink-800">
                  <input type="checkbox" {...register('is_active')} className="w-4 h-4 accent-brand-600" />
                  Active (visible in the public catalog)
                </label>
              </div>
            </Section>

            <Section title="Image">
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="w-full sm:w-56 h-32 shrink-0 rounded-2xl bg-cloud-200 border border-ink-900/10 overflow-hidden flex items-center justify-center text-ink-400">
                  {imageUrl ? (
                    <img
                      src={imageUrl}
                      alt="Program banner preview"
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        e.currentTarget.style.display = 'none'
                      }}
                    />
                  ) : (
                    <FiImage size={28} aria-hidden="true" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <input
                    ref={fileRef}
                    type="file"
                    accept={IMAGE_TYPES.join(',')}
                    onChange={handleFile}
                    className="sr-only"
                    aria-label="Upload program image"
                  />
                  <div className="flex flex-wrap items-center gap-3">
                    <button
                      type="button"
                      onClick={() => fileRef.current?.click()}
                      disabled={uploading}
                      className="btn-secondary !py-2 !px-4 text-sm inline-flex items-center gap-2"
                    >
                      <FiUploadCloud /> {uploading ? 'Uploading…' : imageUrl ? 'Replace image' : 'Upload image'}
                    </button>
                    {imageUrl && !uploading && (
                      <button
                        type="button"
                        onClick={() => setValue('image', '', { shouldDirty: true })}
                        className="text-sm text-red-600 hover:underline"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                  <p className={hint}>PNG, JPEG or WebP, up to {MAX_IMAGE_MB} MB. Wide images (about 800×450) look best.</p>
                  {imageError && (
                    <p className="text-red-500 text-xs mt-1" role="alert">{imageError}</p>
                  )}
                  <label className={`${label} block mt-3`} htmlFor="pe-image">Or paste an image link</label>
                  <input id="pe-image" {...register('image')} className={input} placeholder="https://…" />
                </div>
              </div>
            </Section>

            <Section title="Skills, tools & outcomes">
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className={label} htmlFor="pe-skills">Skills</label>
                  <textarea id="pe-skills" rows={5} {...register('skills')} className={`${input} font-mono`} placeholder={'React\nTailwind CSS'} />
                  <p className={hint}>One per line. The first three show on the program card.</p>
                </div>
                <div>
                  <label className={label} htmlFor="pe-tools">Tools</label>
                  <textarea id="pe-tools" rows={5} {...register('tools')} className={`${input} font-mono`} placeholder={'VS Code\nGitHub'} />
                  <p className={hint}>One per line.</p>
                </div>
              </div>
              <div>
                <label className={label} htmlFor="pe-outcomes">What students will achieve</label>
                <textarea id="pe-outcomes" rows={4} {...register('outcomes')} className={`${input} font-mono`} />
                <p className={hint}>One outcome per line.</p>
              </div>
              <div>
                <label className={label} htmlFor="pe-elig">Eligibility</label>
                <textarea id="pe-elig" rows={2} {...register('eligibility')} className={`${input} resize-none`} />
              </div>
            </Section>

            <Section title="Curriculum">
              {fields.length === 0 && <p className="text-sm text-ink-400">No weeks yet. Add the first one below.</p>}
              <div className="space-y-4">
                {fields.map((field, index) => (
                  <div key={field.id} className="rounded-2xl border border-ink-900/10 p-4 bg-cloud-200/40">
                    <div className="flex items-start gap-3">
                      <div className="grid sm:grid-cols-[8rem_1fr] gap-3 flex-1">
                        <div>
                          <label className={label} htmlFor={`pe-wk-${index}`}>Week</label>
                          <input id={`pe-wk-${index}`} {...register(`curriculum.${index}.week`)} className={input} placeholder="Week 1" />
                        </div>
                        <div>
                          <label className={label} htmlFor={`pe-wt-${index}`}>Title</label>
                          <input id={`pe-wt-${index}`} {...register(`curriculum.${index}.title`)} className={input} />
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => remove(index)}
                        aria-label={`Remove week ${index + 1}`}
                        className="mt-7 w-9 h-9 rounded-full flex items-center justify-center text-red-600 hover:bg-red-50 shrink-0"
                      >
                        <FiTrash2 size={16} />
                      </button>
                    </div>
                    <label className={`${label} block mt-3`} htmlFor={`pe-wp-${index}`}>Topics</label>
                    <textarea
                      id={`pe-wp-${index}`}
                      rows={3}
                      {...register(`curriculum.${index}.points`)}
                      className={`${input} font-mono`}
                      placeholder="One topic per line"
                    />
                  </div>
                ))}
              </div>
              {fields.length < 12 && (
                <button
                  type="button"
                  onClick={() => append({ week: `Week ${fields.length + 1}`, title: '', points: '' })}
                  className="btn-secondary !py-2 !px-4 text-sm inline-flex items-center gap-2"
                >
                  <FiPlus /> Add week
                </button>
              )}
            </Section>
          </div>

          <div className="px-7 py-4 border-t border-ink-900/5 flex items-center justify-end gap-3">
            <button type="button" onClick={onClose} className="btn-secondary !py-2.5 !px-5 text-sm">
              Cancel
            </button>
            <button type="submit" disabled={isSubmitting || uploading} className="btn-primary !py-2.5 !px-6 text-sm">
              {isSubmitting ? 'Saving…' : isNew ? 'Create Program' : 'Save Changes'}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  )
}
