import { useEffect } from 'react'
import { Navigate, NavLink, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { useGameStore } from './store/gameStore'
import { fmt } from './lib/utils'
import Login from './pages/Login'
import Onboarding from './pages/Onboarding'
import Dashboard from './pages/Dashboard'
import WorldMap from './pages/WorldMap'
import MyCountry from './pages/MyCountry'
import Fleet from './pages/Fleet'
import ShopPage from './pages/Shop'
import AttackPage from './pages/Attack'
import SpyPage from './pages/Spy'
import UnionsPage from './pages/Unions'
import BasesPage from './pages/Bases'
import SocialPage from './pages/Social'
import LeaderboardPage from './pages/Leaderboard'
import GuidePage from './pages/Guide'
import Equipment from './pages/Equipment'
import AchievementsPage from './pages/Achievements'
import PlayerProfile from './pages/PlayerProfile'
import AdminPage from './pages/Admin'
import NotificationsPage from './pages/Notifications'
import CommandCenter from './pages/CommandCenter'
import DiplomacyPage from './pages/Diplomacy'

function ResourcesHUD() {
  const { dashboard } = useGameStore()
  if (!dashboard?.player) return null
  const p = dashboard.player
  return (
    <div className="sticky top-0 z-40 resource-rail glass-card !rounded-none border-x-0 border-t-0 px-3 py-2">
      <div className="max-w-7xl mx-auto flex items-center gap-2 overflow-x-auto text-sm">
        <span className="stat-chip shrink-0">💰 <b className="resource-value">{fmt(p.credit)}</b></span>
        <span className="stat-chip shrink-0">🛡 <b className="resource-value">{fmt(p.defense)}</b></span>
        <span className="stat-chip shrink-0">💥 <b className="resource-value">{fmt(p.attack_power)}</b></span>
        <span className="stat-chip shrink-0">📈 <b className="resource-value">{fmt(p.daily_profit)}</b></span>
        <span className="stat-chip shrink-0">👥 <b className="resource-value">{fmt(p.population)}</b></span>
        <span className="stat-chip shrink-0">🏆 <b className="resource-value">{fmt(p.score)}</b></span>
        <span className="stat-chip shrink-0 mr-auto">
          {dashboard.war_active
            ? <span className="text-danger-400 font-black">⚔️ جنگ فعال</span>
            : <span className="text-slate-400">🕊️ صلح</span>}
        </span>
      </div>
    </div>
  )
}

const NAV = [
  { to: '/', label: 'داشبورد', icon: '🏛️' },
  { to: '/command-center', label: 'مرکز فرماندهی', icon: '🚨' },
  { to: '/diplomacy', label: 'دیپلماسی', icon: '🕊️' },
  { to: '/map', label: 'نقشه جهانی', icon: '🌍' },
  { to: '/my-country', label: 'کشور من', icon: '🗺️' },
  { to: '/fleet', label: 'ناوگان', icon: '⚓' },
  { to: '/shop', label: 'فروشگاه', icon: '🛒' },
  { to: '/equipment', label: 'تجهیزات', icon: '📦' },
  { to: '/attack', label: 'حمله', icon: '⚔️' },
  { to: '/spy', label: 'جاسوسی', icon: '🕵️' },
  { to: '/unions', label: 'اتحاد', icon: '🤝' },
  { to: '/bases', label: 'پایگاه‌ها', icon: '🏕️' },
  { to: '/social', label: 'بیانیه‌ها', icon: '📢' },
  { to: '/leaderboard', label: 'رتبه‌بندی', icon: '🏆' },
  { to: '/achievements', label: 'دستاوردها', icon: '🎖️' },
  { to: '/guide', label: 'راهنما', icon: '📖' },
]

const MOBILE_NAV = [
  { to: '/', label: '\u062e\u0627\u0646\u0647', icon: '???' },
  { to: '/map', label: '\u0646\u0642\u0634\u0647', icon: '??' },
  { to: '/my-country', label: '\u06a9\u0634\u0648\u0631 \u0645\u0646', icon: '\u{1F5FA}\uFE0F' },
  { to: '/attack', label: '\u062d\u0645\u0644\u0647', icon: '??' },
  { to: '/more', label: '\u0628\u06cc\u0634\u062a\u0631', icon: '?' },
]

function Sidebar() {
  const { dashboard, unreadCount, logout } = useGameStore()
  const isAdmin = !!dashboard
  return (
    <aside className="hidden lg:flex flex-col w-60 shrink-0 h-screen sticky top-0 glass-card sidebar-depth !rounded-none border-l-0 border-t-0 border-b-0 p-4 gap-1">
      <div className="text-2xl font-black mb-6 flex items-center gap-2">
        <span className="brand-orb" aria-hidden="true"><span /></span>
        <span className="bg-gradient-to-l from-primary-300 to-gold-300 bg-clip-text text-transparent">جنگ جهانی</span>
      </div>
      {NAV.map((n) => (
        <NavLink
          key={n.to}
          to={n.to}
          className={({ isActive }) =>
            `flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all ${
              isActive
                ? 'bg-primary-500/15 text-primary-300 font-bold border border-primary-500/30'
                : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
            }`
          }
        >
          <span className="text-xl">{n.icon}</span> {n.label}
        </NavLink>
      ))}
      <NavLink to="/notifications" className="relative flex items-center gap-3 px-4 py-2.5 rounded-xl text-slate-400 hover:bg-white/5">
        <span className="text-xl">🔔</span> اعلان‌ها
        {unreadCount > 0 && (
          <span className="absolute left-3 bg-danger-500 text-white text-xs rounded-full px-2 py-0.5">{unreadCount}</span>
        )}
      </NavLink>
      {dashboard?.player && (
        <div className="mt-auto glass-card p-3 text-sm">
          <div className="font-bold">{dashboard.player.emoji} {dashboard.player.name}</div>
          <div className="text-slate-400 text-xs">{dashboard.player.country}</div>
          <button onClick={logout} className="btn-ghost w-full mt-3 !py-1.5 text-xs">خروج</button>
        </div>
      )}
    </aside>
  )
}

function BottomNav() {
  return (
    <nav className="lg:hidden fixed bottom-0 inset-x-0 z-40 glass-card !rounded-none border-x-0 border-b-0 flex justify-around py-2">
      {MOBILE_NAV.map((n) => (
        <NavLink
          key={n.to}
          to={n.to}
          className={({ isActive }) =>
            `flex flex-col items-center gap-0.5 px-3 py-1 rounded-lg text-xs ${
              isActive ? 'text-primary-300 font-bold' : 'text-slate-500'
            }`
          }
        >
          <span className="text-xl">{n.icon}</span>
          {n.label}
        </NavLink>
      ))}
    </nav>
  )
}

function GameLayout() {
  const { dashboard, loadingDashboard, fetchDashboard, fetchNotifications, connectWs, isLoggedIn } = useGameStore()
  useEffect(() => {
    fetchDashboard()
    fetchNotifications()
    connectWs()
  }, [])
  if (!isLoggedIn) return <Navigate to="/login" replace />
  if (loadingDashboard && !dashboard) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center space-y-4">
          <div className="text-6xl animate-float">🌍</div>
          <div className="w-48 h-2 rounded-full overflow-hidden skeleton mx-auto" />
          <p className="text-slate-500 text-sm">در حال ورود به فرماندهی...</p>
        </div>
      </div>
    )
  }
  if (dashboard?.needs_registration) return <Navigate to="/onboarding" replace />
  return (
    <div className="game-shell flex min-h-screen">
      <Sidebar />
      <div className="flex-1 min-w-0 flex flex-col pb-20 lg:pb-0">
        <ResourcesHUD />
        <main className="flex-1 max-w-7xl w-full mx-auto p-4 page-depth">
          <Outlet />
        </main>
      </div>
      <BottomNav />
    </div>
  )
}

function MoreMenu() {
  return (
    <div className="grid grid-cols-2 gap-3">
      {NAV.slice(4).map((n) => (
        <NavLink key={n.to} to={n.to} className="glass-card p-6 flex flex-col items-center gap-2 active:scale-95 transition">
          <span className="text-3xl">{n.icon}</span>
          <span className="font-bold">{n.label}</span>
        </NavLink>
      ))}
      <NavLink to="/notifications" className="glass-card p-6 flex flex-col items-center gap-2 active:scale-95 transition">
        <span className="text-3xl">🔔</span>
        <span className="font-bold">اعلان‌ها</span>
      </NavLink>
      <NavLink to="/admin" className="glass-card p-6 flex flex-col items-center gap-2 active:scale-95 transition">
        <span className="text-3xl">👑</span>
        <span className="font-bold">پنل ادمین</span>
      </NavLink>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/onboarding" element={<Onboarding />} />
      <Route element={<GameLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/map" element={<WorldMap />} />
        <Route path="/my-country" element={<MyCountry />} />
        <Route path="/command-center" element={<CommandCenter />} />
        <Route path="/diplomacy" element={<DiplomacyPage />} />
        <Route path="/fleet" element={<Fleet />} />
        <Route path="/shop" element={<ShopPage />} />
        <Route path="/equipment" element={<Equipment />} />
        <Route path="/achievements" element={<AchievementsPage />} />
        <Route path="/players/:username" element={<PlayerProfile />} />
        <Route path="/attack" element={<AttackPage />} />
        <Route path="/spy" element={<SpyPage />} />
        <Route path="/unions" element={<UnionsPage />} />
        <Route path="/bases" element={<BasesPage />} />
        <Route path="/social" element={<SocialPage />} />
        <Route path="/leaderboard" element={<LeaderboardPage />} />
        <Route path="/guide" element={<GuidePage />} />
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/more" element={<MoreMenu />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
