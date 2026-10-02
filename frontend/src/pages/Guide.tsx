import { useEffect, useState } from 'react'
import { api } from '../lib/api'

interface GuideSection {
  key: string
  title: string
  content: string
}

export default function GuidePage() {
  const [sections, setSections] = useState<GuideSection[]>([])
  const [open, setOpen] = useState<string | null>(null)

  useEffect(() => {
    api.get('/guide/').then(({ data }) => setSections(data.sections))
  }, [])

  return (
    <div className="space-y-3">
      <div className="glass-card p-4">
        <h1 className="section-title text-xl">📖 راهنمای بازی — از صفر تا صد</h1>
      </div>
      {sections.map((s) => (
        <div key={s.key} className="glass-card overflow-hidden">
          <button className="w-full text-right px-4 py-3 font-bold flex items-center justify-between hover:bg-white/5 transition"
            onClick={() => setOpen(open === s.key ? null : s.key)}>
            {s.title}
            <span className={`transition-transform ${open === s.key ? 'rotate-180' : ''}`}>▾</span>
          </button>
          {open === s.key && (
            <div className="px-4 pb-4 text-slate-300 text-sm leading-7 whitespace-pre-wrap">{s.content}</div>
          )}
        </div>
      ))}
    </div>
  )
}
