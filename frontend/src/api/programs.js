import apiClient from './axios'
import { programs as mockPrograms, getProgramBySlug as getMockBySlug } from '../data/programs'

// Talks to the real NeuIntern backend when reachable; falls back to local
// mock data if the API is unavailable (e.g. running the frontend standalone,
// or the backend isn't deployed yet). This keeps Phase 1 demoable everywhere
// while Phase 2 quietly takes over once the backend is live.

async function mockFetchPrograms({ category = 'All', search = '' } = {}) {
  await new Promise((r) => setTimeout(r, 200))
  let result = mockPrograms
  if (category && category !== 'All') result = result.filter((p) => p.category === category)
  if (search) {
    const q = search.toLowerCase()
    result = result.filter((p) => p.title.toLowerCase().includes(q) || p.tagline.toLowerCase().includes(q))
  }
  return result
}

export async function fetchPrograms({ category = 'All', search = '', page = 1, limit = 100 } = {}) {
  try {
    const { data } = await apiClient.get('/programs', { params: { category, search, page, limit } })
    return data.data
  } catch {
    return mockFetchPrograms({ category, search })
  }
}

export async function fetchProgramBySlug(slug) {
  try {
    const { data } = await apiClient.get(`/programs/${slug}`)
    return data.data
  } catch (err) {
    const fallback = getMockBySlug(slug)
    if (fallback) return fallback
    return Promise.reject({ message: err.message || 'Program not found', status: 404 })
  }
}

export async function fetchCategories() {
  try {
    const { data } = await apiClient.get('/programs/categories')
    return data.data
  } catch {
    return ['All', 'Development', 'Data & AI', 'Security & Cloud', 'Design & Marketing']
  }
}
