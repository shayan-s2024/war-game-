import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api, errMsg } from '../lib/api'
import { timeAgo } from '../lib/utils'
import type { StatementItem } from '../lib/types'

export default function SocialPage() {
  const [statements, setStatements] = useState<StatementItem[]>([])
  const [text, setText] = useState('')
  const [kind, setKind] = useState<'statement' | 'tweet'>('statement')
  const [busy, setBusy] = useState(false)
  const [remaining, setRemaining] = useState<number | null>(null)

  const load = () => api.get('/statements/').then(({ data }) => setStatements(data.statements))
  useEffect(() => { load() }, [])

  const post = async () => {
    if (!text.trim()) return
    setBusy(true)
    try {
      const { data: res } = await api.post('/statements/', { text, kind })
      if (res.ok) {
        toast.success(kind === 'statement' ? '📢 بیانیه منتشر شد' : '🐦 توییت ارسال شد')
        setText('')
        setRemaining(res.remaining)
        load()
      }
    } catch (e) { toast.error(errMsg(e)) } finally { setBusy(false) }
  }

  return (
    <div className="space-y-4">
      <div className="glass-card p-4">
        <h1 className="section-title text-xl">📢 بیانیه‌ها و توییت‌ها</h1>
        <p className="text-slate-400 text-sm mt-1">
          بیانیه: {remaining == null ? '۴' : remaining} باقی‌مانده در ۲۴ ساعت | توییت: بدون محدودیت
        </p>
      </div>

      <div className="glass-card p-4 space-y-3">
        <div className="flex gap-2">
          {([['statement', '📝 بیانیه'], ['tweet', '🐦 توییت']] as const).map(([k, label]) => (
            <button key={k} onClick={() => setKind(k)}
              className={`px-4 py-1.5 rounded-lg text-sm transition ${kind === k ? 'bg-primary-500/20 text-primary-300' : 'bg-white/5 text-slate-400'}`}>
              {label}
            </button>
          ))}
        </div>
        <textarea className="input-dark min-h-24" placeholder="متن را بنویسید..." value={text} maxLength={500}
          onChange={(e) => setText(e.target.value)} />
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-500">{text.length}/500</span>
          <button className="btn-primary" onClick={post} disabled={busy || !text.trim()}>انتشار</button>
        </div>
      </div>

      <div className="space-y-2">
        {statements.map((s) => (
          <div key={s.id} className="glass-card p-4">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-lg">{s.kind === 'tweet' ? '🐦' : '📢'}</span>
              <Link to={`/players/${s.username}`} className="font-bold text-sm hover:text-primary-300">{s.player_name}</Link>
              <span className="text-xs text-slate-500">{s.country}</span>
              <span className="text-xs text-slate-600 mr-auto">{timeAgo(s.created_at)}</span>
            </div>
            <p className="text-slate-200 text-sm whitespace-pre-wrap">{s.text}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
