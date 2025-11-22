import { useState, useEffect } from 'react'
import './App.css'
import FlowDiagram from './components/FlowDiagram'

function App() {
  const [darkMode, setDarkMode] = useState<boolean>(() => {
    const saved = localStorage.getItem('darkMode')
    return saved ? JSON.parse(saved) : false
  })

  useEffect(() => {
    localStorage.setItem('darkMode', JSON.stringify(darkMode))
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  const toggleDarkMode = () => {
    setDarkMode(!darkMode)
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="header-left">
            <h1>VibeEngine</h1>
            <span className="header-subtitle">Workflow Designer</span>
          </div>
          <button className="theme-toggle" onClick={toggleDarkMode} title="Toggle dark mode">
            {darkMode ? '☀️' : '🌙'}
          </button>
        </div>
      </header>

      <main className="main-content">
        <div className="workflow-container">
          <FlowDiagram />
        </div>
      </main>
    </div>
  )
}

export default App
