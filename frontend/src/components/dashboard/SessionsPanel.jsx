import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FiMonitor, FiSmartphone, FiShield } from 'react-icons/fi'
import { useAuth } from '../../context/AuthContext'
import { fetchSessions, revokeSession } from '../../api/auth'

const isPhone = (device) => /iOS|Android/.test(device)

function ago(iso) {
  const seconds = Math.max(0, (Date.now() - new Date(iso + 'Z').getTime()) / 1000)
  if (seconds < 90) return 'just now'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`
  const days = Math.round(hours / 24)
  return `${days} day${days === 1 ? '' : 's'} ago`
}

export default function SessionsPanel() {
  const { logoutEverywhere } = useAuth()
  const navigate = useNavigate()
  const [sessions, setSessions] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(null) // a session id, or 'all'
  const [confirmAll, setConfirmAll] = useState(false)

  const load = useCallback(() => {
    fetchSessions()
      .then(setSessions)
      .catch(() => setError('Could not load your devices.'))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleRevoke = async (id) => {
    setBusy(id)
    setError('')
    try {
      await revokeSession(id)
      load()
    } catch (err) {
      setError(err.message || 'Could not log out that device.')
    } finally {
      setBusy(null)
    }
  }

  const handleLogoutAll = async () => {
    setBusy('all')
    setError('')
    try {
      await logoutEverywhere()
      navigate('/login', { replace: true })
    } catch (err) {
      setError(err.message || 'Could not log out of all devices.')
      setBusy(null)
    }
  }

  return (
    <div className="pt-4 border-t border-ink-900/5">
      <h3 className="font-semibold flex items-center gap-2">
        <FiShield className="text-brand-600" size={15} aria-hidden="true" /> Your devices
      </h3>
      <p className="text-xs text-ink-400 mt-1">Where you&apos;re logged in. Not you? Log that device out.</p>

      {error && (
        <p role="alert" className="text-xs text-red-600 mt-2">{error}</p>
      )}

      <ul className="mt-3 space-y-2.5">
        {(sessions || []).map((s) => {
          const Icon = isPhone(s.device) ? FiSmartphone : FiMonitor
          return (
            <li key={s.id} className="flex items-start gap-2.5 text-sm">
              <Icon className="text-ink-400 mt-0.5 shrink-0" size={15} aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <p className="text-ink-800 font-medium leading-snug">
                  {s.device}
                  {s.current && (
                    <span className="ml-2 text-[10px] uppercase tracking-wide bg-brand-50 text-brand-700 px-1.5 py-0.5 rounded-full align-middle">
                      This device
                    </span>
                  )}
                </p>
                <p className="text-xs text-ink-400">Active {ago(s.lastSeenAt)}</p>
              </div>
              {!s.current && (
                <button
                  onClick={() => handleRevoke(s.id)}
                  disabled={busy === s.id}
                  aria-label={`Log out ${s.device}`}
                  className="text-xs font-semibold text-red-600 hover:underline disabled:opacity-50 shrink-0"
                >
                  {busy === s.id ? 'Logging out…' : 'Log out'}
                </button>
              )}
            </li>
          )
        })}
        {sessions && sessions.length === 0 && <li className="text-xs text-ink-400">No active devices.</li>}
      </ul>

      <div className="mt-4">
        {!confirmAll ? (
          <button onClick={() => setConfirmAll(true)} className="text-sm font-semibold text-red-600 hover:underline">
            Log out of all devices
          </button>
        ) : (
          <div className="rounded-xl bg-red-50 p-3" role="alertdialog" aria-label="Confirm logging out of all devices">
            <p className="text-xs text-red-700">This logs you out everywhere, including here.</p>
            <div className="flex gap-3 mt-2">
              <button
                onClick={handleLogoutAll}
                disabled={busy === 'all'}
                className="text-xs font-semibold text-white bg-red-600 rounded-lg px-3 py-1.5 disabled:opacity-60"
              >
                {busy === 'all' ? 'Logging out…' : 'Yes, log out everywhere'}
              </button>
              <button onClick={() => setConfirmAll(false)} className="text-xs font-semibold text-ink-600 hover:underline">
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
