import type { EvaContext } from './eva'

export interface DashboardOverview {
  calendar_events: number | null
  tasks_today: number | null
  reminders: number | null
  unread_messages: number | null
}

export interface DashboardWeather {
  success: boolean
  city?: string
  temperature?: number
  feels_like?: number
  humidity?: number
  pressure?: number
  wind_speed?: number
  wind_direction?: string
  weather_code?: number
  condition?: string
}

export interface DashboardSystem {
  cpu_percent: number | null
  memory_percent: number | null
  disk_percent: number | null
  network: string | null
}

export interface DashboardData {
  ok: boolean
  overview: DashboardOverview
  weather: DashboardWeather
  system: DashboardSystem
  context: EvaContext
}
