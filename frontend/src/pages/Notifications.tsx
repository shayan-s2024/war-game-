import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { timeAgo } from '../lib/utils'
import { useGameStore } from '../store/gameStore'
import type { NotificationItem } from '../lib/types'

const KIND_ICONS: Record<string, string> = {
  battle: '⚔️', bomb: '💣', hack: '💻', assassination: '🗡️', union: '🤝',
  base: '🏕️', virus: '🦠', reward: '🎁', war: '🔥', system: '📌',
  payment: '💳', sanction: '🌐',
}

export default function NotificationsPage() {
  const { fetchNotifications } = useGameStore()
  const [items, setItems] = useState<NotificationItem[]>([])

  useEffect(() => {
    api.get('/notifications/').then(({ data }) => setItems(data.notifications))
    api.post('/notifications/').then(() => fetchNotifications())
  }, [])

  return (
    <div className="space-y-3">
      <div className="glass-card p-4">
        <h1 className="section-title text-xl">🔔 اعلان‌ها</h1>
      </div>
      {items.length === 0 && <p className="text-slate-500 text-sm text-center py-8">اعلانی ندارید.</p>}
      {items.map((n) => (
        <div key={n.id} className={`glass-card p-4 flex gap-3 ${!n.is_read ? '!border-primary-500/40' : ''}`}>
          <span className="text-2xl shrink-0">{KIND_ICONS[n.kind] || '📌'}</span>
          <div className="min-w-0">
            <div className="font-bold text-sm">{n.title}</div>
            <p className="text-slate-300 text-sm whitespace-pre-wrap mt-0.5">{n.body}</p>
            <span className="text-xs text-slate-600 mt-1 block">{timeAgo(n.created_at)}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
