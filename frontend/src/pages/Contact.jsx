import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { motion } from 'framer-motion'
import { FiMail, FiPhone, FiMapPin, FiLinkedin, FiInstagram, FiTwitter, FiCheckCircle } from 'react-icons/fi'
import Seo from '../seo/Seo'
import { breadcrumbSchema } from '../seo/schema'
import Breadcrumb from '../components/common/Breadcrumb'
import { submitContactForm } from '../api/contact'

export default function Contact() {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm()
  const [submitted, setSubmitted] = useState(false)

  const onSubmit = async (data) => {
    await submitContactForm(data)
    setSubmitted(true)
    reset()
  }

  return (
    <>
      <Seo
        title="Contact Us"
        description="Get in touch with the NeuIntern team for questions about programs, applications, or partnerships."
        path="/contact"
        structuredData={breadcrumbSchema([{ name: 'Home', path: '/' }, { name: 'Contact', path: '/contact' }])}
      />

      <section className="pt-32 pb-16">
        <div className="container-page">
          <Breadcrumb items={[{ name: 'Home', path: '/' }, { name: 'Contact', path: '/contact' }]} />
          <div className="max-w-2xl mt-8">
            <span className="eyebrow">Contact</span>
            <h1 className="text-4xl sm:text-5xl font-bold mt-4">Let's talk</h1>
            <p className="text-ink-400 mt-4 leading-relaxed">
              Questions about a program, an application, or a partnership? Send us a message and our
              team will reply within 24 hours.
            </p>
          </div>
        </div>
      </section>

      <section className="pb-24">
        <div className="container-page grid lg:grid-cols-5 gap-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="lg:col-span-3 rounded-3xl bg-white border border-ink-900/5 p-8 shadow-card"
          >
            {submitted ? (
              <div className="text-center py-14">
                <FiCheckCircle className="text-brand-500 mx-auto" size={40} />
                <h3 className="font-semibold text-xl mt-4">Message sent</h3>
                <p className="text-ink-400 mt-2">Thanks for reaching out — we'll get back to you within 24 hours.</p>
                <button onClick={() => setSubmitted(false)} className="text-brand-600 font-medium text-sm mt-5 hover:underline">
                  Send another message
                </button>
              </div>
            ) : (
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
                <div className="grid sm:grid-cols-2 gap-5">
                  <div>
                    <label htmlFor="name" className="text-sm font-medium text-ink-800">Full name</label>
                    <input
                      id="name"
                      {...register('name', { required: 'Please enter your name' })}
                      className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
                      placeholder="Jane Doe"
                    />
                    {errors.name && <p className="text-red-500 text-xs mt-1">{errors.name.message}</p>}
                  </div>
                  <div>
                    <label htmlFor="email" className="text-sm font-medium text-ink-800">Email</label>
                    <input
                      id="email"
                      type="email"
                      {...register('email', {
                        required: 'Please enter your email',
                        pattern: { value: /^\S+@\S+\.\S+$/, message: 'Enter a valid email' },
                      })}
                      className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
                      placeholder="jane@email.com"
                    />
                    {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>}
                  </div>
                </div>
                <div>
                  <label htmlFor="subject" className="text-sm font-medium text-ink-800">Subject</label>
                  <input
                    id="subject"
                    {...register('subject', { required: 'Please add a subject' })}
                    className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100"
                    placeholder="Question about React Development program"
                  />
                  {errors.subject && <p className="text-red-500 text-xs mt-1">{errors.subject.message}</p>}
                </div>
                <div>
                  <label htmlFor="message" className="text-sm font-medium text-ink-800">Message</label>
                  <textarea
                    id="message"
                    rows={5}
                    {...register('message', { required: 'Please add a message' })}
                    className="w-full mt-1.5 rounded-xl border border-ink-900/10 px-4 py-3 text-sm focus:outline-none focus:border-brand-400 focus:ring-4 focus:ring-brand-100 resize-none"
                    placeholder="Tell us what you'd like to know…"
                  />
                  {errors.message && <p className="text-red-500 text-xs mt-1">{errors.message.message}</p>}
                </div>
                <button type="submit" disabled={isSubmitting} className="btn-primary w-full sm:w-auto">
                  {isSubmitting ? 'Sending…' : 'Send Message'}
                </button>
              </form>
            )}
          </motion.div>

          <div className="lg:col-span-2 space-y-6">
            <div className="rounded-3xl bg-white border border-ink-900/5 p-7 shadow-card space-y-5">
              <div className="flex items-start gap-3">
                <FiMail className="text-brand-600 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold">Email</p>
                  <p className="text-sm text-ink-400">contact@neuintern.in</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <FiPhone className="text-brand-600 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold">Phone</p>
                  <p className="text-sm text-ink-400">+91 9652522929</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <FiMapPin className="text-brand-600 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold">Office</p>
                  <p className="text-sm text-ink-400">#Flat no 401, Vasista Enclave, A.S.Raju Nagar, KPHB, Hyderabad, Telangana 500072</p>
                </div>
              </div>
              <div className="flex gap-3 pt-2">
                {[FiLinkedin, FiInstagram, FiTwitter].map((Icon, i) => (
                  <a
                    key={i}
                    href="#"
                    aria-label="Social link"
                    className="w-9 h-9 rounded-full bg-brand-gradient-soft text-brand-600 flex items-center justify-center hover:bg-brand-gradient hover:text-white transition-colors"
                  >
                    <Icon size={15} />
                  </a>
                ))}
              </div>
            </div>

            <div className="rounded-3xl overflow-hidden border border-ink-900/5 shadow-card h-56 bg-cloud-200 flex items-center justify-center">
              {/* Google Maps placeholder — replace src with a live embed URL in production */}
              <iframe
    title="Location Map"
    src="https://www.google.com/maps/embed/v1/place?q=vasista%20enclae&key=AIzaSyBFw0Qbyq9zTFTd-tUY6dZWTgaQzuU17R8"
    className="w-full h-full border-0"
    allowFullScreen=""
    loading="lazy"
    referrerPolicy="no-referrer-when-downgrade"
  ></iframe>
             
            </div>
          </div>
        </div>
      </section>
    </>
  )
}
