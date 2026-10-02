export interface PlayerState {
  id: number
  name: string
  country: string | null
  emoji: string
  continent: string | null
  credit: number
  defense: number
  attack_power: number
  daily_profit: number
  score: number
  population: number
  invite_count: number
  on_fire: boolean
  viruses: Record<string, { remaining_days: number; daily_loss: number }>
}

export interface DashboardData {
  needs_registration?: boolean
  player?: PlayerState
  cabinet: Record<string, string>
  cabinet_complete: boolean
  war_active: boolean
  attacks_remaining: number
  attack_limit: number
  sanctioned: boolean
  next_step?: 'country' | 'cabinet' | null
}

export interface ShopItem {
  key: string
  name: string
  icon: string
  base_price: number
  price: number
  sanctioned: boolean
  count: number
  q?: number
  power?: number
  cap?: number
  daily_profit?: number
  description?: string
  abilities?: string[]
  fighters?: string[]
  capacity?: number
}

export interface PlayerSummary {
  id: number
  player_name: string
  username?: string
  country: string | null
  continent: string | null
  score: number
  credit: number
  defense: number
  attack_power: number
  daily_profit: number
  population: number
}

export interface TargetPlayer {
  id: number
  name: string
  country: string | null
  emoji: string
  score: number
  defense: number
  continent: string | null
}

export interface CountryInfo {
  name: string
  command_name?: string
  emoji: string
  population: number
  taken: boolean
  lat: number | null
  lon: number | null
  continent?: string | null
  imaginary?: boolean
}

export interface ContinentInfo {
  key: string
  name: string
  flag: string
  lat: number
  lon: number
}

export interface NotificationItem {
  id: number
  kind: string
  title: string
  body: string
  is_read: boolean
  created_at: string
}

export interface UnionInfo {
  id: number
  name: string
  union_id: string
  owner_id: number
  owner_name: string
  level: number
  treasury: number
  members_count: number
  capacity: number
  donation_limit: number
  members: { id: number; name: string; country: string | null; score: number; daily_profit: number }[]
  is_owner: boolean
  is_member: boolean
}

export interface BaseInfo {
  id: number
  country: string
  country_emoji: string
  continent: string
  owner_name: string
  built_at: string
  ready_at: string
  is_ready: boolean
}

export interface BattleLogItem {
  id: number
  ts: string
  text: string
}

export interface GlobalEventItem {
  id: number
  attacker: string
  defender: string
  summary: string
  created_at: string
}

export interface StatementItem {
  id: number
  kind: 'statement' | 'tweet'
  text: string
  likes: number
  created_at: string
  player_name: string
  country: string | null
  username?: string
}

export interface IntelItem {
  target_id: number
  target_name: string
  member_key: string
  position: string
  icon: string
  member: string
  code: string
}
