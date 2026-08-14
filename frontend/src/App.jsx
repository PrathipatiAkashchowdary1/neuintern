import { HelmetProvider } from 'react-helmet-async'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import AppRoutes from './routes/AppRoutes'
import { Toaster } from 'react-hot-toast'

export default function App() {
  return (
    <HelmetProvider>
      <ThemeProvider>
        <AuthProvider>
          <BrowserRouter>
            <AppRoutes />
            <Toaster
                position="top-right"
                toastOptions={{
                  duration: 3500,
                  style: { borderRadius: '12px', fontSize: '14px' },
                }}
              />

          </BrowserRouter>
        </AuthProvider>
      </ThemeProvider>
    </HelmetProvider>
  )
}
