import { useEffect, useRef, useState, type CSSProperties } from 'react';
import type { EvaControlState, EvaState } from '../types/eva';
import '../styles/settings-extended.css';

const WS_URL = import.meta.env.VITE_EVA_WS_URL || `ws://${window.location.hostname || '127.0.0.1'}:8765`;
const WAVEFORM_RECONNECT_MS = 1000;
const stateLabel: Record<EvaState, string> = {
  IDLE: 'HAZIRDIR', LISTENING: 'DİNLƏYİR', SPEAKING: 'DANIŞIR', THINKING: 'DÜŞÜNÜR', EXECUTING: 'İCRA EDİR',
  WAITING_CONFIRMATION: 'TƏSDİQ TƏLƏB OLUNUR', SUCCESS: 'TAMAMLANDI', MUTED: 'SƏS SÖNDÜRÜLÜB', PAUSED: 'DAYANDIRILIB', ERROR: 'SİSTEM XƏTASI', INITIALISING: 'BAŞLADILIR',
};
const defaultColors: Record<EvaState, string> = {
  IDLE: '0, 255, 136', LISTENING: '0, 255, 136', SPEAKING: '68, 136, 255', THINKING: '255, 204, 0', EXECUTING: '68, 136, 255',
  WAITING_CONFIRMATION: '255, 204, 0', SUCCESS: '0, 255, 136', MUTED: '200, 30, 80', PAUSED: '30, 60, 55', ERROR: '255, 51, 68', INITIALISING: '255, 51, 68',
};
type OrbSettings = {
  orb_listening_color?: string; orb_speaking_color?: string; orb_thinking_color?: string; orb_muted_color?: string;
  particle_density?: number; particle_speed?: number; glow_intensity?: number; particle_animation_enabled?: boolean;
  glow_enabled?: boolean; pulse_enabled?: boolean; audio_reactive_enabled?: boolean;
};
interface OrbProps { state: EvaState; }

const WAVEFORM_WIDTH = 560;
const WAVEFORM_HEIGHT = 100;
const WAVEFORM_STRANDS = 11;
const WAVEFORM_POINTS = 72;
const WAVEFORM_MAX_AMPLITUDE = 39;

function buildWavePath(level: number, strandIndex: number): string {
  const normalizedLevel = Math.pow(Math.max(0, Math.min(1, level)), 0.55);
  const layer = strandIndex / Math.max(1, WAVEFORM_STRANDS - 1) * 2 - 1;
  const phase = layer * 0.34;
  const layerScale = 0.55 + (1 - Math.abs(layer)) * 0.45;
  const points = Array.from({ length: WAVEFORM_POINTS }, (_, index) => {
    const x = index / (WAVEFORM_POINTS - 1);
    const envelope = Math.sin(Math.PI * x) ** 0.72;
    const shape =
      Math.sin(Math.PI * x * 2 + phase) * 0.72 +
      Math.sin(Math.PI * x * 4 - phase * 1.7) * 0.2 +
      Math.sin(Math.PI * x * 6 + phase * 2.3) * 0.08;
    const y = WAVEFORM_HEIGHT / 2 + shape * envelope * normalizedLevel * WAVEFORM_MAX_AMPLITUDE * layerScale;
    return { x: x * WAVEFORM_WIDTH, y };
  });

  let path = `M ${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`;
  for (let index = 1; index < points.length; index += 1) {
    const previous = points[index - 1];
    const current = points[index];
    const midX = (previous.x + current.x) / 2;
    const midY = (previous.y + current.y) / 2;
    path += ` Q ${previous.x.toFixed(1)} ${previous.y.toFixed(1)} ${midX.toFixed(1)} ${midY.toFixed(1)}`;
  }

  const last = points[points.length - 1];
  const previous = points[points.length - 2];
  path += ` Q ${previous.x.toFixed(1)} ${previous.y.toFixed(1)} ${last.x.toFixed(1)} ${last.y.toFixed(1)}`;
  return path;
}

export function EvaOrb({ state }: OrbProps) {
  const [control, setControl] = useState<EvaControlState>({});
  const [visualSettings, setVisualSettings] = useState<OrbSettings>({});
  const [waveformLevel, setWaveformLevel] = useState(0);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const mountedRef = useRef(true);

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
      if (socketRef.current && socketRef.current.readyState <= WebSocket.OPEN) return;

      const socket = new WebSocket(WS_URL);
      socketRef.current = socket;

      socket.onopen = () => {
        socket.send(JSON.stringify({ type: 'settings.get' }));
      };

      socket.onmessage = event => {
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
          reconnectTimerRef.current = window.setTimeout(connect, WAVEFORM_RECONNECT_MS);
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
      if (reconnectTimerRef.current !== null) window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, []);

  const visualState: EvaState = control.paused ? 'PAUSED' : control.microphone_muted ? 'MUTED' : state;
  const isSpeaking = visualState === 'SPEAKING';
  const audioReactive = visualSettings.audio_reactive_enabled !== false;
  const colorByState: Record<EvaState, string> = { ...defaultColors,
    LISTENING: visualSettings.orb_listening_color || defaultColors.LISTENING,
    SPEAKING: visualSettings.orb_speaking_color || defaultColors.SPEAKING,
    THINKING: visualSettings.orb_thinking_color || defaultColors.THINKING,
    MUTED: visualSettings.orb_muted_color || defaultColors.MUTED,
  };
  const density = Math.max(0, Math.min(100, Number(visualSettings.particle_density ?? 100)));
  const speed = Math.max(0.25, Number(visualSettings.particle_speed ?? 100) / 100);
  const glow = Math.max(0, Math.min(100, Number(visualSettings.glow_intensity ?? 100))) / 100;
  const orbStyle = { '--orb-rgb': colorByState[visualState], '--orb-density': `${density / 100}`, '--orb-speed': `${speed}`, '--orb-glow': `${glow}` } as CSSProperties;
  const waveformVisible = isSpeaking && audioReactive;
  const renderedLevel = waveformVisible ? waveformLevel : 0;
  const waveformStyle: CSSProperties = { opacity: 0.8, animation: 'none' };

  return <section className={`eva-core state-${visualState.toLowerCase()} ${visualSettings.particle_animation_enabled === false ? 'orb-no-particles-animation' : ''} ${visualSettings.glow_enabled === false ? 'orb-no-glow' : ''} ${visualSettings.pulse_enabled === false ? 'orb-no-pulse' : ''} ${visualSettings.audio_reactive_enabled === false ? 'orb-no-audio-reactive' : ''}`} style={orbStyle} aria-label={`EVA ${stateLabel[visualState]}`}>
    <div className="orb-orbit orbit-a" /><div className="orb-orbit orbit-b" /><div className="orb-orbit orbit-c" /><div className="orb-glow" />
    <div className="orb-sphere"><div className="orb-particles particles-a" /><div className="orb-particles particles-b" /><div className="orb-wire">{Array.from({ length: 9 }, (_, index) => <span className="meridian" key={`m-${index}`} />)}{Array.from({ length: 5 }, (_, index) => <span className="latitude" key={`l-${index}`} />)}</div><span className="orb-wordmark">E.V.A</span></div>
    <div className="orb-beam" /><div className="orb-platform"><i /><i /><i /><i /></div><div className="orb-status"><span className="status-dot" />{stateLabel[visualState]}</div>
    <svg className={`orb-waveform ${waveformVisible ? 'is-speaking' : 'is-flat'}`} style={waveformStyle} viewBox={`0 0 ${WAVEFORM_WIDTH} ${WAVEFORM_HEIGHT}`} preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id="eva-wave-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="rgb(var(--orb-rgb))" />
          <stop offset="52%" stopColor="rgb(var(--orb-rgb))" />
          <stop offset="100%" stopColor="#c48cff" />
        </linearGradient>
      </defs>
      {Array.from({ length: WAVEFORM_STRANDS }, (_, index) => (
        <path
          key={index}
          d={buildWavePath(renderedLevel, index)}
          className="orb-wave-strand"
          style={{ opacity: `${0.34 + (1 - Math.abs(index / (WAVEFORM_STRANDS - 1) * 2 - 1)) * 0.44}` }}
        />
      ))}
    </svg>
  </section>;
}
