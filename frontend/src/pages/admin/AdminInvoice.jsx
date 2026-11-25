import { useCallback, useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { FiAlertCircle, FiCheckCircle, FiEye, FiInfo, FiRotateCcw, FiSave } from 'react-icons/fi'
import Seo from '../../seo/Seo'
import TableSkeleton from '../../components/admin/common/TableSkeleton'
import ErrorState from '../../components/admin/common/ErrorState'
import { fetchInvoiceSettings, saveInvoiceSettings, previewInvoiceSettings } from '../../api/admin'

const input =
  'w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-2.5 text-sm bg-white text-ink-900 focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100'
const label = 'text-sm font-medium text-ink-800'
const hint = 'text-xs text-ink-400 mt-1'
const errText = 'text-red-500 text-xs mt-1'

// The invoice is drawn with a built-in PDF font that only covers Western characters.
// (The server re-checks this exactly; this just gives instant feedback.)
const WESTERN = /^[\n\r -~ -ÿ–—‘’“”•…€™]*$/
const westernOnly = (v) => WESTERN.test(v) || 'Only English/Western characters can be printed on the invoice.'
const singleLine = (v) => !/[\r\n]/.test(v) || 'This must be a single line.'

function Field({ id, title, error, help, children }) {
  return (
    <div>
      <label className={label} htmlFor={id}>{title}</label>
      {children}
      {help && !error && <p className={hint}>{help}</p>}
      {error && <p className={errText} role="alert">{error.message}</p>}
    </div>
  )
}

function Card({ title, children }) {
  return (
    <section className="rounded-3xl bg-white border border-ink-900/10 shadow-card p-6">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-ink-400">{title}</h2>
      <div className="mt-4 space-y-4">{children}</div>
    </section>
  )
}

export default function AdminInvoice() {
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)
  const [defaults, setDefaults] = useState(null)
  const [note, setNote] = useState('')
  const [status, setStatus] = useState(null) // { type: 'ok' | 'error', text }
  const [previewUrl, setPreviewUrl] = useState('')
  const [previewing, setPreviewing] = useState(false)
  const previewRef = useRef('')

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors, isSubmitting, isDirty },
  } = useForm()

  const load = useCallback(() => {
    setLoading(true)
    setLoadError(null)
    fetchInvoiceSettings()
      .then(({ settings, defaults: d, note: n }) => {
        reset(settings)
        setDefaults(d)
        setNote(n)
      })
      .catch((err) => setLoadError(err.message || 'Could not load invoice settings.'))
      .finally(() => setLoading(false))
  }, [reset])

  useEffect(() => {
    load()
  }, [load])

  // Free the previous preview file whenever a new one replaces it, and on leaving the page.
  useEffect(() => {
    previewRef.current = previewUrl
  }, [previewUrl])
  useEffect(() => () => previewRef.current && URL.revokeObjectURL(previewRef.current), [])

  const toPayload = (form) => ({
    ...form,
    gst_rate: Number(form.gst_rate),
    gstin: (form.gstin || '').trim().toUpperCase(),
  })

  const onSave = async (form) => {
    setStatus(null)
    try {
      const saved = await saveInvoiceSettings(toPayload(form))
      reset(saved)
      setStatus({ type: 'ok', text: 'Saved. New invoices will use these details.' })
    } catch (err) {
      setStatus({ type: 'error', text: err.message || 'Could not save. Please check the fields.' })
    }
  }

  const onPreview = async (form) => {
    setStatus(null)
    setPreviewing(true)
    try {
      const blob = await previewInvoiceSettings(toPayload(form))
      setPreviewUrl(URL.createObjectURL(blob))
      // Free the one it replaced (previewRef still holds the old URL at this point).
      if (previewRef.current) URL.revokeObjectURL(previewRef.current)
    } catch {
      setStatus({ type: 'error', text: 'Could not build the preview. Check the fields and try again.' })
    } finally {
      setPreviewing(false)
    }
  }

  const resetToDefaults = () => {
    Object.entries(defaults).forEach(([k, v]) => setValue(k, v, { shouldDirty: true, shouldValidate: true }))
    setStatus({ type: 'ok', text: 'Original details loaded. Press Save to apply them.' })
  }

  return (
    <>
      <Seo title="Invoice Details" path="/admin/invoice-settings" noindex />
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-ink-900 dark:text-white">Invoice details</h1>
        <p className="text-sm text-ink-400 dark:text-white/50">
          The company name, tax details and wording printed on every payment receipt.
        </p>
      </div>

      {loading && (
        <div className="rounded-3xl bg-white border border-ink-900/10 overflow-hidden">
          <TableSkeleton rows={6} cols={2} />
        </div>
      )}
      {!loading && loadError && <ErrorState message={loadError} onRetry={load} />}

      {!loading && !loadError && (
        <div className="grid xl:grid-cols-[minmax(0,1fr)_minmax(0,26rem)] gap-6 items-start">
          <form onSubmit={handleSubmit(onSave)} noValidate className="space-y-6">
            <div className="flex items-start gap-2 bg-brand-50 text-brand-700 text-sm rounded-2xl p-4">
              <FiInfo className="shrink-0 mt-0.5" size={16} aria-hidden="true" />
              <span>{note}</span>
            </div>

            <Card title="Company on the invoice">
              <Field id="inv-company" title="Company name" error={errors.company_name}>
                <input id="inv-company" className={input} {...register('company_name', { required: 'Company name is required', maxLength: { value: 120, message: 'Max 120 characters' }, validate: { w: westernOnly, l: singleLine } })} />
              </Field>
              <Field id="inv-address" title="Address" error={errors.address} help="Up to 3 lines, one per line.">
                <textarea
                  id="inv-address"
                  rows={3}
                  className={`${input} resize-none`}
                  {...register('address', {
                    required: 'Address is required',
                    validate: {
                      w: westernOnly,
                      lines: (v) => v.split('\n').filter((l) => l.trim()).length <= 3 || 'Use at most 3 address lines.',
                      long: (v) => v.split('\n').every((l) => l.trim().length <= 90) || 'Each line must be 90 characters or fewer.',
                    },
                  })}
                />
              </Field>
              <div className="grid sm:grid-cols-2 gap-4">
                <Field id="inv-gstin" title="GSTIN" error={errors.gstin} help="Leave blank to hide it.">
                  <input
                    id="inv-gstin"
                    className={`${input} uppercase`}
                    {...register('gstin', { pattern: { value: /^$|^[0-9]{2}[A-Za-z]{5}[0-9]{4}[A-Za-z][1-9A-Za-z]Z[0-9A-Za-z]$/, message: 'Enter a valid 15-character GSTIN' } })}
                  />
                </Field>
                <Field id="inv-phone" title="Phone" error={errors.phone}>
                  <input id="inv-phone" className={input} {...register('phone', { maxLength: { value: 30, message: 'Max 30 characters' }, validate: { w: westernOnly, l: singleLine } })} />
                </Field>
              </div>
              <Field id="inv-email" title="Email" error={errors.email}>
                <input id="inv-email" type="email" className={input} {...register('email', { pattern: { value: /^$|^[^@\s]+@[^@\s]+\.[^@\s]+$/, message: 'Enter a valid email address' } })} />
              </Field>
            </Card>

            <Card title="Tax">
              <Field
                id="inv-gst"
                title="GST rate (%)"
                error={errors.gst_rate}
                help="The fee already includes this GST. It is shown as equal CGST and SGST lines. Enter 0 to print no tax lines."
              >
                <input
                  id="inv-gst"
                  type="number"
                  step="any"
                  min={0}
                  max={40}
                  className={`${input} sm:max-w-[10rem]`}
                  {...register('gst_rate', { required: 'Enter a rate (0 for none)', min: { value: 0, message: 'Minimum 0' }, max: { value: 40, message: 'Maximum 40' } })}
                />
              </Field>
            </Card>

            <Card title="Wording">
              <div className="grid sm:grid-cols-2 gap-4">
                <Field id="inv-title" title="Document title" error={errors.document_title}>
                  <input id="inv-title" className={input} {...register('document_title', { required: 'Required', maxLength: { value: 40, message: 'Max 40 characters' }, validate: { w: westernOnly, l: singleLine } })} />
                </Field>
                <Field id="inv-prefix" title="Invoice number prefix" error={errors.invoice_prefix} help="Letters, numbers and dashes, up to 10. Example: INV-2026-AB12CD34.">
                  <input id="inv-prefix" className={input} {...register('invoice_prefix', { required: 'Required', pattern: { value: /^[A-Za-z0-9-]{1,10}$/, message: 'Letters, numbers and dashes only (max 10)' } })} />
                </Field>
              </div>
              <Field id="inv-item" title="Line item description" error={errors.item_description} help={'Printed as "<this> — <program name> internship".'}>
                <input id="inv-item" className={input} {...register('item_description', { required: 'Required', maxLength: { value: 80, message: 'Max 80 characters' }, validate: { w: westernOnly, l: singleLine } })} />
              </Field>
              <div className="grid sm:grid-cols-2 gap-4">
                <Field id="inv-team" title="Footer: team name" error={errors.team_name}>
                  <input id="inv-team" className={input} {...register('team_name', { maxLength: { value: 80, message: 'Max 80 characters' }, validate: { w: westernOnly, l: singleLine } })} />
                </Field>
                <Field id="inv-brand" title="Footer: brand line" error={errors.brand_line}>
                  <input id="inv-brand" className={input} {...register('brand_line', { maxLength: { value: 100, message: 'Max 100 characters' }, validate: { w: westernOnly, l: singleLine } })} />
                </Field>
              </div>
              <Field id="inv-note" title="Footer: note" error={errors.footer_note}>
                <input id="inv-note" className={input} {...register('footer_note', { maxLength: { value: 100, message: 'Max 100 characters' }, validate: { w: westernOnly, l: singleLine } })} />
              </Field>
            </Card>

            {status && (
              <div
                role={status.type === 'error' ? 'alert' : 'status'}
                className={`flex items-start gap-2 text-sm rounded-xl p-3 ${status.type === 'error' ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}
              >
                {status.type === 'error' ? <FiAlertCircle className="shrink-0 mt-0.5" size={16} /> : <FiCheckCircle className="shrink-0 mt-0.5" size={16} />}
                <span>{status.text}</span>
              </div>
            )}

            <div className="flex flex-wrap items-center gap-3">
              <button type="submit" disabled={isSubmitting} className="btn-primary !py-2.5 !px-6 text-sm inline-flex items-center gap-2">
                <FiSave /> {isSubmitting ? 'Saving…' : 'Save changes'}
              </button>
              <button type="button" onClick={handleSubmit(onPreview)} disabled={previewing} className="btn-secondary !py-2.5 !px-5 text-sm inline-flex items-center gap-2">
                <FiEye /> {previewing ? 'Building…' : 'Preview PDF'}
              </button>
              <button type="button" onClick={resetToDefaults} className="text-sm text-ink-600 hover:text-brand-600 inline-flex items-center gap-1.5">
                <FiRotateCcw size={14} /> Load original details
              </button>
              {isDirty && <span className="text-xs text-ink-400">Unsaved changes</span>}
            </div>
          </form>

          <aside className="xl:sticky xl:top-24">
            <div className="rounded-3xl bg-white border border-ink-900/10 shadow-card overflow-hidden">
              <div className="px-5 py-3 border-b border-ink-900/5 text-xs font-semibold uppercase tracking-wider text-ink-400">
                Preview (sample student, ₹349)
              </div>
              {previewUrl ? (
                <iframe title="Invoice preview" src={previewUrl} className="w-full h-[34rem] bg-cloud-200" />
              ) : (
                <div className="h-[34rem] flex items-center justify-center text-sm text-ink-400 px-8 text-center">
                  Press “Preview PDF” to see the invoice with the values in the form, before saving.
                </div>
              )}
            </div>
          </aside>
        </div>
      )}
    </>
  )
}
