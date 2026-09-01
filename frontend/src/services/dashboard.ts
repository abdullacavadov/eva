import type { DashboardData } from '../types/dashboard'

const CACHE_KEY = 'eva.dashboard.snapshot.v1'

function readCachedDashboard(): DashboardData | null {
  try {
    const raw = window.localStorage.getItem(CACHE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw) as DashboardData
    if (!data || typeof data !== 'object' || !data.overview || !data.system || !data.weather) return null
    return data
  } catch { return null }
}

async function getBrowserCoordinates(): Promise<{ latitude: number; longitude: number } | null> {
  if (!('geolocation' in navigator)) return null
  return new Promise((resolve) => navigator.geolocation.getCurrentPosition(
    (position) => resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude }),
    () => resolve(null),
    { enableHighAccuracy: false, maximumAge: 10 * 60 * 1000, timeout: 5000 },
  ))
}

async function getLocalWeather(latitude: number, longitude: number) {
  try {
    const params = new URLSearchParams({ latitude: String(latitude), longitude: String(longitude), current: 'temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,surface_pressure,wind_speed_10m,wind_direction_10m', wind_speed_unit: 'kmh', timezone: 'auto' })
    const response = await fetch(`https://api.open-meteo.com/v1/forecast?${params.toString()}`, { cache: 'no-store' })
    if (!response.ok) return null
    const current = (await response.json()).current || {}
    let city = 'Cari məkan'
    try {
      const reverse = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${encodeURIComponent(latitude)}&lon=${encodeURIComponent(longitude)}&format=jsonv2&zoom=10&accept-language=az`)
      if (reverse.ok) {
        const address = (await reverse.json()).address || {}
        city = address.city || address.town || address.municipality || address.county || city
      }
    } catch { /* weather data remains usable without reverse geocoding */ }
    const descriptions: Record<number, string> = { 0: 'Açıq hava', 1: 'Əsasən açıq hava', 2: 'Qismən buludlu', 3: 'Buludlu', 45: 'Dumanlı', 48: 'Çənli', 51: 'Zəif çiskin', 53: 'Çiskin', 55: 'Güclü çiskin', 61: 'Zəif yağış', 63: 'Yağış', 65: 'Güclü yağış', 71: 'Zəif qar', 73: 'Qar', 75: 'Güclü qar', 80: 'Zəif yağış keçidləri', 81: 'Yağış keçidləri', 82: 'Güclü yağış keçidləri', 95: 'Şimşəkli hava', 96: 'Şimşək və dolu', 99: 'Güclü şimşək və dolu' }
    const directions = ['Şimal', 'Şimal-Şərq', 'Şərq', 'Cənub-Şərq', 'Cənub', 'Cənub-Qərb', 'Qərb', 'Şimal-Qərb']
    const degrees = current.wind_direction_10m
    return { success: true, city, temperature: current.temperature_2m, feels_like: current.apparent_temperature, humidity: current.relative_humidity_2m, pressure: current.surface_pressure, wind_speed: current.wind_speed_10m, wind_direction: degrees == null ? '—' : directions[Math.floor((degrees + 22.5) / 45) % 8], weather_code: current.weather_code, condition: descriptions[current.weather_code] || 'Hava şəraiti müəyyən edilmədi' }
  } catch { return null }
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
    try { window.localStorage.setItem(CACHE_KEY, JSON.stringify(data)) } catch { /* cache optional */ }
    return data
  } catch { return readCachedDashboard() }
}
