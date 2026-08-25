import type { EvaEvent } from '../types/eva'

export interface EvaTransport {
  connect(): void
  disconnect(): void
  send(event: EvaEvent): void
  subscribe(listener: (event: EvaEvent) => void): () => void
}

export class EvaWebSocketTransport implements EvaTransport {
  private socket: WebSocket | null = null
  private listeners = new Set<(event: EvaEvent) => void>()

  constructor(private readonly url = 'ws://localhost:8765') {}

  connect() {
    if (this.socket || typeof WebSocket === 'undefined') return
    this.socket = new WebSocket(this.url)
    this.socket.onmessage = (message) => {
      try {
        const event = JSON.parse(message.data) as EvaEvent
        this.listeners.forEach((listener) => listener(event))
      } catch {
        // Malformed gateway events are ignored until the backend contract is active.
      }
    }
    this.socket.onclose = () => {
      this.socket = null
    }
  }

  disconnect() {
    this.socket?.close()
    this.socket = null
  }

  send(event: EvaEvent) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(event))
    }
  }

  subscribe(listener: (event: EvaEvent) => void) {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }
}
