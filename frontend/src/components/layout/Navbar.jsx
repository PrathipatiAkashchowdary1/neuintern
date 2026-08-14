import { useState, useEffect } from 'react'
import { NavLink, Link, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { FiMenu, FiX, FiUser, FiLogOut, FiGrid } from 'react-icons/fi'
import { cn } from '../../utils/cn'
import { useAuth } from '../../context/AuthContext'

const links = [
  { to: '/', label: 'Home' },
  { to: '/programs', label: 'Programs' },
  { to: '/about', label: 'About' },
  { to: '/certificate', label: 'Certificate' },
  { to: '/contact', label: 'Contact' },
]

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [open, setOpen] = useState(false)
  const { isAuthenticated, isAdmin, user, logout } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    setOpen(false)
  }, [])

  const handleLogout = () => {
    logout()
    setOpen(false)
    navigate('/')
  }

  return (
    <header
      className={cn(
        'fixed top-0 inset-x-0 z-50 transition-all duration-300',
        scrolled ? 'bg-white/80 backdrop-blur-xl shadow-card' : 'bg-transparent'
      )}
    >
      <nav className="container-page flex items-center justify-between h-20" aria-label="Primary">
        <Link to="/" className="flex items-center gap-3 font-display font-extrabold text-xl">
          <img src="/icon.png" alt="NeuIntern Logo" className="w-auto h-12" />
          
        </Link>

        <div className="hidden md:flex items-center gap-8">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === '/'}
              className={({ isActive }) =>
                cn(
                  'text-sm font-medium transition-colors',
                  isActive ? 'text-brand-600' : 'text-ink-600 hover:text-brand-600'
                )
              }
            >
              {link.label}
            </NavLink>
          ))}
          {isAuthenticated && (
            <NavLink
              to={isAdmin ? '/admin' : '/dashboard'}
              className={({ isActive }) =>
                cn('text-sm font-medium transition-colors', isActive ? 'text-brand-600' : 'text-ink-600 hover:text-brand-600')
              }
            >
              {isAdmin ? 'Admin' : 'Dashboard'}
            </NavLink>
          )}
        </div>

        <div className="hidden md:flex items-center gap-3">
          {isAuthenticated ? (
            <>
              <span className="text-sm text-ink-400 flex items-center gap-1.5">
                <FiUser size={14} /> {user?.fullName?.split(' ')[0]}
              </span>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 text-sm font-medium text-ink-600 hover:text-brand-600 transition-colors"
              >
                <FiLogOut size={14} /> Logout
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="text-sm font-medium text-ink-600 hover:text-brand-600 transition-colors">
                Log In
              </Link>
              <Link to="/register" className="btn-primary !py-2.5 !px-5 text-sm">
                Register
              </Link>
            </>
          )}
        </div>

        <button
          className="md:hidden w-10 h-10 flex items-center justify-center text-ink-900"
          onClick={() => setOpen(!open)}
          aria-label={open ? 'Close menu' : 'Open menu'}
          aria-expanded={open}
        >
          {open ? <FiX size={22} /> : <FiMenu size={22} />}
        </button>
      </nav>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="md:hidden bg-white border-t border-ink-900/5 overflow-hidden"
          >
            <div className="container-page py-6 flex flex-col gap-4">
              {links.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  end={link.to === '/'}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    cn('text-base font-medium', isActive ? 'text-brand-600' : 'text-ink-800')
                  }
                >
                  {link.label}
                </NavLink>
              ))}

              {isAuthenticated ? (
                <>
                  <NavLink
                    to={isAdmin ? '/admin' : '/dashboard'}
                    onClick={() => setOpen(false)}
                    className="text-base font-medium text-ink-800 flex items-center gap-2"
                  >
                    <FiGrid size={16} /> {isAdmin ? 'Admin Dashboard' : 'My Dashboard'}
                  </NavLink>
                  <button onClick={handleLogout} className="text-base font-medium text-left text-ink-800 flex items-center gap-2">
                    <FiLogOut size={16} /> Logout
                  </button>
                </>
              ) : (
                <>
                  <Link to="/login" onClick={() => setOpen(false)} className="text-base font-medium text-ink-800">
                    Log In
                  </Link>
                  <Link to="/register" onClick={() => setOpen(false)} className="btn-primary justify-center mt-2">
                    Register
                  </Link>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}
