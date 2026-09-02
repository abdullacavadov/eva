import { useEffect, useRef, useState, type CSSProperties } from 'react';
import type { EvaControlState, EvaState } from '../types/eva';
import '../styles/settings-extended.css';

const WS_URL =
  import.meta.env.VITE_EVA_WS_URL ||
  `ws://${window.location.hostname || '127.0.0.1'}:8765`;
const WAVEFORM_RECONNECT_MS = 1000;
const stateLabel: Record<EvaState, string> = {
  IDLE: 'HAZIRDIR',
  LISTENING: 'DİNLƏYİR',
  SPEAKING: 'DANIŞIR',
  THINKING: 'DÜŞÜNÜR',
  EXECUTING: 'İCRA EDİR',
  WAITING_CONFIRMATION: 'TƏSDİQ TƏLƏB OLUNUR',
  SUCCESS: 'TAMAMLANDI',
  MUTED: 'SƏS SÖNDÜRÜLÜB',
  PAUSED: 'DAYANDIRILIB',
  ERROR: 'SİSTEM XƏTASI',
  INITIALISING: 'BAŞLADILIR',
};
const defaultColors: Record<EvaState, string> = {
  IDLE: '0, 255, 136',
  LISTENING: '0, 255, 136',
  SPEAKING: '68, 136, 255',
  THINKING: '255, 204, 0',
  EXECUTING: '68, 136, 255',
  WAITING_CONFIRMATION: '255, 204, 0',
  SUCCESS: '0, 255, 136',
  MUTED: '200, 30, 80',
  PAUSED: '30, 60, 55',
  ERROR: '255, 51, 68',
  INITIALISING: '255, 51, 68',
};
type OrbSettings = {
  orb_listening_color?: string;
  orb_speaking_color?: string;
  orb_thinking_color?: string;
  orb_muted_color?: string;
  particle_density?: number;
  particle_speed?: number;
  glow_intensity?: number;
  particle_animation_enabled?: boolean;
  glow_enabled?: boolean;
  pulse_enabled?: boolean;
  audio_reactive_enabled?: boolean;
};
interface OrbProps {
  state: EvaState;
}

const WAVEFORM_WIDTH = 560;
const WAVEFORM_HEIGHT = 110;
const WAVEFORM_GAIN = 13;
const WAVEFORM_STRAND_COUNT = 5;
const WAVEFORM_DOTS_PER_STRAND = 80;
const WAVEFORM_MAX_AMPLITUDE = 30;
const WAVEFORM_DUST_COUNT = 60;
// Böyük, ümumi dalğa forması (bütün lentlərin BİRGƏ izlədiyi macro əyri).
const WAVEFORM_MACRO_FREQ_1 = 1.05;
const WAVEFORM_MACRO_FREQ_2 = 1.7;
// Lentlərin bir-birini keçib "hörülmə" effekti üçün yerli fırlanma (twist).
const WAVEFORM_TWIST_FREQ = 3.4;
const WAVEFORM_TWIST_SPEED = 0.55;

// Arxa fonda üzən toz hissəcikləri (statik yerləşim, yalnız parıltısı canlıdır).
const waveformDust = Array.from({ length: WAVEFORM_DUST_COUNT }, (_, index) => {
  const seed = Math.sin(index * 91.17) * 43758.5453;
  const random = seed - Math.floor(seed);
  const seed2 = Math.sin(index * 53.9 + 12.3) * 12543.117;
  const random2 = seed2 - Math.floor(seed2);
  return {
    x: 2 + random * 96,
    y: 10 + random2 * 80,
    radius: 0.3 + random2 * 0.8,
    baseOpacity: 0.06 + random * 0.16,
    twinkle: 0.4 + random2 * 1.6,
  };
});

// Bütün lentlər EYNİ böyük dalğanı (macro) izləyir, lakin hər birinin öz
// "twist" fazası var — sanki lent bir ip kimi öz oxu ətrafında burulur və
// bu burulma zamanla fırlanır (WAVEFORM_TWIST_SPEED). Nəticə: ayrı-ayrı
// laylar yox, TƏK, hörülmüş, real vaxtda hərəkət edən bir lent görünüşü.
const waveformStrands = Array.from({ length: WAVEFORM_STRAND_COUNT }, (_, index) => {
  const twistPhase = (index / WAVEFORM_STRAND_COUNT) * Math.PI * 2;
  return {
    twistPhase,
    hue: index / Math.max(1, WAVEFORM_STRAND_COUNT - 1),
  };
});

function getStrandPoints(
  level: number,
  strand: (typeof waveformStrands)[number],
  time: number
) {
  const amplifiedLevel = Math.min(1, Math.max(0, level) * WAVEFORM_GAIN);
  const normalizedLevel = Math.pow(amplifiedLevel, 0.45);
  const idleLevel = 0.18; // audio olmasa belə lent tam düz qalmasın
  const levelFactor = Math.max(idleLevel, normalizedLevel);

  return Array.from({ length: WAVEFORM_DOTS_PER_STRAND }, (_, i) => {
    const t = i / (WAVEFORM_DOTS_PER_STRAND - 1);
    // Uclarda nazikləşən, mərkəzdə güclü zərf (edge-də lent demək olar ki yox olur).
    const envelope = Math.sin(Math.PI * t) ** 0.7;

    // Ümumi (macro) dalğa forması — bütün lentlər buna tabedir.
    // İki fərqli sürətlə zamanla sürüşür ki, forma da dəyişsin, sadəcə axmasın.
    const macroShape =
      Math.sin(t * Math.PI * WAVEFORM_MACRO_FREQ_1 * 2 + time * 0.32) * 0.65 +
      Math.sin(t * Math.PI * WAVEFORM_MACRO_FREQ_2 * 2 - time * 0.21) * 0.35;

    // Yerli burulma (twist) — hər lentin öz fazası ilə eyni sürətdə fırlanır,
    // bu da lentlərin real vaxtda bir-birini keçməsinə səbəb olur.
    const twistShape = Math.sin(
      t * Math.PI * WAVEFORM_TWIST_FREQ * 2 +
        strand.twistPhase +
        time * WAVEFORM_TWIST_SPEED
    );

    const macroAmplitude = WAVEFORM_MAX_AMPLITUDE * 0.75 * envelope * levelFactor;
    const twistAmplitude = WAVEFORM_MAX_AMPLITUDE * 0.4 * envelope * levelFactor;

    return {
      x: t * WAVEFORM_WIDTH,
      y:
        WAVEFORM_HEIGHT / 2 +
        macroShape * macroAmplitude +
        twistShape * twistAmplitude,
      // Lentin özü ilə kəsişdiyi (twist pik) nöqtələrdə daha sıx/parlaq nöqtə.
      density: 0.3 + Math.abs(twistShape) * 0.7,
    };
  });
}

function strandColor(hue: number, coreLine = false): string {
  // 0 -> mavi/cyan, 0.5 -> ağımtıl mavi, 1 -> bənövşəyi/çəhrayı
  if (coreLine) return 'rgba(255,255,255,0.9)';
  if (hue < 0.5) {
    return `rgba(${64 + hue * 2 * 60}, ${170 + hue * 2 * 40}, 255, 0.9)`;
  }
  const t = (hue - 0.5) * 2;
  return `rgba(${124 + t * 100}, ${150 - t * 40}, ${255 - t * 30}, 0.9)`;
}

export function EvaOrb({ state }: OrbProps) {
  const [control, setControl] = useState<EvaControlState>({});
  const [visualSettings, setVisualSettings] = useState<OrbSettings>({});
  const [waveformLevel, setWaveformLevel] = useState(0);
  const [waveTime, setWaveTime] = useState(0);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const mountedRef = useRef(true);
  const waveAnimationRef = useRef<number | null>(null);
  const lastFrameRef = useRef<number | null>(null);

  // Dalğaların faktiki AXMASI üçün zaman-əsaslı animasiya loop-u.
  // Səs səviyyəsi yalnız amplitudanı idarə edir, hərəkəti yox.
  useEffect(() => {
    const FRAME_INTERVAL = 1000 / 30; // ~30fps kifayətdir, hamar görünür
    const tick = (timestamp: number) => {
      if (lastFrameRef.current === null) lastFrameRef.current = timestamp;
      const elapsed = timestamp - lastFrameRef.current;
      if (elapsed >= FRAME_INTERVAL) {
        lastFrameRef.current = timestamp;
        setWaveTime((previous) => previous + elapsed / 1000);
      }
      waveAnimationRef.current = requestAnimationFrame(tick);
    };
    waveAnimationRef.current = requestAnimationFrame(tick);
    return () => {
      if (waveAnimationRef.current !== null)
        cancelAnimationFrame(waveAnimationRef.current);
      lastFrameRef.current = null;
    };
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    const handleControlState = (event: Event) => {
      const detail = (event as CustomEvent<EvaControlState>).detail;
      if (detail && typeof detail === 'object') setControl(detail);
    };
    const handleSettings = (event: Event) => {
      const detail = (event as CustomEvent<OrbSettings>).detail;
      if (detail && typeof detail === 'object') setVisualSettings(detail);
    };

    window.addEventListener('eva:control-state', handleControlState);
    window.addEventListener('eva:settings', handleSettings);

    const connect = () => {
      if (!mountedRef.current) return;
      if (socketRef.current && socketRef.current.readyState <= WebSocket.OPEN)
        return;

      const socket = new WebSocket(WS_URL);
      socketRef.current = socket;

      socket.onopen = () => {
        socket.send(JSON.stringify({ type: 'settings.get' }));
      };

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'settings.state') {
            setVisualSettings(message.settings || {});
            return;
          }
          if (message.type === 'audio.level') {
            const level = Math.max(0, Math.min(1, Number(message.level) || 0));
            setWaveformLevel(level);
          }
        } catch {
          // Yanlış WebSocket mesajlarını UI-ı pozmadan keç.
        }
      };

      socket.onclose = () => {
        if (socketRef.current === socket) socketRef.current = null;
        if (mountedRef.current) {
          reconnectTimerRef.current = window.setTimeout(
            connect,
            WAVEFORM_RECONNECT_MS
          );
        }
      };

      socket.onerror = () => {
        socket.close();
      };
    };

    connect();

    return () => {
      mountedRef.current = false;
      window.removeEventListener('eva:control-state', handleControlState);
      window.removeEventListener('eva:settings', handleSettings);
      if (reconnectTimerRef.current !== null)
        window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, []);

  const visualState: EvaState = control.paused
    ? 'PAUSED'
    : control.microphone_muted
      ? 'MUTED'
      : state;
  const isSpeaking = visualState === 'SPEAKING';
  const audioReactive = visualSettings.audio_reactive_enabled !== false;
  const colorByState: Record<EvaState, string> = {
    ...defaultColors,
    LISTENING: visualSettings.orb_listening_color || defaultColors.LISTENING,
    SPEAKING: visualSettings.orb_speaking_color || defaultColors.SPEAKING,
    THINKING: visualSettings.orb_thinking_color || defaultColors.THINKING,
    MUTED: visualSettings.orb_muted_color || defaultColors.MUTED,
  };
  const density = Math.max(
    0,
    Math.min(100, Number(visualSettings.particle_density ?? 100))
  );
  const speed = Math.max(
    0.25,
    Number(visualSettings.particle_speed ?? 100) / 100
  );
  const glow =
    Math.max(0, Math.min(100, Number(visualSettings.glow_intensity ?? 100))) /
    100;
  const orbStyle = {
    '--orb-rgb': colorByState[visualState],
    '--orb-density': `${density / 100}`,
    '--orb-speed': `${speed}`,
    '--orb-glow': `${glow}`,
  } as CSSProperties;
  const waveformVisible = isSpeaking && audioReactive;
  const renderedLevel = waveformVisible ? waveformLevel : 0;
  const amplifiedLevel = Math.min(1, renderedLevel * WAVEFORM_GAIN);
  const waveformStyle: CSSProperties = { opacity: 0.8, animation: 'none' };

  return (
    <section
      className={`eva-core state-${visualState.toLowerCase()} ${visualSettings.particle_animation_enabled === false ? 'orb-no-particles-animation' : ''} ${visualSettings.glow_enabled === false ? 'orb-no-glow' : ''} ${visualSettings.pulse_enabled === false ? 'orb-no-pulse' : ''} ${visualSettings.audio_reactive_enabled === false ? 'orb-no-audio-reactive' : ''}`}
      style={orbStyle}
      aria-label={`EVA ${stateLabel[visualState]}`}
    >
      <div className="orb-orbit orbit-a" />
      <div className="orb-orbit orbit-b" />
      <div className="orb-orbit orbit-c" />
      <div className="orb-glow" />
      <div className="orb-sphere">
        <div className="orb-particles particles-a" />
        <div className="orb-particles particles-b" />
        <div className="orb-wire">
          {Array.from({ length: 9 }, (_, index) => (
            <span className="meridian" key={`m-${index}`} />
          ))}
          {Array.from({ length: 5 }, (_, index) => (
            <span className="latitude" key={`l-${index}`} />
          ))}
        </div>
        <span className="orb-wordmark">E.V.A</span>
      </div>
      <div className="orb-beam" />
      <div className="orb-platform">
        <i />
        <i />
        <i />
        <i />
      </div>
      <div className="orb-status">
        <span className="status-dot" />
        {stateLabel[visualState]}
      </div>
      <svg
        className={`orb-waveform ${waveformVisible ? 'is-speaking' : 'is-flat'}`}
        style={waveformStyle}
        viewBox={`0 0 ${WAVEFORM_WIDTH} ${WAVEFORM_HEIGHT}`}
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <defs>
          <filter
            id="eva-wave-glow"
            x="-40%"
            y="-140%"
            width="180%"
            height="380%"
          >
            <feGaussianBlur stdDeviation="1.6" result="softBlur" />
            <feGaussianBlur in="SourceGraphic" stdDeviation="4.5" result="wideBlur" />
            <feMerge>
              <feMergeNode in="wideBlur" />
              <feMergeNode in="softBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Arxa fon tozu - sabit, yalnız parıltısı canlıdır */}
        {waveformDust.map((particle, index) => (
          <circle
            key={`dust-${index}`}
            cx={`${particle.x}%`}
            cy={`${particle.y}%`}
            r={particle.radius}
            fill="#bcd8ff"
            style={{
              opacity: waveformVisible
                ? particle.baseOpacity *
                  (0.5 + amplifiedLevel * particle.twinkle)
                : particle.baseOpacity * 0.3,
              transition: 'opacity 220ms ease-out',
            }}
          />
        ))}

        {/* Dalğavari hissəcik lentləri (mesh) */}
        <g filter="url(#eva-wave-glow)">
          {waveformStrands.map((strand, strandIndex) => {
            const points = getStrandPoints(renderedLevel, strand, waveTime);
            const linePath = points
              .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
              .join(' ');
            return (
              <g key={`strand-${strandIndex}`}>
                <path
                  d={linePath}
                  fill="none"
                  stroke={strandColor(strand.hue)}
                  strokeWidth={0.6}
                  style={{
                    opacity: waveformVisible ? 0.35 : 0.14,
                    transition: 'opacity 160ms ease-out',
                  }}
                />
                {points.map((p, i) => {
                  if (i % 1 !== 0) return null;
                  const radius = 0.5 + p.density * 1.5;
                  return (
                    <circle
                      key={`s${strandIndex}-d${i}`}
                      cx={p.x}
                      cy={p.y}
                      r={radius}
                      fill={strandColor(strand.hue)}
                      style={{
                        opacity: waveformVisible
                          ? 0.35 + p.density * 0.55
                          : 0.16,
                        transition: 'cy 90ms ease-out, opacity 140ms ease-out',
                      }}
                    />
                  );
                })}
              </g>
            );
          })}
        </g>
      </svg>
    </section>
  );
}
