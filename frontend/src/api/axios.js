import axios from 'axios'

// Phase 2: point this at the real backend (Node/FastAPI/Laravel/PHP)
// by setting VITE_API_BASE_URL in a .env file. Until then, service
// modules in this folder return mock data and ignore this instance.
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000,
  // The session is an httpOnly cookie set by the API; the browser attaches it. Page
  // scripts never see the token, so an XSS bug cannot steal it.
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
    // Proof the request came from this app: the API requires a custom header on
    // cookie-authenticated writes, which other websites cannot send (CSRF guard).
    'X-Requested-With': 'neuintern',
  },
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Centralized error shape so components never parse axios errors directly
    const message =
      error.response?.data?.message || error.message || 'Something went wrong. Please try again.'
    return Promise.reject({ message, status: error.response?.status })
  }
)

export default apiClient
