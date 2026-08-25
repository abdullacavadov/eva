import { useEffect, useMemo, useState } from 'react'
import { ActivityFeed } from './components/ActivityFeed'
import { ContextPanel } from './components/ContextPanel'
import { ConversationPanel, type Message } from './components/ConversationPanel'
import { EvaOrb } from './components/EvaOrb'
import { Sidebar } from './components/Sidebar'
import { demoConversation } from './services/mockEva'
import type { ActivityItem, EvaContext, EvaEvent, EvaState } from './types/eva'
import './styles/globals.css'
import './styles/responsive.css'

const initialContext: EvaContext = { items: [] }

const stateStatusLabel: Record<EvaState, string> = {
  IDLE: 'SİSTEM HAZIRDIR',
  LISTENING: 'EVA DİNLƏYİR',
  THINKING: 'EVA DÜŞÜNÜR',
  EXECUTING: 'EVA İCRA EDİR',
  WAITING_CONFIRMATION: 'TƏSDİQ GÖZLƏNİLİR',
  SUCCESS: 'ƏMƏLİYYAT TAMAMLANDI',
  ERROR: 'SİSTEM XƏTASI',
}

const formatClock = (date: Date) => date.toLocaleTimeString('az-AZ', { hour: '2-digit', minute: '2-digit' })
const formatDate = (date: Date) => date.toLocaleDateString('az-AZ', { day: '2-digit', month: 'short', year: 'numeric' })

export default function App() {
  const [state, setState] = useState<EvaState>('IDLE')
  const [messages, setMessages] = useState<Message[]>([])
  const [activities, setActivities] = useState<ActivityItem[]>([])
  const [context, setContext] = useState<EvaContext>(initialContext)
  const [online, setOnline] = useState(true)
  const [now, setNow] = useState(() => new Date())

  const applyEvent = (event: EvaEvent) => {
    if (event.type === 'state.changed' && event.state) setState(event.state)
    if (event.type === 'conversation.user' && event.text) setMessages((items) => [...items, { id: crypto.randomUUID(), role: 'user', text: event.text! }])
    if (event.type === 'conversation.assistant' && event.text) setMessages((items) => [...items, { id: crypto.randomUUID(), role: 'assistant', text: event.text! }])
    if (event.type === 'activity.created' && event.activity) setActivities((items) => [...items, event.activity!])
    if (event.type === 'context.updated' && event.context) setContext(event.context)
  }

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      for await (const event of demoConversation()) {
        if (cancelled) return
        applyEvent(event)
      }
    }
    run().catch(() => { setOnline(false); setState('ERROR') })
    return () => { cancelled = true }
  }, [])

  const statusText = useMemo(() => stateStatusLabel[state], [state])

  const handleSubmit = (text: string) => {
    applyEvent({ type: 'conversation.user', text })
    applyEvent({ type: 'activity.created', activity: { id: crypto.randomUUID(), time: new Date().toLocaleTimeString('az-AZ'), text: 'Komanda növbəyə əlavə edildi', kind: 'user', detail: text } })
    setState('THINKING')
    window.setTimeout(() => {
      applyEvent({ type: 'activity.created', activity: { id: crypto.randomUUID(), time: new Date().toLocaleTimeString('az-AZ'), text: 'Test bağlantısı hazırdır', kind: 'action', detail: 'WebSocket keçidi gözlənilir' } })
      applyEvent({ type: 'conversation.assistant', text: 'Komanda qəbul edildi. Real backend bağlantısı Phase 6.5-də aktivləşdiriləcək.' })
      setState('SUCCESS')
      window.setTimeout(() => setState('IDLE'), 900)
    }, 650)
  }

  return (
    <div className="app-shell">
      <div className="ambient ambient-a" /><div className="ambient ambient-b" />
      <Sidebar />
      <main className="workspace">
        <header className="topbar">
          <div><span className="eyebrow">E.V.A / ŞƏXSİ ASSİSTENT</span><h1>İdarə Mərkəzi</h1></div>
          <div className="system-status"><span className={`online-dot ${online ? '' : 'offline'}`} />{statusText}<small>LOKAL NÜVƏ</small></div>
          <div className="clock" aria-label={`Cari vaxt ${formatClock(now)}, ${formatDate(now)}`}><strong>{formatClock(now)}</strong><small>{formatDate(now)}</small></div>
        </header>

        <div className="dashboard-grid">
          <div className="left-stack">
            <section className="panel overview-panel">
              <div className="panel-heading"><span>BU GÜNÜN İCMALI</span><small>CANLI</small></div>
              <div className="metric"><span>Təqvim tədbirləri</span><strong>3</strong></div>
              <div className="metric"><span>Tapşırıqlar</span><strong>5</strong></div>
              <div className="metric"><span>Xatırlatmalar</span><strong>7</strong></div>
              <div className="metric"><span>Oxunmamış mesajlar</span><strong>7</strong></div>
            </section>
            <section className="panel system-panel">
              <div className="panel-heading"><span>SİSTEM</span><small>LOKAL</small></div>
              {['CPU', 'RAM', 'YADDAŞ', 'ŞƏBƏKƏ'].map((name, index) => <div className="system-metric" key={name}><span>{name}</span><div><i style={{ width: `${32 + index * 14}%` }} /></div><strong>{[12, 45, 68, 32][index]}%</strong></div>)}
            </section>
          </div>

          <section className="core-column">
            <div className="core-meta"><span>SÜNİ İNTELLEKT NÜVƏSİ / HOLOQRAFİK İNTERFEYS</span><span>v6.1</span></div>
            <EvaOrb state={state} />
            <ConversationPanel messages={messages} onSubmit={handleSubmit} />
          </section>

          <div className="right-stack">
            <ContextPanel context={context} />
            <ActivityFeed items={activities} />
            <section className="panel weather-panel">
              <div className="panel-heading">
                <span>HAVA PROQNOZU</span>
                <small>BAKI, AZ</small>
              </div>
              <div className="weather-main">
                <strong>28°</strong>
                <div className="weather-icon">
                  <img src="https://cdn-icons-png.flaticon.com/512/1247/1247953.png" height="35" width="50"></img>
                  <small>Qismən buludlu</small>
                </div>
                
              </div>
              <div className="weather-meta">
                <span>Hiss edilən: 31°</span>
                <span>Külək: 8 km/saat, Şimal-Cənub</span>
                <span>Rütubət: 83%</span>
                <span>Təzyiq: 1009.6 hPa</span>
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  )
}
