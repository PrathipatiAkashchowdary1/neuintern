import apiClient from './axios'

export async function fetchAllEnrollments(params = {}) {
  const { data } = await apiClient.get('/admin/enrollments', { params })
  return data.data
}

export async function fetchAnalytics() {
  const { data } = await apiClient.get('/admin/analytics')
  return data.data
}

export async function fetchAdminPrograms() {
  const { data } = await apiClient.get('/admin/programs')
  return data.data
}

export async function createAdminProgram(payload) {
  const { data } = await apiClient.post('/admin/programs', payload)
  return data.data
}

export async function updateAdminProgram(slug, payload) {
  const { data } = await apiClient.put(`/admin/programs/${slug}`, payload)
  return data.data
}

export async function deleteAdminProgram(slug) {
  const { data } = await apiClient.delete(`/admin/programs/${slug}`)
  return data
}

export async function fetchAllMessages() {
  const { data } = await apiClient.get('/admin/messages')
  return data.data
}

export async function markMessageRead(id) {
  const { data } = await apiClient.put(`/admin/messages/${id}/read`)
  return data.data
}

export async function deleteMessage(id) {
  const { data } = await apiClient.delete(`/admin/messages/${id}`)
  return data
}
