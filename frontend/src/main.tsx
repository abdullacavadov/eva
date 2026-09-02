import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { SettingsHost } from './components/SettingsPage'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
    <SettingsHost />
  </StrictMode>,
)
