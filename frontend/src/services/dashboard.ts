import type { DashboardData } from '../types/dashboard'

const CACHE_KEY = 'eva.dashboard.snapshot.v1'

function readCachedDashboard(): DashboardData | null {
  try {
    const raw = window.localStorage.getItem(CACHE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw) as DashboardData
    if (!data || typeof data !== 'object' || !data.overview || !data.system || !data.weather) return null
    return data
  } catch {
    return null
  }
}

async function getBrowserCoordinates(): Promise<{ latitude: number; longitude: number } | null> {
  if (!('geolocation' in navigator)) return null
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude }),
      () => resolve(null),
      { enableHighAccuracy: false, maximumAge: 10 * 60 * 1000, timeout: 5000 },
    )
  })
}

async function getLocalWeather(latitude: number, longitude: number) {
  try {
    const params = new URLSearchParams({
      latitude: String(latitude),
      longitude: String(longitude),
      current: 'temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,surface_pressure,wind_speed_10m,wind_direction_10m',
      wind_speed_unit: 'kmh',
      timezone: 'auto',
    })
    const response = await fetch(`https://api.open-meteo.com/v1/forecast?${params.toString()}`, { cache: 'no-store' })
    if (!response.ok) return null
    const current = (await response.json()).current || {}
    return {
      success: true,
      city: 'Cari məkan',
      temperature: current.temperature_2m,
      feels_like: current.apparent_temperature,
      humidity: current.relative_humidity_2m,
      pressure: current.surface_pressure,
      wind_speed: current.wind_speed_10m,
      wind_direction: '—',
      weather_code: current.weather_code,
      condition: undefined,
    }
  } catch {
    return null
  }
}

export async function fetchDashboard(): Promise<DashboardData | null> {
  try {
    const response = await fetch('/api/dashboard', { cache: 'no-store' })
    if (!response.ok) throw new Error(`Dashboard API: ${response.status}`)
    const data = (await response.json()) as DashboardData
    if (!data || typeof data !== 'object' || !data.overview || !data.system || !data.weather) throw new Error('Dashboard cavabı yanlışdır.')

    const coordinates = await getBrowserCoordinates()
    if (coordinates) {
      const localWeather = await getLocalWeather(coordinates.latitude, coordinates.longitude)
      if (localWeather) data.weather = { ...data.weather, ...localWeather }
    }

    try { window.localStorage.setItem(CACHE_KEY, JSON.stringify(data)) } catch {
      // Cache yazıla bilməsə də canlı məlumat işləməyə davam etməlidir.
    }
    return data
  } catch {
    return readCachedDashboard()
  }
}
