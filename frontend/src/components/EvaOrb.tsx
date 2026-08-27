import type { CSSProperties } from 'react'
import type { EvaState } from '../types/eva'

const stateLabel: Record<EvaState, string> = {
  IDLE: 'HAZIRDIR',
  LISTENING: 'DİNLƏYİR',
  THINKING: 'DÜŞÜNÜR',
  EXECUTING: 'İCRA EDİR',
  WAITING_CONFIRMATION: 'TƏSDİQ TƏLƏB OLUNUR',
  SUCCESS: 'TAMAMLANDI',
  ERROR: 'SİSTEM XƏTASI',
}

const stateColors: Record<EvaState, string> = {
  IDLE: '#45D9FF',
  LISTENING: '#00FF88',
  THINKING: '#FFCC00',
  EXECUTING: '#4488FF',
  WAITING_CONFIRMATION: '#FFC857',
  SUCCESS: '#43E6AA',
  ERROR: '#FF3344',
}

const withAlpha = (hex: string, alpha: string) => {
  const value = hex.replace('#', '')
  const r = Number.parseInt(value.slice(0, 2), 16)
  const g = Number.parseInt(value.slice(2, 4), 16)
  const b = Number.parseInt(value.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

export function EvaOrb({ state }: { state: EvaState }) {
  const color = stateColors[state]
  const glow = withAlpha(color, '0.16')
  const softGlow = withAlpha(color, '0.08')
  const strongGlow = withAlpha(color, '0.72')

  const orbStyle = {
    '--orb-color': color,
    '--orb-glow': glow,
    '--orb-soft-glow': softGlow,
    '--orb-strong-glow': strongGlow,
  } as CSSProperties

  const particleStyle = (opacity: number, size: string, duration: string): CSSProperties => ({
    backgroundImage: `radial-gradient(circle, ${withAlpha(color, String(opacity))} 0 ${size}, transparent ${size})`,
    animationDuration: duration,
  })

  return (
    <section
      className={`eva-core state-${state.toLowerCase()}`}
      aria-label={`EVA ${stateLabel[state]}`}
      style={orbStyle}
    >
      <div className="orb-orbit orbit-a" style={{ borderColor: withAlpha(color, '0.32'), boxShadow: `0 0 12px ${softGlow}` }} />
      <div className="orb-orbit orbit-b" style={{ borderColor: withAlpha(color, '0.24'), boxShadow: `0 0 16px ${softGlow}` }} />
      <div className="orb-orbit orbit-c" style={{ borderColor: withAlpha(color, '0.20') }} />

      <div
        className="orb-glow"
        style={{ background: glow, boxShadow: `0 0 70px ${softGlow}` }}
      />

      <div
        className="orb-sphere"
        style={{
          borderColor: withAlpha(color, '0.58'),
          background: `radial-gradient(circle at 42% 36%, ${withAlpha(color, '0.20')}, rgba(3, 26, 39, .72) 43%, rgba(1, 8, 13, .95) 70%)`,
          boxShadow: `0 0 36px ${softGlow}, inset 0 0 45px ${softGlow}`,
        }}
      >
        <div className="orb-grid" style={{ opacity: state === 'THINKING' ? 1 : undefined }} />
        <div className="orb-particles particles-a" style={particleStyle(.95, '1px', state === 'THINKING' ? '4s' : '8s')} />
        <div className="orb-particles particles-b" style={particleStyle(.55, '1px', state === 'EXECUTING' ? '5s' : '11s')} />
        <div className="orb-particles particles-c" style={particleStyle(.78, '1.2px', state === 'LISTENING' ? '3.5s' : '7s')} />
        <div className="orb-particles particles-d" style={particleStyle(.48, '.8px', state === 'ERROR' ? '2.5s' : '9s')} />
        <span
          className="orb-wordmark"
          style={{ color: '#D8F7FF', textShadow: `0 0 14px ${color}, 0 0 38px ${withAlpha(color, '0.62')}` }}
        >
          E.V.A
        </span>
      </div>

      <div
        className="orb-beam"
        style={{ background: `linear-gradient(transparent, ${withAlpha(color, '0.62')}, transparent)`, boxShadow: `0 0 30px 5px ${softGlow}` }}
      />

      <div
        className="orb-platform"
        style={{ borderColor: withAlpha(color, '0.34'), boxShadow: `0 0 22px ${softGlow}, inset 0 0 22px ${softGlow}` }}
      >
        <i style={{ background: color, boxShadow: `0 0 8px ${color}` }} />
        <i style={{ background: color, boxShadow: `0 0 8px ${color}` }} />
        <i style={{ background: color, boxShadow: `0 0 8px ${color}` }} />
        <i style={{ background: color, boxShadow: `0 0 8px ${color}` }} />
      </div>

      <div className="orb-status">
        <span
          className="status-dot"
          style={{ background: color, boxShadow: `0 0 10px ${color}` }}
        />
        {stateLabel[state]}
      </div>

      <div className="orb-waveform" aria-hidden="true">
        {Array.from({ length: 28 }, (_, index) => (
          <i
            key={index}
            style={{
              '--bar': `${16 + ((index * 17) % 54)}%`,
              background: color,
              boxShadow: `0 0 8px ${withAlpha(color, '0.70')}`,
            } as CSSProperties}
          />
        ))}
      </div>
    </section>
  )
}
