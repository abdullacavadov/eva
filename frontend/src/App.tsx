import { useCallback, useEffect, useMemo, useState } from 'react'
import { ActivityFeed } from './components/ActivityFeed'
import { ContextPanel } from './components/ContextPanel'
import { ConversationPanel, type Message } from './components/ConversationPanel'
import { EvaOrb } from './components/EvaOrb'
import { Sidebar } from './components/Sidebar'
import { useEvaConnection } from './services/useEvaConnection'
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
  const [online, setOnline] = useState(false)
  const [now, setNow] = useState(() => new Date())

  const applyEvent = useCallback((event: EvaEvent) => {
    if (event.type === 'connection.ready') {
      setOnline(true)
      return
    }
    if (event.type === 'bridge.error') {
      setOnline(false)
      setState('ERROR')
      setActivities((items) => [...items, {
        id: crypto.randomUUID(),
        time: new Date().toLocaleTimeString('az-AZ'),
        text: 'UI bağlantı xətası',
        kind: 'error',
        detail: event.message,
      }])
      return
    }
    if (event.type === 'state.changed') setState(event.state)
    if (event.type === 'conversation.user') setMessages((items) => [...items, { id: crypto.randomUUID(), role: 'user', text: event.text }])
    if (event.type === 'conversation.assistant') setMessages((items) => [...items, { id: crypto.randomUUID(), role: 'assistant', text: event.text }])
    if (event.type === 'activity.created') setActivities((items) => [...items, event.activity])
    if (event.type === 'context.updated') setContext(event.context)
    if (event.type === 'tool.started') {
      setState('EXECUTING')
      setActivities((items) => [...items, {
        id: crypto.randomUUID(),
        time: new Date().toLocaleTimeString('az-AZ'),
        text: `Alət icra olunur: ${event.tool}`,
        kind: 'action',
      }])
    }
    if (event.type === 'tool.completed') {
      setActivities((items) => [...items, {
        id: crypto.randomUUID(),
        time: new Date().toLocaleTimeString('az-AZ'),
        text: event.success ? `Alət tamamlandı: ${event.tool}` : `Alət uğursuz oldu: ${event.tool}`,
        kind: event.success ? 'success' : 'error',
        detail: event.result,
      }])
    }
  }, [])

  const { connected, sendText } = useEvaConnection(applyEvent)

  useEffect(() => {
    setOnline(connected)
  }, [connected])

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  const statusText = useMemo(() => stateStatusLabel[state], [state])

  const handleSubmit = (text: string) => {
    if (!sendText(text)) {
      setState('ERROR')
      setActivities((items) => [...items, {
        id: crypto.randomUUID(),
        time: new Date().toLocaleTimeString('az-AZ'),
        text: 'EVA bağlantısı hazır deyil',
        kind: 'error',
        detail: 'WebSocket bağlantısı gözlənilir.',
      }])
    }
  }

  return (
    <div className="app-shell">
      <div className="ambient ambient-a" /><div className="ambient ambient-b" />
      <Sidebar />
      <main className="workspace">
        <header className="topbar">
          <div><span className="eyebrow">E.V.A / ŞƏXSİ ASSİSTENT</span><h1>İdarə Mərkəzi</h1></div>
          <div className="system-status"><span className={`online-dot ${online ? '' : 'offline'}`} />{statusText}<small>{online ? 'LOKAL NÜVƏ' : 'BAĞLANTI GÖZLƏNİLİR'}</small></div>
          <div className="clock" aria-label={`Cari vaxt ${formatClock(now)}, ${formatDate(now)}`}><strong>{formatClock(now)}</strong><small>{formatDate(now)}</small></div>
        </header>

        <div className="dashboard-grid">
          <div className="left-stack">
            <section className="panel overview-panel">
              <div className="panel-heading"><span>BU GÜNÜN İCMALI</span><small>CANLI</small></div>
              <div className="metric"><span>Təqvim tədbirləri</span><strong>—</strong></div>
              <div className="metric"><span>Tapşırıqlar</span><strong>—</strong></div>
              <div className="metric"><span>Xatırlatmalar</span><strong>—</strong></div>
              <div className="metric"><span>Oxunmamış mesajlar</span><strong>—</strong></div>
            </section>
            <section className="panel system-panel">
              <div className="panel-heading"><span>SİSTEM</span><small>LOKAL</small></div>
              {['CPU', 'RAM', 'YADDAŞ', 'ŞƏBƏKƏ'].map((name, index) => <div className="system-metric" key={name}><span>{name}</span><div><i style={{ width: `${32 + index * 14}%` }} /></div><strong>{[12, 45, 68, 32][index]}%</strong></div>)}
            </section>
          </div>

          <section className="core-column">
            <div className="core-meta"><span>SÜNİ İNTELLEKT NÜVƏSİ / HOLOQRAFİK İNTERFEYS</span><span>v6.2</span></div>
            <EvaOrb state={state} />
            <ConversationPanel messages={messages} onSubmit={handleSubmit} />
          </section>

          <div className="right-stack">
            <ContextPanel context={context} />
            <ActivityFeed items={activities} />
            <section className="panel weather-panel"><div className="panel-heading"><span>MÜHİT</span><small>BAKI, AZ</small></div><div className="weather-main"><strong>—°</strong><span>CANLI MƏLUMAT GÖZLƏNİLİR</span></div><div className="weather-meta"><span>Y —</span><span>A —</span><span>— km/s</span></div></section>
          </div>
        </div>
      </main>
    </div>
  )
}
