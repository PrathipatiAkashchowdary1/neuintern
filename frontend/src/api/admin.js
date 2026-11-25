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

// Uploads a program banner; resolves to the public URL to store in `image`.
export async function uploadProgramImage(file) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await apiClient.post('/admin/uploads/image', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
  return data.data.url
}

export async function fetchInvoiceSettings() {
  const { data } = await apiClient.get('/admin/invoice-settings')
  return data.data
}

export async function saveInvoiceSettings(payload) {
  const { data } = await apiClient.put('/admin/invoice-settings', payload)
  return data.data.settings
}

// Resolves to a PDF Blob of a sample invoice built from `payload`; nothing is saved.
export async function previewInvoiceSettings(payload) {
  const { data } = await apiClient.post('/admin/invoice-settings/preview', payload, { responseType: 'blob', timeout: 30000 })
  return data
}

// The email outbox: { counts: {pending, sent, failed}, items: [...] }. `status` is all|pending|sent|failed.
export async function fetchEmailOutbox(status = 'all') {
  const { data } = await apiClient.get('/admin/emails', { params: { status } })
  return data.data
}

export async function retryEmail(id) {
  const { data } = await apiClient.post(`/admin/emails/${id}/retry`)
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
