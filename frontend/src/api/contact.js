import apiClient from './axios'

export async function submitContactForm(payload) {
  try {
    const { data } = await apiClient.post('/contact', payload)
    return { success: true, message: data.message }
  } catch (err) {
    return Promise.reject({ message: err.message || 'Could not send message. Please try again.' })
  }
}

export async function subscribeNewsletter(email) {
  try {
    const { data } = await apiClient.post('/contact/newsletter', { email })
    return { success: true, message: data.message }
  } catch (err) {
    return Promise.reject({ message: err.message || 'Could not subscribe right now.' })
  }
}
