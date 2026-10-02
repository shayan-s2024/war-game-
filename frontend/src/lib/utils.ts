export const fmt = (n: number | null | undefined): string =>
  n == null ? '۰' : n.toLocaleString('fa-IR')

export const fmtEn = (n: number): string => n.toLocaleString('en-US')

export const CATEGORY_LABELS: Record<string, string> = {
  mine: '⛏️ معادن',
  economic: '🏢 شرکت‌ها',
  defense: '🛡️ پدافندها',
  tank: '⚙️ تانک‌ها',
  fighter: '✈️ جنگنده‌ها',
  helicopter: '🚁 بالگردها',
  missile: '🚀 موشک‌ها',
  drone: '🛸 پهپادها',
  naval: '🚢 ناوها',
  submarine: '🐋 زیردریایی‌ها',
  carrier: '🛳️ ناو هواپیمابر',
  ground: '🥷 نیروی زمینی',
  artillery: '💥 توپخانه',
  hacker: '💻 هکرها',
  bomb: '💣 بمب‌ها',
  pilot: '👨‍✈️ خلبان‌ها',
  building: '🏗️ ساختمان‌ها',
}

export const CONTINENT_LABELS: Record<string, string> = {
  asia: 'آسیا',
  europe: 'اروپا',
  africa: 'آفریقا',
  north_america: 'آمریکای شمالی',
  south_america: 'آمریکای جنوبی',
  oceania: 'اقیانوسیه',
}

export const WEAPON_LABELS: Record<string, string> = {
  tank: '🪖 زمینی (تانک)',
  fighter: '✈️ هوایی (جنگنده)',
  helicopter: '🚁 هوایی (بالگرد)',
  drone: '🛸 پهپادی',
  navy: '🚢 دریایی (ناو)',
  submarine: '🐋 دریایی (زیردریایی)',
  missile: '🚀 موشکی',
}

export const HACKER_LABELS: Record<string, string> = {
  weak: '🟡 هکر ضعیف',
  medium: '🟠 هکر متوسط',
  strong: '🔴 هکر قوی',
  elite: '🟣 هکر نخبه',
}

export const ASSESS_METHODS = [
  { key: 'drone', label: '🛸 پهپاد', success: 60 },
  { key: 'fighter', label: '✈️ جنگنده', success: 75 },
  { key: 'commando', label: '🥷 کماندو', success: 50 },
]

export function timeAgo(iso: string): string {
  const d = new Date(iso)
  const diff = (Date.now() - d.getTime()) / 1000
  if (diff < 60) return 'لحظاتی پیش'
  if (diff < 3600) return `${Math.floor(diff / 60)} دقیقه پیش`
  if (diff < 86400) return `${Math.floor(diff / 3600)} ساعت پیش`
  return d.toLocaleDateString('fa-IR')
}
