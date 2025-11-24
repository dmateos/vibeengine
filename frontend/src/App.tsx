import { useState, useEffect } from 'react'
import './App.css'
import FlowDiagram from './components/FlowDiagram'
import HomePage from './components/HomePage'

type Page = 'home' | 'flow'

function App() {
  const [darkMode, setDarkMode] = useState<boolean>(() => {
    const saved = localStorage.getItem('darkMode')
    return saved ? JSON.parse(saved) : false
  })

  const [currentPage, setCurrentPage] = useState<Page>('home')

  useEffect(() => {
    localStorage.setItem('darkMode', JSON.stringify(darkMode))
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  const toggleDarkMode = () => {
    setDarkMode(!darkMode)
  }

  const navigateToHome = () => {
    setCurrentPage('home')
  }

  const navigateToFlow = () => {
    setCurrentPage('flow')
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="header-left">
            <h1 style={{ cursor: 'pointer' }} onClick={navigateToHome}>VibeEngine</h1>
            <span className="header-subtitle">
              {currentPage === 'home' ? 'AI-Powered Workflow Engine' : 'Workflow Designer'}
            </span>
          </div>
          <div className="header-right">
            {currentPage === 'flow' && (
              <button className="nav-button" onClick={navigateToHome}>
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M15 12.5l-5 5-5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" transform="rotate(90 10 10)"/>
                </svg>
                Home
              </button>
            )}
            <button className="theme-toggle" onClick={toggleDarkMode} title="Toggle dark mode">
              {darkMode ? '☀️' : '🌙'}
            </button>
          </div>
        </div>
      </header>

      <main className={`main-content ${currentPage === 'flow' ? 'has-workflow' : ''}`}>
        {currentPage === 'home' ? (
          <HomePage onNavigateToFlow={navigateToFlow} />
        ) : (
          <div className="workflow-container">
            <FlowDiagram />
          </div>
        )}
      </main>
    </div>
  )
}

export default App
