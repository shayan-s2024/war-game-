import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import App from './App'

import './index.css'

const miniApp = window.Telegram?.WebApp
if (miniApp) {
  miniApp.ready?.()
  miniApp.expand?.()
  miniApp.setHeaderColor?.('#050b12')
  miniApp.setBackgroundColor?.('#050b12')
  document.documentElement.dataset.telegramMiniApp = 'true'
  document.documentElement.classList.add('telegram-mini-app')
  const applySafeArea = () => {
    const inset = miniApp.safeAreaInset
    const contentInset = miniApp.contentSafeAreaInset
    document.documentElement.style.setProperty('--app-safe-top', `${Math.max(inset?.top || 0, contentInset?.top || 0)}px`)
    document.documentElement.style.setProperty('--app-safe-bottom', `${Math.max(inset?.bottom || 0, contentInset?.bottom || 0)}px`)
    document.documentElement.style.setProperty('--app-safe-left', `${Math.max(inset?.left || 0, contentInset?.left || 0)}px`)
    document.documentElement.style.setProperty('--app-safe-right', `${Math.max(inset?.right || 0, contentInset?.right || 0)}px`)
  }
  applySafeArea()
  miniApp.onEvent?.('safeAreaChanged', applySafeArea)
  miniApp.onEvent?.('contentSafeAreaChanged', applySafeArea)
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="top-center"
        toastOptions={{
          style: {
            background: '#0f172a',
            color: '#e2e8f0',
            border: '1px solid rgba(255,255,255,0.1)',
            fontFamily: 'Vazirmatn, sans-serif',
          },
        }}
      />
    </BrowserRouter>
  </React.StrictMode>,
)
