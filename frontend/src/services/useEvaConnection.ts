import { useCallback, useEffect, useRef, useState } from 'react'
import type { EvaEvent } from '../types/eva'

const DEFAULT_WS_URL = `ws://${window.location.hostname || '127.0.0.1'}:8765`
const WS_URL = import.meta.env.VITE_EVA_WS_URL || DEFAULT_WS_URL

export function useEvaConnection(onEvent: (event: EvaEvent) => void) {
  const socketRef = useRef<WebSocket | null>(null)
  const onEventRef = useRef(onEvent)
  const reconnectRef = useRef<number | null>(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    onEventRef.current = onEvent
  }, [onEvent])

  useEffect(() => {
    let disposed = false

    const connect = () => {
      if (disposed) return
      const socket = new WebSocket(WS_URL)
      socketRef.current = socket

      socket.onopen = () => {
        if (!disposed) setConnected(true)
      }
      socket.onmessage = (message) => {
        try {
          const event = JSON.parse(message.data) as EvaEvent
          onEventRef.current(event)
        } catch {
          // WebSocket protokolundakı gözlənilməz mesaj UI state-i pozmamalıdır.
        }
      }
      socket.onclose = () => {
        if (disposed) return
        setConnected(false)
        reconnectRef.current = window.setTimeout(connect, 1500)
      }
      socket.onerror = () => {
        socket.close()
      }
    }

    connect()
    return () => {
      disposed = true
      if (reconnectRef.current !== null) window.clearTimeout(reconnectRef.current)
      socketRef.current?.close()
      socketRef.current = null
    }
  }, [])

  const sendText = useCallback((text: string) => {
    const socket = socketRef.current
    if (!socket || socket.readyState !== WebSocket.OPEN) return false
    socket.send(JSON.stringify({ type: 'conversation.send', text }))
    return true
  }, [])

  return { connected, sendText }
}
