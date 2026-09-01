import { useEffect, useState, type CSSProperties } from 'react';
import type { EvaControlState, EvaState } from '../types/eva';

const stateLabel: Record<EvaState, string> = {
  IDLE: 'HAZIRDIR', LISTENING: 'DİNLƏYİR', SPEAKING: 'DANIŞIR', THINKING: 'DÜŞÜNÜR',
  EXECUTING: 'İCRA EDİR', WAITING_CONFIRMATION: 'TƏSDİQ TƏLƏB OLUNUR', SUCCESS: 'TAMAMLANDI',
  MUTED: 'SƏS SÖNDÜRÜLÜB', PAUSED: 'DAYANDIRILIB', ERROR: 'SİSTEM XƏTASI', INITIALISING: 'BAŞLADILIR',
};

const defaultColors: Record<EvaState, string> = {
  IDLE: '0, 255, 136', LISTENING: '0, 255, 136', SPEAKING: '68, 136, 255', THINKING: '255, 204, 0',
  EXECUTING: '68, 136, 255', WAITING_CONFIRMATION: '255, 204, 0', SUCCESS: '0, 255, 136', MUTED: '200, 30, 80',
  PAUSED: '30, 60, 55', ERROR: '255, 51, 68', INITIALISING: '255, 51, 68',
};

type OrbSettings = {
  orb_listening_color?: string; orb_speaking_color?: string; orb_thinking_color?: string; orb_muted_color?: string;
  particle_density?: number; particle_speed?: number; glow_intensity?: number;
  particle_animation_enabled?: boolean; glow_enabled?: boolean; pulse_enabled?: boolean; audio_reactive_enabled?: boolean;
};

interface EvaOrbProps { state: EvaState; }

export function EvaOrb({ state }: EvaOrbProps) {
  const [control, setControl] = useState<EvaControlState>({});
  const [visualSettings, setVisualSettings] = useState<OrbSettings>({});

  useEffect(() => {
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
    return () => {
      window.removeEventListener('eva:control-state', handleControlState);
      window.removeEventListener('eva:settings', handleSettings);
    };
  }, []);

  const visualState: EvaState = control.paused ? 'PAUSED' : control.microphone_muted ? 'MUTED' : state;
  const colorByState: Record<EvaState, string> = {
    ...defaultColors,
    LISTENING: visualSettings.orb_listening_color || defaultColors.LISTENING,
    SPEAKING: visualSettings.orb_speaking_color || defaultColors.SPEAKING,
    THINKING: visualSettings.orb_thinking_color || defaultColors.THINKING,
    MUTED: visualSettings.orb_muted_color || defaultColors.MUTED,
  };
  const density = Math.max(0, Math.min(100, Number(visualSettings.particle_density ?? 100)));
  const speed = Math.max(0.25, Number(visualSettings.particle_speed ?? 100) / 100);
  const glow = Math.max(0, Math.min(100, Number(visualSettings.glow_intensity ?? 100))) / 100;
  const orbStyle = {
    '--orb-rgb': colorByState[visualState],
    '--orb-density': `${density / 100}`,
    '--orb-speed': `${speed}`,
    '--orb-glow': `${glow}`,
  } as CSSProperties;

  return (
    <section className={`eva-core state-${visualState.toLowerCase()} ${visualSettings.particle_animation_enabled === false ? 'orb-no-particles-animation' : ''} ${visualSettings.glow_enabled === false ? 'orb-no-glow' : ''} ${visualSettings.pulse_enabled === false ? 'orb-no-pulse' : ''} ${visualSettings.audio_reactive_enabled === false ? 'orb-no-audio-reactive' : ''}`} style={orbStyle} aria-label={`EVA ${stateLabel[visualState]}`}>
      <div className="orb-orbit orbit-a" /><div className="orb-orbit orbit-b" /><div className="orb-orbit orbit-c" />
      <div className="orb-glow" /><div className="orb-sphere">
        <div className="orb-particles particles-a" /><div className="orb-particles particles-b" />
        <div className="orb-wire">{Array.from({ length: 9 }, (_, index) => <span className="meridian" key={`m-${index}`} />)}{Array.from({ length: 5 }, (_, index) => <span className="latitude" key={`l-${index}`} />)}</div>
        <span className="orb-wordmark">E.V.A</span>
      </div>
      <div className="orb-beam" /><div className="orb-platform"><i /><i /><i /><i /></div>
      <div className="orb-status"><span className="status-dot" />{stateLabel[visualState]}</div>
      <div className="orb-waveform" aria-hidden="true">{Array.from({ length: 28 }, (_, index) => <i key={index} style={{ '--bar': `${16 + ((index * 17) % 54)}%` } as CSSProperties} />)}</div>
    </section>
  );
}
