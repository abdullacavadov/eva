import { useEffect, useState, type CSSProperties } from 'react';
import type { EvaControlState, EvaState } from '../types/eva';
//import '../styles/eva-orb-state.css';

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

const stateColors: Record<EvaState, string> = {
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

interface EvaOrbProps {
  state: EvaState;
}

export function EvaOrb({ state }: EvaOrbProps) {
  const [control, setControl] = useState<EvaControlState>({});

  useEffect(() => {
    const handleControlState = (event: Event) => {
      const detail = (event as CustomEvent<EvaControlState>).detail;
      if (detail && typeof detail === 'object') setControl(detail);
    };
    window.addEventListener('eva:control-state', handleControlState);
    return () => window.removeEventListener('eva:control-state', handleControlState);
  }, []);

  const visualState: EvaState = control.paused
    ? 'PAUSED'
    : control.microphone_muted
      ? 'MUTED'
      : state;
  const orbStyle = { '--orb-rgb': stateColors[visualState] } as CSSProperties;

  return (
    <section
      className={`eva-core state-${visualState.toLowerCase()}`}
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
          {Array.from({ length: 9 }, (_, index) => <span className="meridian" key={`m-${index}`} />)}
          {Array.from({ length: 5 }, (_, index) => <span className="latitude" key={`l-${index}`} />)}
        </div>
        <span className="orb-wordmark">E.V.A</span>
      </div>
      <div className="orb-beam" />
      <div className="orb-platform"><i /><i /><i /><i /></div>
      <div className="orb-status">
        <span className="status-dot" />
        {stateLabel[visualState]}
      </div>
      <div className="orb-waveform" aria-hidden="true">
        {Array.from({ length: 28 }, (_, index) => (
          <i key={index} style={{ '--bar': `${16 + ((index * 17) % 54)}%` } as CSSProperties} />
        ))}
      </div>
    </section>
  );
}
