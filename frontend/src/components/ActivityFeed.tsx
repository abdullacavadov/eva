import type { ActivityItem } from '../types/eva'

export function ActivityFeed({ items }: { items: ActivityItem[] }) {
  return (
    <section className="panel activity-panel">
      <div className="panel-heading"><span>LIVE ACTIVITY</span><small>REALTIME</small></div>
      <div className="activity-list">
        {items.slice(-7).reverse().map((item) => (
          <div className={`activity-item kind-${item.kind}`} key={item.id}>
            <span className="activity-dot" />
            <time>{item.time}</time>
            <div><strong>{item.text}</strong>{item.detail && <small>{item.detail}</small>}</div>
          </div>
        ))}
        {!items.length && <div className="empty-message">Waiting for activity...</div>}
      </div>
    </section>
  )
}
