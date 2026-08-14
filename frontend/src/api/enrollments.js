import apiClient from './axios'

export async function enrollInProgram(programSlug) {
  const { data } = await apiClient.post('/enrollments', { programSlug })
  return data.data
}

export async function fetchMyEnrollments() {
  const { data } = await apiClient.get('/enrollments/me')
  return data.data
}

export async function fetchEnrollment(id) {
  const { data } = await apiClient.get(`/enrollments/${id}`)
  return data.data
}

export async function fetchOfferLetter(id) {
  const { data } = await apiClient.get(`/enrollments/${id}/offer-letter`)
  return data.data
}

export async function submitTask(id, { githubLink, linkedinLink }) {
  const { data } = await apiClient.post(`/enrollments/${id}/task`, { githubLink, linkedinLink })
  return data.data
}

export async function createCertificateOrder(id) {
  const { data } = await apiClient.post(`/enrollments/${id}/payment/create-order`)
  return data.data
}

export async function verifyCertificatePayment(id, payload) {
  const { data } = await apiClient.post(`/enrollments/${id}/payment/verify`, payload)
  return data
}

export async function fetchCertificate(id) {
  const { data } = await apiClient.get(`/enrollments/${id}/certificate`)
  return data.data
}

async function downloadBlob(url, filename) {
  const response = await apiClient.get(url, { responseType: 'blob' })
  const blobUrl = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
  const link = document.createElement('a')
  link.href = blobUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(blobUrl)
}

export async function downloadOfferLetterPdf(id) {
  await downloadBlob(`/enrollments/${id}/offer-letter/pdf`, `NeuIntern-Offer-Letter-${id.slice(0, 8)}.pdf`)
}

export async function downloadCertificatePdf(id, certificateId) {
  await downloadBlob(`/enrollments/${id}/certificate/pdf`, `NeuIntern-Certificate-${certificateId || id.slice(0, 8)}.pdf`)
}

export async function downloadInvoicePdf(id) {
  await downloadBlob(`/enrollments/${id}/invoice/pdf`, `NeuIntern-Invoice-${id.slice(0, 8)}.pdf`)
}
