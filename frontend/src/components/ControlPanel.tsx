import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faCamera,
  faMicrophone,
  faPause,
  faPowerOff,
} from '@fortawesome/free-solid-svg-icons';
import '../styles/control-panel.css';

const controls = [
  { label: 'SÖNDÜR', icon: faPowerOff, tone: 'danger' },
  { label: 'FASİLƏ', icon: faPause, tone: 'warning' },
  { label: 'KAMERA', icon: faCamera, tone: 'camera' },
  { label: 'MİKROFON', icon: faMicrophone, tone: 'microphone' },
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
