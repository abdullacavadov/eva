const items = ['Dashboard', 'Conversations', 'Calendar', 'Tasks', 'Email', 'Contacts', 'Reminders', 'WhatsApp']

const icons: Record<string, string> = {
  Dashboard: '⌂', Conversations: '◌', Calendar: '□', Tasks: '✓', Email: '✉', Contacts: '♙', Reminders: '◔', WhatsApp: '◉',
}

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-orb"><span>✦</span></div>
        <div><strong>EVA</strong><small>PERSONAL AI</small></div>
      </div>
      <nav>
        {items.map((item, index) => (
          <button className={`nav-item ${index === 0 ? 'active' : ''}`} key={item}>
            <span className="nav-icon">{icons[item]}</span>{item}
          </button>
        ))}
      </nav>
      <button className="nav-item settings"><span className="nav-icon">⚙</span>Settings</button>
      <div className="profile">
        <div className="avatar">A</div>
        <div><strong>Abdulla</strong><small>OWNER</small></div>
        <span>›</span>
      </div>
    </aside>
  )
}
