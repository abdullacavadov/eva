import type { DashboardData } from '../types/dashboard'

const fallbackData: DashboardData = {
  ok: false,
  overview: {
    calendar_events: null,
    tasks_today: null,
    reminders: null,
    unread_messages: null,
  },
  weather: { success: false },
  system: {
    cpu_percent: null,
    memory_percent: null,
    disk_percent: null,
    network: null,
    battery_percent: null,
    volume_percent: null,
  },
  context: {
    source: 'Google Calendar',
    title: 'Aktiv kontekst',
    items: [],
  },
}

export async function fetchDashboard(): Promise<DashboardData> {
  try {
    const response = await fetch('/api/dashboard', { cache: 'no-store' })
    if (!response.ok) throw new Error(`Dashboard API: ${response.status}`)
    const data = (await response.json()) as DashboardData
    if (!data || typeof data !== 'object') throw new Error('Dashboard cavabı yanlışdır.')
    return data
  } catch {
    return fallbackData
  }
}
