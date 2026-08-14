import apiClient from './axios'

export async function createOrder({ programSlug, name, email, phone }) {
  const { data } = await apiClient.post('/payments/create-order', { programSlug, name, email, phone })
  return data.data
}

export async function verifyPayment(payload) {
  const { data } = await apiClient.post('/payments/verify', payload)
  return data
}
