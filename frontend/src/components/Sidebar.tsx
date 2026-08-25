import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faAddressBook,
  faBell,
  faCalendarDays,
  faComments,
  faEnvelope,
  faGear,
  faGaugeHigh,
  faListCheck,
  faStar,
  faChevronRight,
} from '@fortawesome/free-solid-svg-icons'
import { faWhatsapp } from '@fortawesome/free-brands-svg-icons'

const items = [
  { label: 'İdarə paneli', icon: faGaugeHigh },
  { label: 'Söhbətlər', icon: faComments },
  { label: 'Təqvim', icon: faCalendarDays },
  { label: 'Tapşırıqlar', icon: faListCheck },
  { label: 'E-poçt', icon: faEnvelope },
  { label: 'Kontaktlar', icon: faAddressBook },
  { label: 'Xatırlatmalar', icon: faBell },
  { label: 'WhatsApp', icon: faWhatsapp },
]

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-orb"><span><FontAwesomeIcon icon={faStar} /></span></div>
        <div><strong>EVA</strong><small>ŞƏXSİ ASSİSTENT</small></div>
      </div>
      <nav>
        {items.map((item, index) => (
          <button className={`nav-item ${index === 0 ? 'active' : ''}`} key={item.label}>
            <span className="nav-icon"><FontAwesomeIcon icon={item.icon} /></span>{item.label}
          </button>
        ))}
      </nav>
      <button className="nav-item settings"><span className="nav-icon"><FontAwesomeIcon icon={faGear} /></span>Parametrlər</button>
      <div className="profile">
        <div className="avatar">A</div>
        <div><strong>Abdulla</strong></div>
        <span><FontAwesomeIcon icon={faChevronRight} /></span>
      </div>
    </aside>
  )
}
