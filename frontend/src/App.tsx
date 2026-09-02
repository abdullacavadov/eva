import { useEffect, useMemo, useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faTemperatureLow,
  faWind,
  faDroplet,
  faGaugeHigh,
  faMicrochip,
  faCalendarDays,
  faListCheck,
  faBell,
  faEnvelope,
  faMemory,
  faBatteryHalf,
  faHardDrive,
  faWifi,
  faVolumeHigh,
  faGear,
  faClock,
  faCalendarDay,
} from '@fortawesome/free-solid-svg-icons';
import { ContextPanel } from './components/ContextPanel';
import {
  ConversationPanel,
  type Message,
} from './components/ConversationPanel';
import { ControlPanel, type ControlCommand } from './components/ControlPanel';
import { EvaOrb } from './components/EvaOrb';
import { fetchDashboard } from './services/dashboard';
import { useEvaConnection } from './services/useEvaConnection';
import type { DashboardData } from './types/dashboard';
import type { ActivityItem, EvaContext, EvaEvent, EvaState } from './types/eva';
import './styles/globals.css';
import './styles/responsive.css';
import AzCalendar from './components/Calendar';



const initialContext: EvaContext = { items: [] };
const emptyDashboard: DashboardData = {
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
  context: initialContext,
};
const stateStatusLabel: Record<EvaState, string> = {
  IDLE: 'SİSTEM HAZIRDIR',
  LISTENING: 'EVA DİNLƏYİR',
  SPEAKING: 'EVA DANIŞIR',
  THINKING: 'EVA DÜŞÜNÜR',
  EXECUTING: 'EVA İCRA EDİR',
  WAITING_CONFIRMATION: 'TƏSDİQ GÖZLƏNİLİR',
  SUCCESS: 'ƏMƏLİYYAT TAMAMLANDI',
  ERROR: 'SİSTEM XƏTASI',
  MUTED: 'MİKROFON SƏSSİZDİR',
  PAUSED: 'EVA DAYANDIRILIB',
  INITIALISING: 'EVA BAŞLADILIR',
};

const formatClock = (date: Date) =>
  date.toLocaleTimeString('az-AZ', { hour: '2-digit', minute: '2-digit', second: '2-digit' }).split(':').join(':');
const formatDate = (date: Date) =>
  date.toLocaleDateString('eu-EU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).split('.').join('.');
const displayValue = (value: number | null | undefined, suffix = '') =>
  value == null ? '—' : `${Math.round(value)}${suffix}`;

function getWeatherIcon(weatherCode: number | undefined) {
  switch (weatherCode) {
    case 0:
      return 1;
    case 1:
      return 2;
    case 2:
      return 4;
    case 3:
      return 7;
    case 45:
    case 48:
      return 9;
    case 51:
    case 53:
    case 55:
      return 9;
    case 61:
      return 37;
    case 63:
      return 38;
    case 65:
      return 39;
    case 71:
      return 57;
    case 73:
      return 58;
    case 75:
      return 59;
    case 80:
      return 31;
    case 81:
      return 32;
    case 82:
      return 33;
    case 95:
      return 77;
    case 96:
    case 99:
      return 17;
    default:
      return 4;
  }
}

export default function App() {
  const [state, setState] = useState<EvaState>('IDLE');
  const [messages, setMessages] = useState<Message[]>([]);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [context, setContext] = useState<EvaContext>(initialContext);
  const [online, setOnline] = useState(false);
  const [dashboard, setDashboard] = useState<DashboardData>(emptyDashboard);
  const [now, setNow] = useState(() => new Date());
  const [paused, setPaused] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);
  const [microphoneMuted, setMicrophoneMuted] = useState(false);

  const applyEvent = (event: EvaEvent) => {
    if (event.type === 'connection.ready') setOnline(true);

    if (event.type === 'runtime.snapshot') {
      setOnline(true);
      if (event.state) setState(event.state);
      setMessages(
        (event.messages ?? []).map((message, index) => ({
          id: `runtime-${index}-${message.type}`,
          role: message.type === 'conversation.user' ? 'user' : 'assistant',
          text: message.text,
        }))
      );
      setActivities(event.activities ?? []);
      if (event.context) setContext(event.context);
      if (event.control) {
        setPaused(Boolean(event.control.paused));
        setCameraActive(Boolean(event.control.camera_active));
        setMicrophoneMuted(Boolean(event.control.microphone_muted));
      }
      return;
    }

    if (event.type === 'bridge.error') {
      setOnline(false);
      setState('ERROR');
      setActivities((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          time: new Date().toLocaleTimeString('az-AZ'),
          text: 'UI bağlantı xətası',
          kind: 'error',
          detail: event.message,
        },
      ]);
    }
    if (event.type === 'state.changed' && event.state) setState(event.state);
    if (event.type === 'control.state') {
      if (event.control.paused !== undefined)
        setPaused(Boolean(event.control.paused));
      if (event.control.camera_active !== undefined)
        setCameraActive(Boolean(event.control.camera_active));
      if (event.control.microphone_muted !== undefined)
        setMicrophoneMuted(Boolean(event.control.microphone_muted));
    }
    if (event.type === 'conversation.user' && event.text)
      setMessages((items) => [
        ...items,
        { id: crypto.randomUUID(), role: 'user', text: event.text! },
      ]);
    if (event.type === 'conversation.assistant' && event.text)
      setMessages((items) => [
        ...items,
        { id: crypto.randomUUID(), role: 'assistant', text: event.text! },
      ]);
    if (event.type === 'activity.created' && event.activity)
      setActivities((items) => [...items, event.activity!]);
    if (event.type === 'context.updated' && event.context)
      setContext(event.context);
    if (event.type === 'tool.started') {
      setState('EXECUTING');
      setActivities((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          time: new Date().toLocaleTimeString('az-AZ'),
          text: `Alət icra olunur: ${event.tool}`,
          kind: 'action',
        },
      ]);
    }
    if (event.type === 'tool.completed')
      setActivities((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          time: new Date().toLocaleTimeString('az-AZ'),
          text: event.success
            ? `Alət tamamlandı: ${event.tool}`
            : `Alət uğursuz oldu: ${event.tool}`,
          kind: event.success ? 'success' : 'error',
          detail: event.result,
        },
      ]);
  };

  const { connected, sendText, sendControl } = useEvaConnection(applyEvent);
  useEffect(() => setOnline(connected), [connected]);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const sleep = (ms: number) =>
      new Promise((resolve) => window.setTimeout(resolve, ms));

    const poll = async () => {
      while (!cancelled) {
        const data = await fetchDashboard();
        if (cancelled) return;
        if (data) {
          setDashboard(data);
          if (data.context.items.length > 0) setContext(data.context);
        }
        await sleep(15000);
      }
    };

    void poll();
    return () => {
      cancelled = true;
    };
  }, []);

  const statusText = useMemo(() => stateStatusLabel[state], [state]);
  const { overview, weather, system } = dashboard;
  const handleSubmit = (text: string) => {
    if (!sendText(text)) {
      setState('ERROR');
      setActivities((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          time: new Date().toLocaleTimeString('az-AZ'),
          text: 'EVA bağlantısı hazır deyil',
          kind: 'error',
          detail: 'WebSocket bağlantısı gözlənilir.',
        },
      ]);
    }
  };

  const handleControl = (command: ControlCommand) => {
    if (!sendControl(command)) {
      setActivities((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          time: new Date().toLocaleTimeString('az-AZ'),
          text: 'EVA idarəetmə bağlantısı hazır deyil',
          kind: 'error',
          detail: 'WebSocket bağlantısı gözlənilir.',
        },
      ]);
    }
  };

  const systemRows: Array<[string, number | null, string, typeof faMicrochip]> =
    [
      ['CPU', system.cpu_percent, '%', faMicrochip],
      ['RAM', system.memory_percent, '%', faMemory],
      ['YADDAŞ', system.disk_percent, '%', faHardDrive],
      [
        'ŞƏBƏKƏ',
        system.network === 'ONLAYN'
          ? 100
          : system.network === 'OFFLAYN'
            ? 0
            : null,
        system.network || '—',
        faWifi,
      ],
      [
        'BATEREYA',
        system.battery_percent ?? null,
        system.battery_percent != null ? `${system.battery_percent}%` : '—',
        faBatteryHalf,
      ],
      [
        'SƏS',
        system.volume_percent ?? null,
        system.volume_percent != null ? `${system.volume_percent}%` : '—',
        faVolumeHigh,
      ],
    ];

  return (
    <div className="app-shell">
      <div className="ambient ambient-a" />
      <div className="ambient ambient-b" />
      <aside>
        <AzCalendar />
        <ContextPanel context={context} />
      </aside>
      <main className="workspace">
        <header className="topbar">
          <div>
            <span className="eyebrow">E.V.A</span>
            <h3>Enhanced Virtual Assistant</h3>
          </div>

          <div
            className="clock"
            aria-label={`Cari vaxt ${formatClock(now)}, ${formatDate(now)}`}
          >
            <span style={{ marginRight: '10px' }}><FontAwesomeIcon icon={faClock} /> {formatClock(now)}</span>
            <span><FontAwesomeIcon icon={faCalendarDay} /> {formatDate(now)}</span>
          </div>

          <div className="settings-block">
            <a className="settings">
              <FontAwesomeIcon icon={faGear} />
            </a>
          </div>
        </header>
        <div className="dashboard-grid">
          <div className="left-stack">
            <section className="panel overview-panel">
              <div className="panel-heading">
                <span>BU GÜNÜN İCMALI</span>
                <small>CANLI</small>
              </div>
              <div className="metric">
                <span>
                  <i>
                    <FontAwesomeIcon icon={faCalendarDays} />
                  </i>{' '}
                  Təqvim tədbirləri
                </span>
                <strong>{displayValue(overview.calendar_events)}</strong>
              </div>
              <div className="metric">
                <span>
                  <i>
                    <FontAwesomeIcon icon={faListCheck} />
                  </i>{' '}
                  Tapşırıqlar
                </span>
                <strong>{displayValue(overview.tasks_today)}</strong>
              </div>
              <div className="metric">
                <span>
                  <i>
                    <FontAwesomeIcon icon={faBell} />
                  </i>{' '}
                  Xatırlatmalar
                </span>
                <strong>{displayValue(overview.reminders)}</strong>
              </div>
              <div className="metric">
                <span>
                  <i>
                    <FontAwesomeIcon icon={faEnvelope} />
                  </i>{' '}
                  Oxunmamış mesajlar
                </span>
                <strong>{displayValue(overview.unread_messages)}</strong>
              </div>
            </section>
            <ControlPanel
              onCommand={handleControl}
              paused={paused}
              cameraActive={cameraActive}
              microphoneMuted={microphoneMuted}
              disabled={!connected}
            />
          </div>
          <section className="core-column">
            <div className="core-meta">
              <span>HOLOQRAFİK İNTERFEYS</span>
              <span>v2.1</span>
            </div>
            <EvaOrb state={state} />

            <div style={{ display: 'flex', justifyContent: 'space-between', height: '210px'}}>
              <section className="panel system-panel">
                <div className="panel-heading">
                  <span>
                    <FontAwesomeIcon icon={faMicrochip} /> SİSTEM
                  </span>
                  <small>LOKAL</small>
                </div>
                {systemRows.map(([name, percent, label, icon]) => (
                  <div className="system-metric" key={name}>
                    <span>
                      <span className="icon">
                        <FontAwesomeIcon icon={icon} />
                      </span>{' '}
                      {name}
                    </span>

                    <div>
                      <i style={{ width: `${percent ?? 0}%` }} />
                    </div>

                    <strong>
                      {name === 'ŞƏBƏKƏ' ? label : displayValue(percent, '%')}
                    </strong>
                  </div>
                ))}
              </section>

              <section className="panel weather-panel">
                <div className="panel-heading">
                  <span>HAVA PROQNOZU</span>
                  <small>
                    {weather.city
                      ? `${weather.city.toUpperCase()}, AZ`
                      : 'BAKI, AZ'}
                  </small>
                </div>
                <div className="weather-main">
                  <strong>{displayValue(weather.temperature, '°C')}</strong>
                  <div
                    className="weather-icon"
                    aria-label={weather.condition || 'Hava məlumatı yoxdur'}
                  >
                    <img
                      src={`https://cdn.fmi.fi/symbol-images/smartsymbol/v3/p/${getWeatherIcon(weather.weather_code)}.svg`}
                      alt={
                        weather.condition
                          ? `Weather condition: ${weather.condition}`
                          : 'Current weather conditions unavailable'
                      }
                      style={{ height: '70px' }}
                    />
                    <small>{weather.condition || 'Məlumat yoxdur'}</small>
                  </div>
                </div>
                <div className="weather-meta">
                  <span>
                    <i>
                      <FontAwesomeIcon icon={faTemperatureLow} />
                    </i>{' '}
                    Hiss edilən: {displayValue(weather.feels_like, '°C')}
                  </span>
                  <span>
                    <i>
                      <FontAwesomeIcon icon={faWind} />
                    </i>{' '}
                    Külək: {displayValue(weather.wind_speed, ' km/saat')},{' '}
                    {weather.wind_direction || '—'}
                  </span>
                  <span>
                    <i>
                      <FontAwesomeIcon icon={faDroplet} />
                    </i>{' '}
                    Rütubət: {displayValue(weather.humidity, '%')}
                  </span>
                  <span>
                    <i>
                      <FontAwesomeIcon icon={faGaugeHigh} />
                    </i>{' '}
                    Təzyiq: {displayValue(weather.pressure, ' hPa')}
                  </span>
                </div>
              </section>
            </div>
          </section>
          <div className="right-stack">
            <ConversationPanel messages={messages} onSubmit={handleSubmit} />
          </div>
        </div>
      </main>
    </div>
  );
}
