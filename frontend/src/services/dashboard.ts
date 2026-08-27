import type { DashboardData } from '../types/dashboard'

const CACHE_KEY = 'eva.dashboard.snapshot.v1'

function readCachedDashboard(): DashboardData | null {
  try {
    const raw = window.localStorage.getItem(CACHE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw) as DashboardData
    if (!data || typeof data !== 'object' || !data.overview || !data.system || !data.weather) {
      return null
    }
    return data
  } catch {
    return null
  }
}

export async function fetchDashboard(): Promise<DashboardData | null> {
  try {
    const response = await fetch('/api/dashboard', { cache: 'no-store' })
    if (!response.ok) throw new Error(`Dashboard API: ${response.status}`)
    const data = (await response.json()) as DashboardData
    if (!data || typeof data !== 'object' || !data.overview || !data.system || !data.weather) {
      throw new Error('Dashboard cavabı yanlışdır.')
    }
    try {
      window.localStorage.setItem(CACHE_KEY, JSON.stringify(data))
    } catch {
      // Cache yazıla bilməsə də canlı məlumat işləməyə davam etməlidir.
    }
    return data
  } catch {
    // Şəbəkə/API problemi mövcud UI state-i heç vaxt silməməlidir.
    return readCachedDashboard()
  }
}
