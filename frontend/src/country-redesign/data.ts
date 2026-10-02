// Game data shapes (mirroring the original "My Country" API contract) + local demo data.

export type DivisionKind = 'capital' | 'province' | 'city'

export interface Division {
  id: string
  name: string
  kind: DivisionKind
  x: number
  z: number
  radius: number
  population: number
  custom?: boolean
}

export type ItemKey = 'radar' | 'sam' | 'airbase' | 'armor' | 'artillery' | 'silo'

export interface InvItem {
  key: ItemKey
  name: string
  icon: string
  qty: number
  desc: string
  footprint: number
}

export interface Placement {
  id: number
  item_key: ItemKey
  qty: number
  x: number
  z: number
  city_name?: string
}

export type BiomeId = 'temperate' | 'arid' | 'nordic'

export interface BiomePreset {
  id: BiomeId
  label: string
  desc: string
  mountainAmp: number
  mountainCover: number
  plainAmp: number
  moistureBias: number
  forest: number
  scrub: number
  snowLine: number
  treeLine: number
  coniferRatio: number
  palette: {
    grassA: string
    grassB: string
    dry: string
    forestFloor: string
    rockA: string
    rockB: string
    sand: string
    snow: string
  }
}

export const BIOMES: Record<BiomeId, BiomePreset> = {
  temperate: {
    id: 'temperate',
    label: 'معتدل و سرسبز',
    desc: 'جنگل‌های انبوه، دشت‌های سبز و قله‌های برفی',
    mountainAmp: 1,
    mountainCover: 0.5,
    plainAmp: 1,
    moistureBias: 0.08,
    forest: 1,
    scrub: 0.15,
    snowLine: 19,
    treeLine: 17,
    coniferRatio: 0.35,
    palette: {
      grassA: '#5b7d36',
      grassB: '#7d9548',
      dry: '#9b9158',
      forestFloor: '#2d4824',
      rockA: '#6c675f',
      rockB: '#8c867a',
      sand: '#cdbd93',
      snow: '#f3f7fb',
    },
  },
  arid: {
    id: 'arid',
    label: 'فلات خشک',
    desc: 'فلات مرتفع، بیابان‌های سنگی و رشته‌کوه‌های خشک',
    mountainAmp: 1.1,
    mountainCover: 0.58,
    plainAmp: 0.8,
    moistureBias: -0.3,
    forest: 0.25,
    scrub: 1,
    snowLine: 29,
    treeLine: 14,
    coniferRatio: 0.15,
    palette: {
      grassA: '#8b8a52',
      grassB: '#a59c5f',
      dry: '#bda774',
      forestFloor: '#6c6f3e',
      rockA: '#8b6e55',
      rockB: '#ad8d6b',
      sand: '#dcc698',
      snow: '#eef0f2',
    },
  },
  nordic: {
    id: 'nordic',
    label: 'شمالگان کوهستانی',
    desc: 'سوزنی‌برگان تیره، فیوردها و برف همیشگی',
    mountainAmp: 1.25,
    mountainCover: 0.55,
    plainAmp: 0.9,
    moistureBias: 0.15,
    forest: 1,
    scrub: 0.1,
    snowLine: 12,
    treeLine: 11,
    coniferRatio: 0.92,
    palette: {
      grassA: '#4a6844',
      grassB: '#617a4f',
      dry: '#7d7b5b',
      forestFloor: '#22382a',
      rockA: '#5a5e63',
      rockB: '#7b8085',
      sand: '#b9b5a2',
      snow: '#f5f9fc',
    },
  },
}

export const INVENTORY: InvItem[] = [
  { key: 'radar', name: 'رادار دوربرد', icon: '📡', qty: 3, desc: 'دیده‌بانی هوایی تا ۴۰۰ کیلومتر', footprint: 6 },
  { key: 'sam', name: 'پدافند هوایی', icon: '🚀', qty: 4, desc: 'آتشبار موشکی زمین به هوا', footprint: 7 },
  { key: 'airbase', name: 'پایگاه هوایی', icon: '✈️', qty: 2, desc: 'باند، آشیانه و برج مراقبت', footprint: 17 },
  { key: 'armor', name: 'یگان زرهی', icon: '🛡️', qty: 3, desc: 'گردان تانک و نفربر', footprint: 8 },
  { key: 'artillery', name: 'توپخانه', icon: '💥', qty: 3, desc: 'آتشبار هویتزر خودکششی', footprint: 7 },
  { key: 'silo', name: 'سیلوی موشکی', icon: '☢️', qty: 1, desc: 'سیلوی زیرزمینی موشک بالستیک', footprint: 6 },
]

export const ITEM_BY_KEY = Object.fromEntries(INVENTORY.map((i) => [i.key, i])) as Record<ItemKey, InvItem>

export const GOVS = ['جمهوری', 'پادشاهی', 'امارات', 'فدراسیون', 'جمهوری خلق', 'دولت شهری']

export const PROVINCE_NAMES = ['البرزکوه', 'دریابار', 'سبزدشت', 'سنگ‌آباد', 'نیلگون', 'کوهپایه', 'خزرآباد', 'مهرگان']
export const CITY_NAMES = ['آبشار', 'گلبرگ', 'ساحل‌شهر', 'باغ‌سار', 'رودبار', 'سروستان', 'دشت‌آرا', 'پیروزی', 'نسیم', 'آفتاب']

export interface CountryProfile {
  display_name: string
  flag_emoji: string
  map_color: string
  capital_name: string
  government: string
  biome: BiomeId
  seed: number
}

export const DEFAULT_PROFILE: CountryProfile = {
  display_name: 'جمهوری آریانا',
  flag_emoji: '🇮🇷',
  map_color: '#55d6ff',
  capital_name: 'آریان‌شهر',
  government: 'جمهوری',
  biome: 'temperate',
  seed: 1403,
}

export interface Stats {
  treasury: number
  population: number
  score: number
  daily_profit: number
  income: { mines: number; economic: number; total: number }
  assets: {
    mines: Record<string, number>
    economic: Record<string, number>
    buildings: Record<string, number>
  }
  army: {
    attack: number
    defense: number
    categories: Record<string, { count: number; quality: number }>
    ready_fighters: number
    ready_helicopters: number
  }
  bases: { id: number; country: string; ready: boolean; ground: number; air: number }[]
  fleets: { outbound: number; returning: number }
  status: {
    viruses: string[]
    sanction: { active: boolean; penalty: number; until: string | null }
    on_fire: boolean
  }
  recent_battles: string[]
  notifications: { title: string; kind: string; at: string }[]
  combat_ready: boolean
}

export const DEMO_STATS: Stats = {
  treasury: 48_250_000,
  population: 31_400_000,
  score: 18_920,
  daily_profit: 1_240_000,
  income: { mines: 620_000, economic: 620_000, total: 1_240_000 },
  assets: {
    mines: { 'معدن آهن': 4, 'معدن مس': 3, 'میدان نفتی': 2 },
    economic: { 'بندر تجاری': 2, 'کارخانه فولاد': 3, 'نیروگاه': 4 },
    buildings: { 'مرکز فرماندهی': 1, 'دانشگاه': 5, 'بیمارستان': 9 },
  },
  army: {
    attack: 8420,
    defense: 9650,
    categories: {
      'نیروی زمینی': { count: 1850, quality: 74 },
      'نیروی هوایی': { count: 312, quality: 81 },
      'نیروی دریایی': { count: 96, quality: 62 },
      'پدافند': { count: 140, quality: 88 },
      'موشکی': { count: 54, quality: 69 },
    },
    ready_fighters: 118,
    ready_helicopters: 46,
  },
  bases: [
    { id: 1, country: 'پایگاه شمال', ready: true, ground: 420, air: 36 },
    { id: 2, country: 'پایگاه ساحلی', ready: true, ground: 310, air: 22 },
    { id: 3, country: 'پایگاه مرزی شرق', ready: false, ground: 180, air: 0 },
  ],
  fleets: { outbound: 1, returning: 0 },
  status: {
    viruses: [],
    sanction: { active: false, penalty: 0, until: null },
    on_fire: false,
  },
  recent_battles: ['دفاع موفق در برابر یورش هوایی — پیروزی', 'عملیات شناسایی مرز شرقی — پایان', 'رزمایش دریایی — در حال اجرا'],
  notifications: [
    { title: 'گزارش روزانه درآمد ثبت شد', kind: 'economy', at: 'امروز ۰۸:۰۰' },
    { title: 'رادار دوربرد در حالت آماده‌باش', kind: 'army', at: 'دیروز ۲۲:۱۰' },
    { title: 'پیشنهاد اتحاد از یک کشور همسایه', kind: 'diplomacy', at: 'دیروز ۱۴:۳۰' },
  ],
  combat_ready: true,
}
