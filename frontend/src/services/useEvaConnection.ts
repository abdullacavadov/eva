import { useCallback, useEffect, useRef, useState } from 'react'
import type { EvaEvent } from '../types/eva'

const DEFAULT_WS_URL = `ws://${window.location.hostname || '127.0.0.1'}:8765`
const WS_URL = import.meta.env.VITE_EVA_WS_URL || DEFAULT_WS_URL
const RECONNECT_DELAY_MS = 1500
const SFX_NAMES = new Set(['HUD', 'Start', 'Think', 'Done', 'Error'])

function playSfx(name: string) {
  if (!SFX_NAMES.has(name)) return
  try {
    const audio = new Audio(`/sfx/${encodeURIComponent(name)}.mp3`)
    audio.volume = 0.45
    void audio.play().catch(() => undefined)
  } catch {
    // Browser audio policy SFX-i UI state-dən ayırmamalıdır.
  }
}

export function useEvaConnection(onEvent: (event: EvaEvent) => void) {
  const socketRef = useRef<WebSocket | null>(null)
  const onEventRef = useRef(onEvent)
  const reconnectRef = useRef<number | null>(null)
  const [socketConnected, setSocketConnected] = useState(false)
  const [liveConnected, setLiveConnected] = useState(false)

  useEffect(() => {
    onEventRef.current = onEvent
  }, [onEvent])

  useEffect(() => {
    let disposed = false

    const scheduleReconnect = () => {
      if (disposed || reconnectRef.current !== null) return
      reconnectRef.current = window.setTimeout(() => {
        reconnectRef.current = null
        connect()
      }, RECONNECT_DELAY_MS)
    }

    const connect = () => {
      if (disposed) return
      const socket = new WebSocket(WS_URL)
      socketRef.current = socket

      socket.onopen = () => {
        if (disposed || socketRef.current !== socket) return
        setSocketConnected(true)
      }

      socket.onmessage = (message) => {
        if (disposed || socketRef.current !== socket) return
        try {
          const event = JSON.parse(message.data) as EvaEvent
          if (event.type === 'live.connection') {
            const status = String(event.status || '')
            setLiveConnected(status === 'connected')
          }
          if (event.type === 'sfx.play') playSfx(String(event.name || ''))
          onEventRef.current(event)
        } catch {
          // Gözlənilməz WebSocket mesajı UI state-i pozmamalıdır.
        }
      }

      socket.onclose = () => {
        if (socketRef.current !== socket) return
        socketRef.current = null
        if (disposed) return
        setSocketConnected(false)
        setLiveConnected(false)
        scheduleReconnect()
      }

      socket.onerror = () => {
        if (socketRef.current === socket) socket.close()
      }
    }

    connect()
    return () => {
      disposed = true
      if (reconnectRef.current !== null) window.clearTimeout(reconnectRef.current)
      reconnectRef.current = null
      socketRef.current?.close()
      socketRef.current = null
    }
  }, [])

  const sendText = useCallback((text: string) => {
    const socket = socketRef.current
    if (!socket || socket.readyState !== WebSocket.OPEN || !liveConnected) return false
    socket.send(JSON.stringify({ type: 'conversation.send', text }))
    return true
  }, [liveConnected])

  return { connected: liveConnected, socketConnected, sendText }
}
