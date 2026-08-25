export interface Message { id: string; role: 'user' | 'assistant'; text: string }

export function ConversationPanel({ messages, onSubmit }: { messages: Message[]; onSubmit: (text: string) => void }) {
  return (
    <section className="conversation panel">
      <div className="panel-heading"><span>CONVERSATION</span><small>LIVE CHANNEL</small></div>
      <div className="messages">
        {messages.length === 0 && <div className="empty-message">EVA is ready. Start a conversation.</div>}
        {messages.map((message) => (
          <article className={`message ${message.role}`} key={message.id}>
            <span className="message-role">{message.role === 'user' ? 'YOU' : 'EVA'}</span>
            <p>{message.text}</p>
          </article>
        ))}
      </div>
      <form className="command-input" onSubmit={(event) => { event.preventDefault(); const input = event.currentTarget.elements.namedItem('command') as HTMLInputElement; const text = input.value.trim(); if (text) { onSubmit(text); input.value = '' } }}>
        <input name="command" autoComplete="off" placeholder="Ask EVA anything..." aria-label="Ask EVA" />
        <button type="submit" aria-label="Send command">↗</button>
      </form>
    </section>
  )
}
