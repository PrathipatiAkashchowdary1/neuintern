import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { getCurrentUser, loginUser, registerUser, logout as logoutApi } from '../api/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (credentials) => {
    const loggedInUser = await loginUser(credentials)
    setUser(loggedInUser)
    return loggedInUser
  }, [])

  const register = useCallback(async (payload) => {
    const newUser = await registerUser(payload)
    setUser(newUser)
    return newUser
  }, [])

  const logout = useCallback(() => {
    logoutApi()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider
      value={{ user, loading, isAuthenticated: Boolean(user), isAdmin: user?.role === 'admin', login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
