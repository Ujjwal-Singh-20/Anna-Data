import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import MockupSMS from './App'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <MockupSMS />
  </StrictMode>,
)
