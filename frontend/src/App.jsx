import { useState, useEffect } from 'react'
import './App.css'

const API_BASE_URL = 'http://localhost:8000/api'

function App() {
  const [message, setMessage] = useState(null)
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch hello message
      const helloResponse = await fetch(`${API_BASE_URL}/hello/`)
      const helloData = await helloResponse.json()
      setMessage(helloData)

      // Fetch items
      const itemsResponse = await fetch(`${API_BASE_URL}/items/`)
      const itemsData = await itemsResponse.json()
      setItems(itemsData.items)

      setLoading(false)
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Django + React App</h1>
        <p className="subtitle">Full-stack application with Django backend and React frontend</p>
      </header>

      <main className="main-content">
        {loading && <div className="loading">Loading...</div>}

        {error && (
          <div className="error">
            <h3>Error connecting to backend</h3>
            <p>{error}</p>
            <p className="hint">Make sure the Django server is running on http://localhost:8000</p>
            <button onClick={fetchData} className="retry-btn">Retry</button>
          </div>
        )}

        {!loading && !error && (
          <>
            <section className="status-section">
              <h2>Backend Status</h2>
              {message && (
                <div className="status-card">
                  <p className="status-message">{message.message}</p>
                  <p className="timestamp">
                    Last updated: {new Date(message.timestamp).toLocaleString()}
                  </p>
                  <span className={`badge ${message.status}`}>{message.status}</span>
                </div>
              )}
            </section>

            <section className="items-section">
              <h2>Items from API</h2>
              <div className="items-grid">
                {items.map((item) => (
                  <div key={item.id} className="item-card">
                    <h3>{item.name}</h3>
                    <p>{item.description}</p>
                    <span className="item-id">ID: {item.id}</span>
                  </div>
                ))}
              </div>
            </section>

            <section className="actions">
              <button onClick={fetchData} className="refresh-btn">
                Refresh Data
              </button>
            </section>
          </>
        )}
      </main>

      <footer className="footer">
        <p>Built with Django 5.2.8 + React + Vite</p>
      </footer>
    </div>
  )
}

export default App
