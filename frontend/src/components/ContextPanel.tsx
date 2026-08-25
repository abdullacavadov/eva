import type { EvaContext } from '../types/eva'

export function ContextPanel({ context }: { context: EvaContext }) {
  return (
    <section className="panel context-panel">
      <div className="panel-heading"><span>AKTİV KONTEKST</span><small>{context.source ?? 'EVA'}</small></div>
      <div className="context-title">{context.title ?? 'Aktiv kontekst yoxdur'}</div>
      <div className="context-list">
        {context.items.map((item, index) => (
          <button className={`context-item ${item.selected ? 'selected' : ''}`} key={item.id}>
            <span className="context-index">{String(index + 1).padStart(2, '0')}</span>
            <span><strong>{item.title}</strong><small>{item.subtitle ?? item.source}</small></span>
            <span className="context-arrow">›</span>
          </button>
        ))}
      </div>
      <div className="context-footer"><span>{context.items.length} element</span><span>KONTEKST HAZIRDIR</span></div>
    </section>
  )
}
