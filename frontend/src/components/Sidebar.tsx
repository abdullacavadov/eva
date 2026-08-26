import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faGaugeHigh, faComments, faCalendarDays, faListCheck, faEnvelope, faAddressBook, faBell, faGear, faStar, faChevronRight } from '@fortawesome/free-solid-svg-icons'
import type { IconDefinition } from '@fortawesome/fontawesome-svg-core'

const items: Array<[string, IconDefinition]> = [
  ['İdarə paneli', faGaugeHigh],
  ['Söhbətlər', faComments],
  ['Təqvim', faCalendarDays],
  ['Tapşırıqlar', faListCheck],
  ['E-poçt', faEnvelope],
  ['Kontaktlar', faAddressBook],
  ['Xatırlatmalar', faBell],
  ['WhatsApp', faComments],
]

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-orb"><FontAwesomeIcon icon={faStar} /></div>
        <div><strong>EVA</strong><small>ŞƏXSİ ASSİSTENT</small></div>
      </div>
      <nav>
        {items.map(([item, icon], index) => (
          <button className={`nav-item ${index === 0 ? 'active' : ''}`} key={item}>
            <span className="nav-icon"><FontAwesomeIcon icon={icon} /></span>{item}
          </button>
        ))}
      </nav>
      <button className="nav-item settings"><span className="nav-icon"><FontAwesomeIcon icon={faGear} /></span>Parametrlər</button>
      <div className="profile">
        <div className="avatar">A</div>
        <div><strong>Abdulla</strong><small>SAHİB</small></div>
        <span><FontAwesomeIcon icon={faChevronRight} /></span>
      </div>
    </aside>
  )
}
