import { useEffect, useRef, useState, type CSSProperties } from 'react';
import type { EvaControlState, EvaState } from '../types/eva';
import '../styles/settings-extended.css';

// Sadə 2D Perlin noise (xarici CDN-ə ehtiyac yoxdur)
const perlinPerm = (() => {
  const p = Array.from({ length: 256 }, (_, i) => i);
  for (let i = 255; i > 0; i--) {
    const j = Math.floor(((Math.sin(i * 12.9898) * 43758.5453) % 1) * (i + 1));
    [p[i], p[j]] = [p[j], p[i]];
  }
  return [...p, ...p];
})();
function fade(t: number) {
  return t * t * t * (t * (t * 6 - 15) + 10);
}
function lerp(t: number, a: number, b: number) {
  return a + t * (b - a);
}
function grad(hash: number, x: number, y: number) {
  const h = hash & 3;
  const u = h < 2 ? x : y;
  const v = h < 2 ? y : x;
  return ((h & 1) === 0 ? u : -u) + ((h & 2) === 0 ? v : -v);
}
function perlin2(x: number, y: number) {
  const X = Math.floor(x) & 255,
    Y = Math.floor(y) & 255;
  x -= Math.floor(x);
  y -= Math.floor(y);
  const u = fade(x),
    v = fade(y);
  const a = perlinPerm[X] + Y,
    b = perlinPerm[X + 1] + Y;
  return lerp(
    v,
    lerp(u, grad(perlinPerm[a], x, y), grad(perlinPerm[b], x - 1, y)),
    lerp(
      u,
      grad(perlinPerm[a + 1], x, y - 1),
      grad(perlinPerm[b + 1], x - 1, y - 1)
    )
  );
}

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

const WAVE_LINE_COUNT = 24;
const WAVE_SEG_COUNT = 60;
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
const waveformStrands = Array.from(
  { length: WAVEFORM_STRAND_COUNT },
  (_, index) => {
    const twistPhase = (index / WAVEFORM_STRAND_COUNT) * Math.PI * 2;
    return {
      twistPhase,
      hue: index / Math.max(1, WAVEFORM_STRAND_COUNT - 1),
    };
  }
);

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

    const macroAmplitude =
      WAVEFORM_MAX_AMPLITUDE * 0.75 * envelope * levelFactor;
    const twistAmplitude =
      WAVEFORM_MAX_AMPLITUDE * 0.4 * envelope * levelFactor;

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
  const waveCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const waveformVisibleRef = useRef(false);
  const waveformLevelRef = useRef(0);
  const lastFrameRef = useRef<number | null>(null);

  // Dalğaların faktiki AXMASI üçün zaman-əsaslı animasiya loop-u.
  // Səs səviyyəsi yalnız amplitudanı idarə edir, hərəkəti yox.
  useEffect(() => {
    const canvas = waveCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let raf = 0;
    const draw = () => {
      const level = waveformVisibleRef.current ? waveformLevelRef.current : 0;
      const amp =
        Math.min(1, Math.max(0.06, level * WAVEFORM_GAIN)) *
        (WAVEFORM_HEIGHT / 2 - 4);
      const time = Date.now() / 2500;

      ctx.clearRect(0, 0, WAVEFORM_WIDTH, WAVEFORM_HEIGHT);
      for (let j = 0; j < WAVE_LINE_COUNT; j++) {
        ctx.beginPath();
        ctx.lineWidth = 0.6;
        const hue = j / (WAVE_LINE_COUNT - 1);
        ctx.strokeStyle = strandColor(hue);
        for (let i = 0; i < WAVE_SEG_COUNT; i++) {
          const t = i / (WAVE_SEG_COUNT - 1);
          const x = t * WAVEFORM_WIDTH;
          const envelope = Math.sin(Math.PI * t) ** 0.7;
          const px = t * 3;
          const py = j / 12 + time;
          const y = WAVEFORM_HEIGHT / 2 + perlin2(px, py) * amp * envelope;
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.globalAlpha = waveformVisibleRef.current ? 0.35 : 0.14;
        ctx.stroke();
      }
      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);

    return () => cancelAnimationFrame(raf);
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

  useEffect(() => {
    waveformVisibleRef.current = waveformVisible;
  }, [waveformVisible]);
  useEffect(() => {
    waveformLevelRef.current = waveformLevel;
  }, [waveformLevel]);

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
      <canvas
        ref={waveCanvasRef}
        className={`orb-waveform ${waveformVisible ? 'is-speaking' : 'is-flat'}`}
        width={WAVEFORM_WIDTH}
        height={WAVEFORM_HEIGHT}
        style={{ opacity: 0.8 }}
        aria-hidden="true"
      />
    </section>
  );
}
