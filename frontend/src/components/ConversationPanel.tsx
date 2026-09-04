import { useEffect, useRef } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCircleArrowUp } from '@fortawesome/free-solid-svg-icons';

export interface Message { id: string; role: 'user' | 'assistant'; text: string }

export function ConversationPanel({ messages, onSubmit }: { messages: Message[]; onSubmit: (text: string) => void }) {
  const messagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = messagesRef.current;
    if (!container) return;
    container.scrollTop = container.scrollHeight;
  }, [messages]);

  return (
    <section className="conversation panel">
      <div className="panel-heading"><span>SÖHBƏT</span><small>CANLI KANAL</small></div>
      <div className="messages" ref={messagesRef}>
        {messages.length === 0 && <div className="empty-message">EVA hazırdır. Söhbətə başla.</div>}
        {messages.map((message) => (
          <article className={`message ${message.role}`} key={message.id}>
            <span className="message-role">{message.role === 'user' ? 'SƏN' : 'EVA'}</span>
            <p>{message.text}</p>
          </article>
        ))}
      </div>
      <form className="command-input" onSubmit={(event) => { event.preventDefault(); const input = event.currentTarget.elements.namedItem('command') as HTMLInputElement; const text = input.value.trim(); if (text) { onSubmit(text); input.value = '' } }}>
        <input name="command" autoComplete="off" placeholder="EVA-ya istənilən sualı ver..." aria-label="EVA-ya sual ver" />
        <button type="submit" aria-label="Komandanı göndər"><FontAwesomeIcon icon={faCircleArrowUp} /></button>
      </form>
    </section>
  )
}
