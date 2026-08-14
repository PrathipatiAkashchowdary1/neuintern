import { lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import MainLayout from '../layouts/MainLayout'
import AdminLayout from '../layouts/AdminLayout'
import Loader from '../components/common/Loader'
import { ProtectedRoute, AdminRoute } from './ProtectedRoute'

// Route-level code splitting keeps the initial bundle small (perf requirement).
const Home = lazy(() => import('../pages/Home'))
const About = lazy(() => import('../pages/About'))
const Programs = lazy(() => import('../pages/Programs'))
const ProgramDetails = lazy(() => import('../pages/ProgramDetails'))
const Certificate = lazy(() => import('../pages/Certificate'))
const Reviews = lazy(() => import('../pages/Reviews'))
const Contact = lazy(() => import('../pages/Contact'))
const Login = lazy(() => import('../pages/Login'))
const Register = lazy(() => import('../pages/Register'))
const ForgotPassword = lazy(() => import('../pages/ForgotPassword'))
const Dashboard = lazy(() => import('../pages/Dashboard'))
const PrivacyPolicy = lazy(() => import('../pages/legal/PrivacyPolicy'))
const TermsAndConditions = lazy(() => import('../pages/legal/TermsAndConditions'))
const RefundPolicy = lazy(() => import('../pages/legal/RefundPolicy'))
const CookiePolicy = lazy(() => import('../pages/legal/CookiePolicy'))
const NotFound = lazy(() => import('../pages/NotFound'))

// Admin pages — deliberately NOT under MainLayout, so they get their own
// sidebar/topbar shell instead of the public site's Navbar/Footer.
const AdminHome = lazy(() => import('../pages/admin/AdminHome'))
const AdminStudents = lazy(() => import('../pages/admin/AdminStudents'))
const AdminPayments = lazy(() => import('../pages/admin/AdminPayments'))
const AdminMessages = lazy(() => import('../pages/admin/AdminMessages'))
const AdminPrograms = lazy(() => import('../pages/admin/AdminPrograms'))

export default function AppRoutes() {
  return (
    <Suspense fallback={<Loader label="Loading page" />}>
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/" element={<Home />} />
          <Route path="/about" element={<About />} />
          <Route path="/programs" element={<Programs />} />
          <Route path="/programs/:slug" element={<ProgramDetails />} />
          <Route path="/certificate" element={<Certificate />} />
          <Route path="/reviews" element={<Reviews />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />

          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<Dashboard />} />
          </Route>

          <Route path="/privacy-policy" element={<PrivacyPolicy />} />
          <Route path="/terms-and-conditions" element={<TermsAndConditions />} />
          <Route path="/refund-policy" element={<RefundPolicy />} />
          <Route path="/cookie-policy" element={<CookiePolicy />} />
          <Route path="*" element={<NotFound />} />
        </Route>

        <Route element={<AdminRoute />}>
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminHome />} />
            <Route path="students" element={<AdminStudents />} />
            <Route path="payments" element={<AdminPayments />} />
            <Route path="messages" element={<AdminMessages />} />
            <Route path="programs" element={<AdminPrograms />} />
          </Route>
        </Route>
      </Routes>
    </Suspense>
  )
}
