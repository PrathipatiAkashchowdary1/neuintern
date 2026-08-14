import apiClient from './axios'
export async function sendOtp(email, purpose = 'register') {
  const { data } = await apiClient.post('/auth/send-otp', { email, purpose })
  return data
}

export async function verifyOtp(email, otp, purpose = 'register') {
  const { data } = await apiClient.post('/auth/verify-otp', { email, otp, purpose })
  return data
}

export async function forgotPassword(email) {
  const { data } = await apiClient.post('/auth/forgot-password', { email })
  return data
}

export async function resetPassword(email, otp, newPassword) {
  const { data } = await apiClient.post('/auth/reset-password', { email, otp, newPassword })
  return data
}

export async function registerUser(payload) {
  // payload: { fullName, email, phone, degree, branch, currentYear, password }
  const { data } = await apiClient.post('/auth/register', payload)
  localStorage.setItem('neuintern_token', data.data.token)
  return data.data.user
}

export async function loginUser(credentials) {
  const { data } = await apiClient.post('/auth/login', credentials)
  localStorage.setItem('neuintern_token', data.data.token)
  return data.data.user
}

export async function getCurrentUser() {
  const token = localStorage.getItem('neuintern_token')
  if (!token) return null
  try {
    const { data } = await apiClient.get('/auth/me')
    return data.data
  } catch {
    localStorage.removeItem('neuintern_token')
    return null
  }
}

export function logout() {
  localStorage.removeItem('neuintern_token')
}

// Reserved for Phase 2 — backend routes exist and return 501 until implemented.
export async function loginWithGoogle() {
  return Promise.reject({ message: 'Google login is not available yet.', status: 501 })
}

export async function requestOtp(_phoneOrEmail) {
  return Promise.reject({ message: 'OTP login is not available yet.', status: 501 })
}
