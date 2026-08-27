import type { DashboardData } from '../types/dashboard'

export async function fetchDashboard(): Promise<DashboardData | null> {
  try {
    const response = await fetch('/api/dashboard', { cache: 'no-store' })
    if (!response.ok) throw new Error(`Dashboard API: ${response.status}`)
    const data = (await response.json()) as DashboardData
    if (!data || typeof data !== 'object' || !data.overview || !data.system || !data.weather) {
      throw new Error('Dashboard cavabı yanlışdır.')
    }
    return data
  } catch {
    // Refresh uğursuz olduqda son düzgün snapshot ekranda qalmalıdır.
    return null
  }
}
