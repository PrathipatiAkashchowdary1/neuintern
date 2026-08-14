import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { FiMenu, FiSearch, FiBell, FiSun, FiMoon, FiChevronDown, FiUser, FiLogOut, FiMail } from 'react-icons/fi'
import { useAuth } from '../../../context/AuthContext'
import { useTheme } from '../../../context/ThemeContext'

export default function Topbar({ onMenuClick, unreadMessages = 0 }) {
  const { user, logout } = useAuth()
  const { isDark, toggle } = useTheme()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [profileOpen, setProfileOpen] = useState(false)
  const [bellOpen, setBellOpen] = useState(false)
  const profileRef = useRef(null)
  const bellRef = useRef(null)

  useEffect(() => {
    const handleClick = (e) => {
      if (profileRef.current && !profileRef.current.contains(e.target)) setProfileOpen(false)
      if (bellRef.current && !bellRef.current.contains(e.target)) setBellOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const handleSearch = (e) => {
    e.preventDefault()
    if (search.trim()) navigate(`/admin/students?search=${encodeURIComponent(search.trim())}`)
  }

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <header className="sticky top-0 z-20 h-16 bg-white/80 dark:bg-ink-900/80 backdrop-blur-xl border-b border-ink-900/5 dark:border-white/5 flex items-center gap-4 px-4 sm:px-6">
      <button
        onClick={onMenuClick}
        className="lg:hidden text-ink-600 dark:text-white/70 hover:text-ink-900 dark:hover:text-white"
        aria-label="Open menu"
      >
        <FiMenu size={22} />
      </button>

      <form onSubmit={handleSearch} className="relative flex-1 max-w-sm hidden sm:block">
        <FiSearch className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-400 dark:text-white/40" size={15} />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search students…"
          className="w-full rounded-full border border-ink-900/10 dark:border-white/10 bg-cloud-200 dark:bg-white/5 pl-9 pr-4 py-2 text-sm text-ink-900 dark:text-white placeholder:text-ink-400 dark:placeholder:text-white/40 focus:outline-none focus:border-brand-400"
        />
      </form>

      <div className="ml-auto flex items-center gap-2 sm:gap-3">
        <button
          onClick={toggle}
          aria-label="Toggle dark mode"
          className="w-9 h-9 rounded-full flex items-center justify-center text-ink-600 dark:text-white/70 hover:bg-cloud-200 dark:hover:bg-white/10 transition-colors"
        >
          {isDark ? <FiSun size={17} /> : <FiMoon size={17} />}
        </button>

        <div className="relative" ref={bellRef}>
          <button
            onClick={() => setBellOpen((v) => !v)}
            aria-label="Notifications"
            className="relative w-9 h-9 rounded-full flex items-center justify-center text-ink-600 dark:text-white/70 hover:bg-cloud-200 dark:hover:bg-white/10 transition-colors"
          >
            <FiBell size={17} />
            {unreadMessages > 0 && (
              <span className="absolute top-1 right-1 w-2 h-2 bg-brand-500 rounded-full" />
            )}
          </button>
          {bellOpen && (
            <div className="absolute right-0 mt-2 w-64 bg-white dark:bg-ink-800 rounded-2xl shadow-glass-lg border border-ink-900/5 dark:border-white/10 p-4 text-sm">
              {unreadMessages > 0 ? (
                <>
                  <p className="font-medium text-ink-900 dark:text-white flex items-center gap-2">
                    <FiMail size={14} className="text-brand-600" /> {unreadMessages} unread message{unreadMessages > 1 ? 's' : ''}
                  </p>
                  <button
                    onClick={() => {
                      setBellOpen(false)
                      navigate('/admin/messages')
                    }}
                    className="text-brand-600 dark:text-brand-400 font-medium text-xs mt-2 hover:underline"
                  >
                    View messages →
                  </button>
                </>
              ) : (
                <p className="text-ink-400 dark:text-white/50">You're all caught up.</p>
              )}
            </div>
          )}
        </div>

        <div className="relative" ref={profileRef}>
          <button
            onClick={() => setProfileOpen((v) => !v)}
            className="flex items-center gap-2 pl-1 pr-2 py-1 rounded-full hover:bg-cloud-200 dark:hover:bg-white/10 transition-colors"
          >
            <span className="w-7 h-7 rounded-full bg-brand-gradient text-white flex items-center justify-center text-xs font-semibold">
              {user?.fullName?.[0]?.toUpperCase() || 'A'}
            </span>
            <span className="hidden sm:block text-sm font-medium text-ink-800 dark:text-white/90">
              {user?.fullName?.split(' ')[0] || 'Admin'}
            </span>
            <FiChevronDown size={14} className="text-ink-400 dark:text-white/40" />
          </button>
          {profileOpen && (
            <div className="absolute right-0 mt-2 w-52 bg-white dark:bg-ink-800 rounded-2xl shadow-glass-lg border border-ink-900/5 dark:border-white/10 py-2 text-sm">
              <div className="px-4 py-2 border-b border-ink-900/5 dark:border-white/10">
                <p className="font-medium text-ink-900 dark:text-white flex items-center gap-1.5">
                  <FiUser size={13} /> {user?.fullName}
                </p>
                <p className="text-xs text-ink-400 dark:text-white/50 truncate mt-0.5">{user?.email}</p>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 w-full text-left px-4 py-2.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors"
              >
                <FiLogOut size={14} /> Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
