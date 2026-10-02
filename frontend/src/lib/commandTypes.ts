// ==================== تایپ‌های Command Center / Diplomacy (از API واقعی) ====================
export interface AlertW {
  id: number; type: string; severity: 'critical' | 'warning' | 'info'; priority: number
  title: string; description: string; cause: string; recommended_action: string
  meta: Record<string, unknown>; status: string; akey: string
  created_at: string; updated_at: string
}
export interface AgreementW {
  id: number; type: 'non_aggression' | 'alliance' | 'transit' | 'trade'; type_fa: string
  other: string; emoji: string; deliveries?: number; terms: Record<string, unknown>
  ends_at: string | null
}
export interface ProposalW {
  id: number; type: AgreementW['type']; type_fa: string
  from?: string; to?: string; emoji: string
  terms: Record<string, unknown>; expires_at: string
  ai_review?: Record<string, unknown>
}
export interface RelationW {
  country: string; emoji: string; score: number; trust: number; tension: number
  agreements: { id: number; type: string; type_fa: string; ends_at: string | null }[]
}
export interface CcStats {
  treasury: number; population: number; score: number; daily_profit: number
  income: { mines: number; economic: number; total: number }
  assets: { mines: Record<string, number>; economic: Record<string, number>; buildings: Record<string, number> }
  army: { attack: number; defense: number; categories: Record<string, { count: number; quality: number }>; ready_fighters: number; ready_helicopters: number }
  bases: { id: number; country: string; ready: boolean; ground: number; air: number }[]
  fleets: { outbound: number; returning: number }
  status: { viruses: string[]; sanction: { active: boolean; penalty: number; until: string | null }; on_fire: boolean }
  recent_battles: string[]
  notifications: { title: string; kind: string; at: string }[]
  combat_ready: boolean
}
export interface CommandCenterW {
  country: { name: string | null; emoji: string }
  treasury: { current: number; income: number; recent_flow: number }
  stats: CcStats
  alerts: AlertW[]
  agreements: AgreementW[]
  incoming_proposals: ProposalW[]
  relations: RelationW[]
}

export const ALERT_TYPE_FA: Record<string, string> = {
  resource_shortage: 'کمبود منابع', treasury_low: 'خزانه کم', supply_disruption: 'اختلال تأمین',
  equipment_shortage: 'کمبود تجهیزات', military_readiness: 'آمادگی نظامی',
  production_failure: 'شکست تولید', diplomatic_change: 'تغییر دیپلماتیک',
  trade_disruption: 'اختلال تجارت', infrastructure_capacity: 'ظرفیت زیرساخت', construction_delay: 'تأخیر ساخت',
}
export const AG_TYPE_FA: Record<string, string> = {
  non_aggression: '🕊 پیمان عدم تجاوز', alliance: '🤝 اتحاد نظامی',
  transit: '🚚 ترانزیت', trade: '💱 تجاری',
}
export const SEV_FA: Record<string, string> = { critical: 'بحرانی', warning: 'هشدار', info: 'اطلاع' }
