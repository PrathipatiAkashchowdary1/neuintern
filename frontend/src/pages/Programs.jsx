import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import Seo from '../seo/Seo'
import { breadcrumbSchema } from '../seo/schema'
import Breadcrumb from '../components/common/Breadcrumb'
import Search from '../components/common/Search'
import Pagination from '../components/common/Pagination'
import ProgramCard from '../components/programs/ProgramCard'
import { ProgramGridSkeleton } from '../components/common/LoadingSkeleton'
import { fetchPrograms } from '../api/programs'
import { categories } from '../data/programs'

const PAGE_SIZE = 9

export default function Programs() {
  const [searchParams, setSearchParams] = useSearchParams()
  const category = searchParams.get('category') || 'All'
  const search = searchParams.get('search') || ''
  const [page, setPage] = useState(1)

  const [allPrograms, setAllPrograms] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchPrograms({ category, search })
      .then((data) => {
        if (!cancelled) setAllPrograms(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Unable to load programs right now.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [category, search])

  useEffect(() => setPage(1), [category, search])

  const totalPages = Math.max(1, Math.ceil(allPrograms.length / PAGE_SIZE))
  const visible = useMemo(
    () => allPrograms.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [allPrograms, page]
  )

  const updateParam = (key, value) => {
    const next = new URLSearchParams(searchParams)
    if (value && value !== 'All') next.set(key, value)
    else next.delete(key)
    setSearchParams(next)
  }

  return (
    <>
      <Seo
        title="Internship Programs"
        description="Browse 16 focused 4-week internship programs across development, data & AI, security, cloud, design and marketing."
        path="/programs"
        keywords="internship programs, web development internship, AI internship, data science internship"
        structuredData={breadcrumbSchema([{ name: 'Home', path: '/' }, { name: 'Programs', path: '/programs' }])}
      />

      <section className="pt-32 pb-10">
        <div className="container-page">
          <Breadcrumb items={[{ name: 'Home', path: '/' }, { name: 'Programs', path: '/programs' }]} />
          <div className="max-w-2xl mt-8">
            <span className="eyebrow">16 Programs · 4 Weeks Each</span>
            <h1 className="text-4xl sm:text-5xl font-bold mt-4">Explore Internship Programs</h1>
            <p className="text-ink-400 mt-4 leading-relaxed">
              Every track below runs for exactly four weeks, ending in a real project and a certificate.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 mt-10">
            <div className="sm:max-w-sm w-full">
              <Search value={search} onChange={(v) => updateParam('search', v)} />
            </div>
            <div className="flex flex-wrap gap-2">
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => updateParam('category', cat)}
                  className={`px-4 py-2 rounded-full text-sm font-medium border transition-colors ${
                    category === cat
                      ? 'bg-brand-gradient text-white border-transparent'
                      : 'border-ink-900/10 text-ink-600 hover:border-brand-400'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="pb-24">
        <div className="container-page">
          {loading && <ProgramGridSkeleton count={6} />}

          {!loading && error && (
            <div className="text-center py-16">
              <p className="text-ink-800 font-semibold">{error}</p>
              <p className="text-ink-400 text-sm mt-2">Please refresh the page or try again shortly.</p>
            </div>
          )}

          {!loading && !error && visible.length === 0 && (
            <div className="text-center py-16">
              <p className="text-ink-800 font-semibold">No programs match your search.</p>
              <p className="text-ink-400 text-sm mt-2">Try a different keyword or clear the category filter.</p>
            </div>
          )}

          {!loading && !error && visible.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.4 }}
              className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6"
            >
              {visible.map((program, i) => (
                <ProgramCard key={program.id} program={program} index={i} />
              ))}
            </motion.div>
          )}

          {!loading && !error && <Pagination page={page} totalPages={totalPages} onChange={setPage} />}
        </div>
      </section>
    </>
  )
}
