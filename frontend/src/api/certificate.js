import apiClient from './axios'

export async function verifyCertificate(certificateId) {
  try {
    const { data } = await apiClient.post('/certificate/verify', { certificateId })
    return data
  } catch (err) {
    return {
      success: false,
      message: err.message || 'Certificate verification is temporarily unavailable.',
      certificateId,
    }
  }
}
