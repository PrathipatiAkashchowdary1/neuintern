import axios from 'axios'

// Phase 2: point this at the real backend (Node/FastAPI/Laravel/PHP)
// by setting VITE_API_BASE_URL in a .env file. Until then, service
// modules in this folder return mock data and ignore this instance.
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('neuintern_token')
  if (token) {
    config.headers.Authorization = 'Bearer ' + token
  }
  return config
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
