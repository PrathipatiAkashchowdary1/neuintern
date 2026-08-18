import { Link } from 'react-router-dom'
import { FiLinkedin, FiInstagram, FiTwitter, FiMail, FiPhone, FiMapPin } from 'react-icons/fi'
import Newsletter from '../common/Newsletter'
import { programs } from '../../data/programs'

const quickLinks = [
  { to: '/', label: 'Home' },
  { to: '/about', label: 'About Us' },
  { to: '/programs', label: 'Programs' },
  { to: '/certificate', label: 'Certificate' },
  { to: '/contact', label: 'Contact' },
]

const resourceLinks = [
  { to: '/privacy-policy', label: 'Privacy Policy' },
  { to: '/terms-and-conditions', label: 'Terms & Conditions' },
  { to: '/refund-policy', label: 'Refund Policy' },
  { to: '/cookie-policy', label: 'Cookie Policy' },
]

export default function Footer() {
  const featuredPrograms = programs.slice(0, 5)

  return (
    <footer className="bg-ink-gradient text-white">
      <div className="container-page py-16 grid sm:grid-cols-2 lg:grid-cols-5 gap-10">
        <div className="lg:col-span-2">
          <Link to="/" className="flex items-center gap-3 font-display font-extrabold text-xl">
            <img src="/icon.png" alt="NeuIntern Logo" className="w-auto h-12" />
          </Link>
          <p className="text-ink-100/60 text-sm mt-4 max-w-xs leading-relaxed">
            Focused 4-week internship programs that turn curious students into job-ready builders.
          </p>
          <div className="flex gap-3 mt-6">
            {[
              { Icon: FiLinkedin, href: 'https://linkedin.com', label: 'LinkedIn' },
              { Icon: FiInstagram, href: 'https://instagram.com', label: 'Instagram' },
              { Icon: FiTwitter, href: 'https://twitter.com', label: 'Twitter' },
            ].map(({ Icon, href, label }) => (
              <a
                key={label}
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={label}
                className="w-9 h-9 rounded-full bg-white/10 flex items-center justify-center hover:bg-brand-500 transition-colors"
              >
                <Icon size={15} />
              </a>
            ))}
          </div>
        </div>

        <div>
          <h4 className="font-semibold">Quick Links</h4>
          <ul className="mt-4 space-y-2.5">
            {quickLinks.map((link) => (
              <li key={link.to}>
                <Link to={link.to} className="text-sm text-ink-100/60 hover:text-white transition-colors">
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h4 className="font-semibold">Programs</h4>
          <ul className="mt-4 space-y-2.5">
            {featuredPrograms.map((p) => (
              <li key={p.slug}>
                <Link to={`/programs/${p.slug}`} className="text-sm text-ink-100/60 hover:text-white transition-colors">
                  {p.title}
                </Link>
              </li>
            ))}
            <li>
              <Link to="/programs" className="text-sm text-brand-300 hover:text-white transition-colors">
                View all →
              </Link>
            </li>
          </ul>
        </div>

        <div>
          <Newsletter />
          <ul className="mt-6 space-y-2.5 text-sm text-ink-100/60">
            <li className="flex items-center gap-2">
              <FiMail size={14} /> contact@neuintern.in
            </li>
            <li className="flex items-center gap-2">
              <FiPhone size={14} /> +91 9652522929
            </li>
            <li className="flex items-center gap-2">
              <FiMapPin size={14} /> Hyderabad, India
            </li>
          </ul>
        </div>
      </div>

      <div className="border-t border-white/10">
        <div className="container-page py-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-ink-100/50">
          <p>© {new Date().getFullYear()} Vivivdone Pvt. Ltd. All rights reserved. NeuIntern is operated by Vivivdone Pvt. Ltd.</p>
          <div className="flex flex-wrap gap-x-5 gap-y-1.5 justify-center">
            {resourceLinks.map((link) => (
              <Link key={link.to} to={link.to} className="hover:text-white transition-colors">
                {link.label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </footer>
  )
}
