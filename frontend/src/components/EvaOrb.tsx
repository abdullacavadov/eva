import type { EvaState } from '../types/eva'

const stateLabel: Record<EvaState, string> = {
  IDLE: 'READY',
  LISTENING: 'LISTENING',
  THINKING: 'THINKING',
  EXECUTING: 'EXECUTING',
  WAITING_CONFIRMATION: 'CONFIRMATION REQUIRED',
  SUCCESS: 'COMPLETE',
  ERROR: 'SYSTEM ERROR',
}

export function EvaOrb({ state }: { state: EvaState }) {
  return (
    <section className={`eva-core state-${state.toLowerCase()}`} aria-label={`EVA ${stateLabel[state]}`}>
      <div className="orb-orbit orbit-a" />
      <div className="orb-orbit orbit-b" />
      <div className="orb-orbit orbit-c" />
      <div className="orb-glow" />
      <div className="orb-sphere">
        <div className="orb-grid" />
        <div className="orb-particles particles-a" />
        <div className="orb-particles particles-b" />
        <span className="orb-wordmark">EVA</span>
      </div>
      <div className="orb-beam" />
      <div className="orb-platform">
        <i /><i /><i /><i />
      </div>
      <div className="orb-status">
        <span className="status-dot" />
        {stateLabel[state]}
      </div>
      <div className="orb-waveform" aria-hidden="true">
        {Array.from({ length: 28 }, (_, index) => <i key={index} style={{ '--bar': `${16 + ((index * 17) % 54)}%` } as React.CSSProperties} />)}
      </div>
    </section>
  )
}
