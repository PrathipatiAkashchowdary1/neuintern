import { useState, useEffect, useCallback } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from '../components/admin/layout/Sidebar'
import Topbar from '../components/admin/layout/Topbar'
import AdminBreadcrumbs from '../components/admin/layout/AdminBreadcrumbs'
import { fetchAllMessages } from '../api/admin'

export default function AdminLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [unreadMessages, setUnreadMessages] = useState(0)

  const refreshUnread = useCallback(() => {
    fetchAllMessages()
      .then((messages) => setUnreadMessages(messages.filter((m) => !m.isRead).length))
      .catch(() => {})
  }, [])

  useEffect(() => {
    refreshUnread()
  }, [refreshUnread])

  return (
    <div className="min-h-screen bg-cloud-200 dark:bg-ink-900 transition-colors">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} unreadMessages={unreadMessages} />

      <div className="lg:pl-64">
        <Topbar onMenuClick={() => setSidebarOpen(true)} unreadMessages={unreadMessages} />

        <main className="p-4 sm:p-6">
          <AdminBreadcrumbs />
          <div className="mt-4">
            <Outlet context={{ refreshUnread }} />
          </div>
        </main>
      </div>
    </div>
  )
}
