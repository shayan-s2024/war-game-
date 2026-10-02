import { create } from 'zustand'
import toast from 'react-hot-toast'
import { api } from '../lib/api'
import type { DashboardData, NotificationItem } from '../lib/types'

interface GameState {
  // auth
  isLoggedIn: boolean
  // dashboard
  dashboard: DashboardData | null
  loadingDashboard: boolean
  // notifications
  notifications: NotificationItem[]
  unreadCount: number
  wsConnected: boolean
  // actions
  login: (username: string, password: string) => Promise<void>
  register: (username: string, password: string, ref?: string) => Promise<void>
  telegramLogin: (data: Record<string, string>) => Promise<void>
  logout: () => void
  fetchDashboard: () => Promise<void>
  fetchNotifications: () => Promise<void>
  connectWs: () => void
}

let ws: WebSocket | null = null
let wsReconnectTimer: ReturnType<typeof setTimeout> | null = null

export const useGameStore = create<GameState>((set, get) => ({
  isLoggedIn: !!localStorage.getItem('access_token'),
  dashboard: null,
  loadingDashboard: false,
  notifications: [],
  unreadCount: 0,
  wsConnected: false,

  login: async (username, password) => {
    const { data } = await api.post('/auth/login/', { username, password })
    localStorage.setItem('access_token', data.tokens.access)
    localStorage.setItem('refresh_token', data.tokens.refresh)
    set({ isLoggedIn: true })
    get().fetchDashboard()
    get().connectWs()
  },

  register: async (username, password, ref) => {
    const { data } = await api.post('/auth/register/', { username, password, ref })
    localStorage.setItem('access_token', data.tokens.access)
    localStorage.setItem('refresh_token', data.tokens.refresh)
    set({ isLoggedIn: true })
  },

  telegramLogin: async (tgData) => {
    const { data } = await api.post('/auth/telegram/', tgData)
    localStorage.setItem('access_token', data.tokens.access)
    localStorage.setItem('refresh_token', data.tokens.refresh)
    set({ isLoggedIn: true })
    get().fetchDashboard()
    get().connectWs()
  },

  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    ws?.close()
    ws = null
    set({ isLoggedIn: false, dashboard: null, notifications: [], unreadCount: 0 })
  },

  fetchDashboard: async () => {
    set({ loadingDashboard: true })
    try {
      const { data } = await api.get('/dashboard/')
      set({ dashboard: data, loadingDashboard: false })
    } catch {
      set({ loadingDashboard: false })
    }
  },

  fetchNotifications: async () => {
    try {
      const { data } = await api.get('/notifications/')
      set({ notifications: data.notifications, unreadCount: data.unread_count })
    } catch {
      /* silent */
    }
  },

  connectWs: () => {
    if (ws) return
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = import.meta.env.VITE_WS_HOST || window.location.host
    const token = localStorage.getItem('access_token') || ''
    ws = new WebSocket(`${proto}://${host}/ws/game/?token=${encodeURIComponent(token)}`)
    ws.onopen = () => set({ wsConnected: true })
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      if (msg.type === 'notification') {
        const p = msg.payload
        toast(p.title, { icon: p.kind === 'battle' ? '⚔️' : '🔔' })
        set((s) => ({
          notifications: [{ id: Date.now(), kind: p.kind, title: p.title, body: p.body, is_read: false, created_at: new Date().toISOString() }, ...s.notifications],
          unreadCount: s.unreadCount + 1,
        }))
        get().fetchDashboard()
      }
    }
    ws.onclose = () => {
      set({ wsConnected: false })
      ws = null
      // auto-reconnect
      if (wsReconnectTimer) clearTimeout(wsReconnectTimer)
      wsReconnectTimer = setTimeout(() => {
        if (get().isLoggedIn) get().connectWs()
      }, 5000)
    }
    ws.onerror = () => ws?.close()
  },
}))
