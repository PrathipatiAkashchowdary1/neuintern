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
  return data.data.user // the API also set the session cookie
}

export async function loginUser(credentials) {
  const { data } = await apiClient.post('/auth/login', credentials)
  return data.data.user // the API also set the session cookie
}

export async function getCurrentUser() {
  // Older versions kept the token in localStorage, where any injected script could read it.
  // Remove it so it is not left lying around on returning visitors' browsers.
  localStorage.removeItem('neuintern_token')
  try {
    const { data } = await apiClient.get('/auth/me') // 401 when there is no valid session cookie
    return data.data
  } catch {
    return null
  }
}

export async function logout() {
  try {
    await apiClient.post('/auth/logout') // asks the API to clear the cookie
  } catch {
    // Offline or already expired: nothing more to do; the caller clears local state anyway.
  }
}

// Reserved for Phase 2 — backend routes exist and return 501 until implemented.
export async function loginWithGoogle() {
  return Promise.reject({ message: 'Google login is not available yet.', status: 501 })
}

export async function requestOtp(_phoneOrEmail) {
  return Promise.reject({ message: 'OTP login is not available yet.', status: 501 })
}
