import { useEffect, useMemo, useState } from 'react'
import { ActivityFeed } from './components/ActivityFeed'
import { ContextPanel } from './components/ContextPanel'
import { ConversationPanel, type Message } from './components/ConversationPanel'
import { EvaOrb } from './components/EvaOrb'
import { Sidebar } from './components/Sidebar'
import { demoConversation } from './services/mockEva'
import type { ActivityItem, EvaContext, EvaEvent, EvaState } from './types/eva'
import './styles/globals.css'

const initialContext: EvaContext = { items: [] }

export default function App() {
  const [state, setState] = useState<EvaState>('IDLE')
  const [messages, setMessages] = useState<Message[]>([])
  const [activities, setActivities] = useState<ActivityItem[]>([])
  const [context, setContext] = useState<EvaContext>(initialContext)
  const [online, setOnline] = useState(true)

  const applyEvent = (event: EvaEvent) => {
    if (event.type === 'state.changed' && event.state) setState(event.state)
    if (event.type === 'conversation.user' && event.text) setMessages((items) => [...items, { id: crypto.randomUUID(), role: 'user', text: event.text! }])
    if (event.type === 'conversation.assistant' && event.text) setMessages((items) => [...items, { id: crypto.randomUUID(), role: 'assistant', text: event.text! }])
    if (event.type === 'activity.created' && event.activity) setActivities((items) => [...items, event.activity!])
    if (event.type === 'context.updated' && event.context) setContext(event.context)
  }

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

  const statusText = useMemo(() => state === 'IDLE' ? 'SYSTEM READY' : `EVA ${state.replace('_', ' ')}`, [state])

  const handleSubmit = (text: string) => {
    applyEvent({ type: 'conversation.user', text })
    applyEvent({ type: 'activity.created', activity: { id: crypto.randomUUID(), time: new Date().toLocaleTimeString('az-AZ'), text: 'Command queued', kind: 'user', detail: text } })
    setState('THINKING')
    window.setTimeout(() => {
      applyEvent({ type: 'activity.created', activity: { id: crypto.randomUUID(), time: new Date().toLocaleTimeString('az-AZ'), text: 'Mock transport ready', kind: 'action', detail: 'WebSocket gateway pending' } })
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
          <div><span className="eyebrow">E.V.A / PERSONAL AI</span><h1>Command Center</h1></div>
          <div className="system-status"><span className={`online-dot ${online ? '' : 'offline'}`} />{statusText}<small>LOCAL CORE</small></div>
          <div className="clock"><strong>{new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}</strong><small>{new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}</small></div>
        </header>

        <div className="dashboard-grid">
          <div className="left-stack">
            <section className="panel overview-panel">
              <div className="panel-heading"><span>TODAY'S OVERVIEW</span><small>LIVE</small></div>
              <div className="metric"><span>Calendar Events</span><strong>3</strong></div>
              <div className="metric"><span>Tasks</span><strong>5</strong></div>
              <div className="metric"><span>Reminders</span><strong>7</strong></div>
              <div className="metric"><span>Unread Messages</span><strong>7</strong></div>
            </section>
            <section className="panel system-panel">
              <div className="panel-heading"><span>SYSTEM</span><small>LOCAL</small></div>
              {['CPU', 'RAM', 'STORAGE', 'NETWORK'].map((name, index) => <div className="system-metric" key={name}><span>{name}</span><div><i style={{ width: `${32 + index * 14}%` }} /></div><strong>{[12, 45, 68, 32][index]}%</strong></div>)}
            </section>
          </div>

          <section className="core-column">
            <div className="core-meta"><span>AI CORE / HOLOGRAPHIC INTERFACE</span><span>v6.1</span></div>
            <EvaOrb state={state} />
            <ConversationPanel messages={messages} onSubmit={handleSubmit} />
          </section>

          <div className="right-stack">
            <ContextPanel context={context} />
            <ActivityFeed items={activities} />
            <section className="panel weather-panel"><div className="panel-heading"><span>ENVIRONMENT</span><small>BAKU, AZ</small></div><div className="weather-main"><strong>28°</strong><span>CLEAR SKY</span></div><div className="weather-meta"><span>H 31°</span><span>L 22°</span><span>24 km/h</span></div></section>
          </div>
        </div>
      </main>
    </div>
  )
}
