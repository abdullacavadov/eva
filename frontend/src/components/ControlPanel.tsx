import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faCamera,
  faMicrophone,
  faPause,
  faPowerOff,
} from '@fortawesome/free-solid-svg-icons';

const controls = [
  { label: 'SHUTDOWN', icon: faPowerOff, tone: 'danger' },
  { label: 'PAUSE', icon: faPause, tone: 'warning' },
  { label: 'CAMERA', icon: faCamera, tone: 'camera' },
  { label: 'MICROPHONE', icon: faMicrophone, tone: 'microphone' },
] as const;

export function ControlPanel() {
  return (
    <section className="panel control-panel">
      <div className="panel-heading">
        <span>EVA NƏZARƏT PANELİ</span>
      </div>

      <div className="control-grid">
        {controls.map(({ label, icon, tone }) => (
          <button
            className={`control-button control-button-${tone}`}
            key={label}
            type="button"
            aria-label={label}
          >
            <FontAwesomeIcon icon={icon} aria-hidden="true" />
            <span>{label}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
