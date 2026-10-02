import { useEffect, useRef, useState } from 'react'
import { API_BASE } from './api'

export interface WorldEvent {
  id: number | string
  kind: string
  text: string
  created_at: string
  lat?: number | null
  lon?: number | null
  live?: boolean
}

/**
 * 📡 WebSocket زنده /ws/world/ — رویدادهای جهان بدون refresh.
 * روی قطع اتصال، وضعیت disconnected برمی‌گرداند تا UI به polling برود.
 */
export function useWorldSocket(onEvent?: (e: WorldEvent) => void) {
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const retryRef = useRef(0)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const cbRef = useRef(onEvent)
  cbRef.current = onEvent

  useEffect(() => {
    let closed = false

    const connect = () => {
      if (closed) return
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${proto}://${window.location.host}${API_BASE}/ws/world/`)
      wsRef.current = ws
      ws.onopen = () => { retryRef.current = 0; setConnected(true) }
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data)
          if (data.type === 'event' && data.payload) cbRef.current?.({ ...data.payload, live: true })
        } catch { /* ignore bad frame */ }
      }
      ws.onclose = () => {
        setConnected(false)
        if (closed) return
        retryRef.current += 1
        const delay = Math.min(30000, 2000 * retryRef.current) // backoff تا ۳۰ ثانیه
        timerRef.current = setTimeout(connect, delay)
      }
      ws.onerror = () => ws.close()
    }
    connect()
    return () => {
      closed = true
      if (timerRef.current) clearTimeout(timerRef.current)
      wsRef.current?.close()
    }
  }, [])

  return connected
}

/** 🔔 کانال شخصی بازیکن /ws/game/ — اعلان‌های نبرد/ناوگان (اگر جایی دیگر لازم شد) */
export function usePlayerSocket(onNotify?: (p: { kind: string; title: string; body: string }) => void) {
  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) return
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.host}${API_BASE}/ws/game/?token=${encodeURIComponent(token)}`)
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data)
        if (data.type === 'notification' && data.payload) onNotify?.(data.payload)
      } catch { /* ignore */ }
    }
    return () => ws.close()
  }, [])
}
