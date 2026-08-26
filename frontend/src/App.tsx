import { useEffect, useMemo, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faTemperatureLow, faWind, faDroplet, faGaugeHigh,
  faSun, faCloudSun, faCloud, faCloudRain, faCloudShowersHeavy,
  faSnowflake, faCloudBolt, faSmog, faMoon, faCloudMoon,
  faMicrochip, faCalendarDays, faListCheck, faBell, faEnvelope,
} from '@fortawesome/free-solid-svg-icons'
import type { IconDefinition } from '@fortawesome/fontawesome-common-types'
import { ActivityFeed } from './components/ActivityFeed'
import { ContextPanel } from './components/ContextPanel'
import { ConversationPanel, type Message } from './components/ConversationPanel'
import { EvaOrb } from './components/EvaOrb'
import { Sidebar } from './components/Sidebar'
import { fetchDashboard } from './services/dashboard'
import { demoConversation } from './services/mockEva'
import type { DashboardData } from './types/dashboard'
import type { ActivityItem, EvaContext, EvaEvent, EvaState } from './types/eva'
import './styles/globals.css'
import './styles/responsive.css'

const initialContext: EvaContext = { items: [] }
const emptyDashboard: DashboardData = { ok: false, overview: { calendar_events: null, tasks_today: null, reminders: null, unread_messages: null }, weather: { success: false }, system: { cpu_percent: null, memory_percent: null, disk_percent: null, network: null }, context: initialContext }
const stateStatusLabel: Record<EvaState, string> = { IDLE: 'SİSTEM HAZIRDIR', LISTENING: 'EVA DİNLƏYİR', THINKING: 'EVA DÜŞÜNÜR', EXECUTING: 'EVA İCRA EDİR', WAITING_CONFIRMATION: 'TƏSDİQ GÖZLƏNİLİR', SUCCESS: 'ƏMƏLİYYAT TAMAMLANDI', ERROR: 'SİSTEM XƏTASI' }
const formatClock = (date: Date) => date.toLocaleTimeString('az-AZ', { hour: '2-digit', minute: '2-digit' })
const formatDate = (date: Date) => date.toLocaleDateString('az-AZ', { day: '2-digit', month: 'short', year: 'numeric' })
const displayValue = (value: number | null | undefined, suffix = '') => value == null ? '—' : `${Math.round(value)}${suffix}`

const getWeatherIcon = (code: number | undefined, isNight: boolean): IconDefinition => {
  if (code == null || code === 0) return isNight ? faMoon : faSun
  if (code === 1 || code === 2) return isNight ? faCloudMoon : faCloudSun
  if (code === 3) return faCloud
  if (code === 45 || code === 48) return faSmog
  if (code >= 51 && code <= 67) return faCloudRain
  if (code >= 71 && code <= 77) return faSnowflake
  if (code >= 80 && code <= 82) return faCloudShowersHeavy
  if (code >= 85 && code <= 86) return faSnowflake
  if (code >= 95 && code <= 99) return faCloudBolt
  return isNight ? faCloudMoon : faCloudSun
}

export default function App() {
  const [state, setState] = useState<EvaState>('IDLE')
  const [messages, setMessages] = useState<Message[]>([])
  const [activities, setActivities] = useState<ActivityItem[]>([])
  const [context, setContext] = useState<EvaContext>(initialContext)
  const [online, setOnline] = useState(false)
  const [dashboard, setDashboard] = useState<DashboardData>(emptyDashboard)
  const [now, setNow] = useState(() => new Date())
  const applyEvent = (event: EvaEvent) => { if (event.type === 'state.changed' && event.state) setState(event.state); if (event.type === 'conversation.user' && event.text) setMessages((items) => [...items, { id: crypto.randomUUID(), role: 'user', text: event.text! }]); if (event.type === 'conversation.assistant' && event.text) setMessages((items) => [...items, { id: crypto.randomUUID(), role: 'assistant', text: event.text! }]); if (event.type === 'activity.created' && event.activity) setActivities((items) => [...items, event.activity!]); if (event.type === 'context.updated' && event.context) setContext(event.context) }
  useEffect(() => { const timer = window.setInterval(() => setNow(new Date()), 1000); return () => window.clearInterval(timer) }, [])
  useEffect(() => { let cancelled = false; const load = async () => { const data = await fetchDashboard(); if (cancelled) return; setDashboard(data); setOnline(data.ok); if (data.context.items.length > 0) setContext(data.context) }; void load(); const timer = window.setInterval(() => void load(), 15000); return () => { cancelled = true; window.clearInterval(timer) } }, [])
  useEffect(() => { let cancelled = false; const run = async () => { for await (const event of demoConversation()) { if (cancelled) return; applyEvent(event) } }; run().catch(() => setState('ERROR')); return () => { cancelled = true } }, [])
  const statusText = useMemo(() => stateStatusLabel[state], [state])
  const { overview, weather, system } = dashboard
  const weatherIcon = getWeatherIcon(weather.weather_code, now.getHours() < 6 || now.getHours() >= 19)
  const handleSubmit = (text: string) => { applyEvent({ type: 'conversation.user', text }); applyEvent({ type: 'activity.created', activity: { id: crypto.randomUUID(), time: new Date().toLocaleTimeString('az-AZ'), text: 'Komanda növbəyə əlavə edildi', kind: 'user', detail: text } }); setState('THINKING'); window.setTimeout(() => { applyEvent({ type: 'activity.created', activity: { id: crypto.randomUUID(), time: new Date().toLocaleTimeString('az-AZ'), text: 'Test bağlantısı hazırdır', kind: 'action', detail: 'WebSocket keçidi gözlənilir' } }); applyEvent({ type: 'conversation.assistant', text: 'Komanda qəbul edildi. Real backend bağlantısı Phase 6.5-də aktivləşdiriləcək.' }); setState('SUCCESS'); window.setTimeout(() => setState('IDLE'), 900) }, 650) }
  const systemRows: Array<[string, number | null, string]> = [['CPU', system.cpu_percent, '%'], ['RAM', system.memory_percent, '%'], ['YADDAŞ', system.disk_percent, '%'], ['ŞƏBƏKƏ', system.network === 'ONLAYN' ? 100 : system.network === 'OFFLAYN' ? 0 : null, system.network || '—']]
  return (
    <div className="app-shell"><div className="ambient ambient-a" /><div className="ambient ambient-b" /><Sidebar /><main className="workspace">
      <header className="topbar"><div><span className="eyebrow">E.V.A / ŞƏXSİ ASSİSTENT</span><h1>İdarə Mərkəzi</h1></div><div className="system-status"><span className={`online-dot ${online ? '' : 'offline'}`} />{statusText}<small>{online ? 'LOKAL NÜVƏ' : 'MƏLUMAT KANALI GÖZLƏNİLİR'}</small></div><div className="clock" aria-label={`Cari vaxt ${formatClock(now)}, ${formatDate(now)}`}><strong>{formatClock(now)}</strong><small>{formatDate(now)}</small></div></header>
      <div className="dashboard-grid"><div className="left-stack">
        <section className="panel overview-panel"><div className="panel-heading"><span>BU GÜNÜN İCMALI</span><small>CANLI</small></div><div className="metric"><span><i><FontAwesomeIcon icon={faCalendarDays} /></i> Təqvim tədbirləri</span><strong>{displayValue(overview.calendar_events)}</strong></div><div className="metric"><span><i><FontAwesomeIcon icon={faListCheck} /></i> Tapşırıqlar</span><strong>{displayValue(overview.tasks_today)}</strong></div><div className="metric"><span><i><FontAwesomeIcon icon={faBell} /></i> Xatırlatmalar</span><strong>{displayValue(overview.reminders)}</strong></div><div className="metric"><span><i><FontAwesomeIcon icon={faEnvelope} /></i> Oxunmamış mesajlar</span><strong>{displayValue(overview.unread_messages)}</strong></div></section>
        <section className="panel weather-panel"><div className="panel-heading"><span>HAVA PROQNOZU</span><small>{weather.city ? `${weather.city.toUpperCase()}, AZ` : 'BAKI, AZ'}</small></div><div className="weather-main"><strong>{displayValue(weather.temperature, '°C')}</strong><div className="weather-icon" aria-label={weather.condition || 'Hava məlumatı yoxdur'}><FontAwesomeIcon icon={weatherIcon} aria-hidden="true" /><small>{weather.condition || 'Məlumat yoxdur'}</small></div></div><div className="weather-meta"><span><i><FontAwesomeIcon icon={faTemperatureLow} /></i> Hiss edilən: {displayValue(weather.feels_like, '°C')}</span><span><i><FontAwesomeIcon icon={faWind} /></i> Külək: {displayValue(weather.wind_speed, ' km/saat')}, {weather.wind_direction || '—'}</span><span><i><FontAwesomeIcon icon={faDroplet} /></i> Rütubət: {displayValue(weather.humidity, '%')}</span><span><i><FontAwesomeIcon icon={faGaugeHigh} /></i> Təzyiq: {displayValue(weather.pressure, ' hPa')}</span></div></section>
        <section className="panel system-panel"><div className="panel-heading"><span><FontAwesomeIcon icon={faMicrochip} /> SİSTEM</span><small>LOKAL</small></div>{systemRows.map(([name, percent, label]) => <div className="system-metric" key={name}><span>{name}</span><div><i style={{ width: `${percent ?? 0}%` }} /></div><strong>{name === 'ŞƏBƏKƏ' ? label : displayValue(percent, '%')}</strong></div>)}</section>
      </div><section className="core-column"><div className="core-meta"><span>SÜNİ İNTELLEKT NÜVƏSİ / HOLOQRAFİK İNTERFEYS</span><span>v6.1</span></div><EvaOrb state={state} /><ConversationPanel messages={messages} onSubmit={handleSubmit} /></section><div className="right-stack"><ContextPanel context={context} /><ActivityFeed items={activities} /></div></div>
    </main></div>
  )
}
