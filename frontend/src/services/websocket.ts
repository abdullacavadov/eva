import type { VictorEvent } from '../types/victor.ts'

export interface VictorTransport {
  connect(): void
  disconnect(): void
  send(event: VictorEvent): void
  subscribe(listener: (event: VictorEvent) => void): () => void
}

export class VictorWebSocketTransport implements VictorTransport {
  private socket: WebSocket | null = null
  private listeners = new Set<(event: VictorEvent) => void>()

  constructor(private readonly url = 'ws://localhost:8765') {}

  connect() {
    if (this.socket || typeof WebSocket === 'undefined') return
    this.socket = new WebSocket(this.url)
    this.socket.onmessage = (message) => {
      try {
        const event = JSON.parse(message.data) as VictorEvent
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

  send(event: VictorEvent) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(event))
    }
  }

  subscribe(listener: (event: VictorEvent) => void) {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }
}
