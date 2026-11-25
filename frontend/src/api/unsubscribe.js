import apiClient from './axios'

// POST/DELETE (not GET) on purpose: mail scanners auto-follow links, so a
// plain GET would unsubscribe people who never clicked.
export async function unsubscribe(token) {
  const { data } = await apiClient.post(`/unsubscribe/${encodeURIComponent(token)}`)
  return data
}

export async function resubscribe(token) {
  const { data } = await apiClient.delete(`/unsubscribe/${encodeURIComponent(token)}`)
  return data
}
