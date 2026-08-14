import { NavLink, useNavigate } from 'react-router-dom'
import { FiHome, FiUsers, FiBook, FiCreditCard, FiMail, FiLogOut, FiX } from 'react-icons/fi'
import { cn } from '../../../utils/cn'
import { useAuth } from '../../../context/AuthContext'

const links = [
  { to: '/admin', label: 'Dashboard', icon: FiHome, end: true },
  { to: '/admin/students', label: 'Students', icon: FiUsers },
  { to: '/admin/programs', label: 'Courses', icon: FiBook },
  { to: '/admin/payments', label: 'Payments', icon: FiCreditCard },
  { to: '/admin/messages', label: 'Messages', icon: FiMail },
]

export default function Sidebar({ open, onClose, unreadMessages = 0 }) {
  const { logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  const content = (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-5 h-20 shrink-0">
        <span className="w-9 h-9 rounded-xl bg-brand-gradient text-white flex items-center justify-center text-sm font-bold">
          NI
        </span>
        <span className="font-display font-bold text-lg text-white">NeuIntern</span>
        <button onClick={onClose} className="ml-auto lg:hidden text-white/60 hover:text-white" aria-label="Close menu">
          <FiX size={20} />
        </button>
      </div>

      <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            onClick={onClose}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors',
                isActive ? 'bg-white/10 text-white' : 'text-white/60 hover:bg-white/5 hover:text-white'
              )
            }
          >
            <link.icon size={17} />
            {link.label}
            {link.to === '/admin/messages' && unreadMessages > 0 && (
              <span className="ml-auto bg-brand-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                {unreadMessages}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="p-3 border-t border-white/10">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-white/60 hover:bg-white/5 hover:text-white transition-colors w-full"
        >
          <FiLogOut size={17} /> Logout
        </button>
      </div>
    </div>
  )

  return (
    <>
      {/* Desktop: fixed sidebar */}
      <aside className="hidden lg:block fixed inset-y-0 left-0 w-64 bg-ink-gradient z-30">{content}</aside>

      {/* Mobile: slide-over */}
      {open && (
        <div className="lg:hidden fixed inset-0 z-40 flex">
          <div className="absolute inset-0 bg-ink-900/60 backdrop-blur-sm" onClick={onClose} />
          <div className="relative w-64 bg-ink-gradient h-full">{content}</div>
        </div>
      )}
    </>
  )
}
