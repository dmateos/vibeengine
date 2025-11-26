import { useState, useEffect } from 'react'
import './App.css'
import FlowDiagram from './components/FlowDiagram'
import HomePage from './components/HomePage'
import Login from './components/Login'
import Signup from './components/Signup'
import { useAuth } from './contexts/AuthContext'

type Page = 'home' | 'flow' | 'login' | 'signup'

function App() {
  const { user, logout, isAuthenticated } = useAuth()

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
    if (!isAuthenticated) {
      navigateToLogin()
      return
    }
    setCurrentPage('flow')
  }

  const navigateToLogin = () => {
    setCurrentPage('login')
  }

  const navigateToSignup = () => {
    setCurrentPage('signup')
  }

  const handleLogout = () => {
    logout()
    navigateToHome()
  }

  const handleAuthSuccess = () => {
    navigateToHome()
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
            {isAuthenticated ? (
              <>
                <span style={{ color: 'var(--text-secondary)', marginRight: '1rem', fontSize: '0.9rem' }}>
                  {user?.username}
                </span>
                <button className="nav-button" onClick={handleLogout}>
                  Logout
                </button>
              </>
            ) : (
              currentPage !== 'login' && currentPage !== 'signup' && (
                <>
                  <button className="nav-button" onClick={navigateToLogin}>
                    Login
                  </button>
                  <button className="nav-button" onClick={navigateToSignup}>
                    Sign Up
                  </button>
                </>
              )
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
        ) : currentPage === 'flow' ? (
          isAuthenticated ? (
            <div className="workflow-container">
              <FlowDiagram />
            </div>
          ) : (
            <Login onSwitchToSignup={navigateToSignup} onSuccess={() => { handleAuthSuccess(); navigateToFlow(); }} />
          )
        ) : currentPage === 'login' ? (
          <Login onSwitchToSignup={navigateToSignup} onSuccess={handleAuthSuccess} />
        ) : currentPage === 'signup' ? (
          <Signup onSwitchToLogin={navigateToLogin} onSuccess={handleAuthSuccess} />
        ) : null}
      </main>
    </div>
  )
}

export default App
