import { useCallback, useEffect, useRef, useState } from 'react'
import type { EvaEvent } from '../types/eva'

const DEFAULT_WS_URL = `ws://${window.location.hostname || '127.0.0.1'}:8765`
const WS_URL = import.meta.env.VITE_EVA_WS_URL || DEFAULT_WS_URL
const RECONNECT_DELAY_MS = 1500

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
        setConnected(true)
      }

      socket.onmessage = (message) => {
        if (disposed || socketRef.current !== socket) return
        try {
          const event = JSON.parse(message.data) as EvaEvent
          if (event.type === 'webcam.frame') {
            window.dispatchEvent(new CustomEvent('eva:webcam-frame', { detail: event.data }))
          }
          if (event.type === 'control.state') {
            window.dispatchEvent(new CustomEvent('eva:control-state', { detail: event.control }))
          }
          if (event.type === 'runtime.snapshot' && event.control) {
            window.dispatchEvent(new CustomEvent('eva:control-state', { detail: event.control }))
          }
          onEventRef.current(event)
        } catch {
          // Gözlənilməz WebSocket mesajı UI state-i pozmamalıdır.
        }
      }

      socket.onclose = () => {
        if (socketRef.current !== socket) return
        socketRef.current = null
        if (disposed) return
        setConnected(false)
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

  const sendMessage = useCallback((message: Record<string, unknown>) => {
    const socket = socketRef.current
    if (!socket || socket.readyState !== WebSocket.OPEN) return false
    socket.send(JSON.stringify(message))
    return true
  }, [])

  const sendText = useCallback((text: string) => {
    return sendMessage({ type: 'conversation.send', text })
  }, [sendMessage])

  const sendControl = useCallback((command: 'shutdown' | 'pause' | 'camera' | 'microphone') => {
    return sendMessage({ type: 'control.command', command })
  }, [sendMessage])

  return { connected, sendText, sendControl }
}
