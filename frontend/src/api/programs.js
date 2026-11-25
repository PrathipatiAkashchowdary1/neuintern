import apiClient from './axios'

// The API is the only source of truth for programs: prices, images and categories are
// edited by admins, so a bundled copy would quietly show students stale or wrong
// information whenever a request failed. On failure these reject, and each page shows
// a real error state instead.

export async function fetchPrograms({ category = 'All', search = '', page = 1, limit = 100 } = {}) {
  const { data } = await apiClient.get('/programs', { params: { category, search, page, limit } })
  return data.data
}

// Rejects with { message, status }. status is 404 when the program does not exist, and
// undefined when the API could not be reached at all.
export async function fetchProgramBySlug(slug) {
  const { data } = await apiClient.get(`/programs/${encodeURIComponent(slug)}`)
  return data.data
}

export async function fetchCategories() {
  try {
    const { data } = await apiClient.get('/programs/categories')
    return data.data
  } catch {
    return ['All'] // the filter bar just shows "All"; the program list itself reports the error
  }
}
