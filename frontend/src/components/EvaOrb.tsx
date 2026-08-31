import type { EvaControlState, EvaState } from '../types/eva';

const stateLabel: Record<EvaState, string> = {
  IDLE: 'HAZIRDIR',
  LISTENING: 'DİNLƏYİR',
  SPEAKING: 'DANIŞIR',
  THINKING: 'DÜŞÜNÜR',
  EXECUTING: 'İCRA EDİR',
  WAITING_CONFIRMATION: 'TƏSDİQ TƏLƏB OLUNUR',
  SUCCESS: 'TAMAMLANDI',
  MUTED: 'MİKROFON SÖNÜLÜB',
  PAUSED: 'PAUZADADIR',
  ERROR: 'SİSTEM XƏTASI',
  INITIALISING: 'BAŞLADILIR',
};

function getVisualState(
  state: EvaState,
  control?: EvaControlState,
): EvaState {
  if (state === 'ERROR' || state === 'INITIALISING') return state;
  if (control?.microphone_muted) return 'MUTED';
  if (control?.paused) return 'PAUSED';
  return state;
}

export function EvaOrb({
  state,
  control,
}: {
  state: EvaState;
  control?: EvaControlState;
}) {
  const visualState = getVisualState(state, control);

  return (
    <section
      className={`eva-core state-${visualState.toLowerCase()}`}
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
          <span className="meridian" />
          <span className="meridian" />
          <span className="meridian" />
          <span className="meridian" />
          <span className="meridian" />
          <span className="meridian" />
          <span className="meridian" />
          <span className="meridian" />
          <span className="meridian" />
          <span className="latitude" />
          <span className="latitude" />
          <span className="latitude" />
          <span className="latitude" />
          <span className="latitude" />
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
      <div className="orb-waveform" aria-hidden="true">
        {Array.from({ length: 28 }, (_, index) => (
          <i
            key={index}
            style={
              { '--bar': `${16 + ((index * 17) % 54)}%` } as React.CSSProperties
            }
          />
        ))}
      </div>
    </section>
  );
}
