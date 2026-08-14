import { useState } from 'react'
import { FiEdit2, FiPlus, FiEyeOff } from 'react-icons/fi'
import ProgramEditorModal from './ProgramEditorModal'
import { createAdminProgram, updateAdminProgram, deleteAdminProgram } from '../../api/admin'
import { cn } from '../../utils/cn'

export default function ProgramsManager({ programs, onChanged }) {
  const [editing, setEditing] = useState(null) // program object, or 'new', or null
  const [busySlug, setBusySlug] = useState(null)

  const handleSave = async (formData) => {
    if (editing === 'new') {
      await createAdminProgram(formData)
    } else {
      await updateAdminProgram(editing.slug, formData)
    }
    onChanged()
  }

  const handleDeactivate = async (slug) => {
    setBusySlug(slug)
    try {
      await deleteAdminProgram(slug)
      onChanged()
    } finally {
      setBusySlug(null)
    }
  }

  return (
    <div className="rounded-3xl bg-white border border-ink-900/10 shadow-card overflow-hidden">
      <div className="p-5 border-b border-ink-900/5 flex items-center justify-between">
        <h3 className="font-semibold">Manage Programs</h3>
        <button onClick={() => setEditing('new')} className="btn-primary !py-2 !px-4 text-sm">
          <FiPlus size={14} /> Add Program
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-ink-400 uppercase tracking-wide border-b border-ink-900/5">
              <th className="px-5 py-3 font-medium">Program</th>
              <th className="px-5 py-3 font-medium">Category</th>
              <th className="px-5 py-3 font-medium">Price</th>
              <th className="px-5 py-3 font-medium">Status</th>
              <th className="px-5 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-900/5">
            {programs.map((p) => (
              <tr key={p.slug} className="hover:bg-cloud-200/60 transition-colors">
                <td className="px-5 py-4 font-medium text-ink-900">{p.title}</td>
                <td className="px-5 py-4 text-ink-600">{p.category}</td>
                <td className="px-5 py-4 text-ink-600">₹{p.price?.toLocaleString('en-IN')}</td>
                <td className="px-5 py-4">
                  <span
                    className={cn(
                      'text-xs font-semibold px-2.5 py-1 rounded-full',
                      p.isActive ? 'bg-brand-50 text-brand-700' : 'bg-ink-50 text-ink-500'
                    )}
                  >
                    {p.isActive ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-5 py-4">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => setEditing(p)}
                      aria-label={`Edit ${p.title}`}
                      className="w-8 h-8 rounded-full flex items-center justify-center text-ink-600 hover:bg-brand-50 hover:text-brand-600 transition-colors"
                    >
                      <FiEdit2 size={14} />
                    </button>
                    {p.isActive && (
                      <button
                        onClick={() => handleDeactivate(p.slug)}
                        disabled={busySlug === p.slug}
                        aria-label={`Deactivate ${p.title}`}
                        className="w-8 h-8 rounded-full flex items-center justify-center text-ink-600 hover:bg-red-50 hover:text-red-600 transition-colors disabled:opacity-40"
                      >
                        <FiEyeOff size={14} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && (
        <ProgramEditorModal
          program={editing === 'new' ? null : editing}
          onClose={() => setEditing(null)}
          onSave={handleSave}
        />
      )}
    </div>
  )
}
