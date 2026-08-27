import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faCamera,
  faMicrophone,
  faPause,
  faPowerOff,
} from '@fortawesome/free-solid-svg-icons'
import '../styles/control-panel.css'

type ControlCommand = 'shutdown' | 'pause' | 'camera' | 'microphone'

interface ControlPanelProps {
  onCommand: (command: ControlCommand) => void
  paused: boolean
  cameraActive: boolean
  microphoneMuted: boolean
  disabled?: boolean
}

const controls: Array<{
  command: ControlCommand
  label: string
  icon: typeof faPowerOff
  tone: string
}> = [
  { command: 'shutdown', label: 'SHUTDOWN', icon: faPowerOff, tone: 'danger' },
  { command: 'pause', label: 'PAUSE', icon: faPause, tone: 'warning' },
  { command: 'camera', label: 'CAMERA', icon: faCamera, tone: 'camera' },
  { command: 'microphone', label: 'MICROPHONE', icon: faMicrophone, tone: 'microphone' },
]

export function ControlPanel({
  onCommand,
  paused,
  cameraActive,
  microphoneMuted,
  disabled = false,
}: ControlPanelProps) {
  const labels: Record<ControlCommand, string> = {
    shutdown: 'SHUTDOWN',
    pause: paused ? 'RESUME' : 'PAUSE',
    camera: cameraActive ? 'CAMERA ON' : 'CAMERA',
    microphone: microphoneMuted ? 'MICROPHONE OFF' : 'MICROPHONE',
  }

  return (
    <section className="panel control-panel">
      <div className="panel-heading">
        <span>EVA NƏZARƏT PANELİ</span>
      </div>

      <div className="control-grid">
        {controls.map(({ command, icon, tone }) => {
          const active =
            (command === 'pause' && paused) ||
            (command === 'camera' && cameraActive) ||
            (command === 'microphone' && !microphoneMuted)

          return (
            <button
              className={`control-button control-button-${tone} ${active ? 'is-active' : ''}`}
              key={command}
              type="button"
              aria-label={labels[command]}
              aria-pressed={command === 'shutdown' ? undefined : active}
              disabled={disabled}
              onClick={() => onCommand(command)}
            >
              <FontAwesomeIcon icon={icon} aria-hidden="true" />
              <span>{labels[command]}</span>
            </button>
          )
        })}
      </div>
    </section>
  )
}

export type { ControlCommand }