import { useState, useEffect } from 'react'
import './App.css'
import FlowDiagram from './components/FlowDiagram'

const API_BASE_URL = 'http://localhost:8000/api'

type TabType = 'api' | 'workflow'

interface HelloMessage {
  message: string
  timestamp: string
  status: string
}

interface Item {
  id: number
  name: string
  description: string
}

interface ItemsResponse {
  items: Item[]
  count: number
}

function App() {
  const [activeTab, setActiveTab] = useState<TabType>('workflow')
  const [message, setMessage] = useState<HelloMessage | null>(null)
  const [items, setItems] = useState<Item[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch hello message
      const helloResponse = await fetch(`${API_BASE_URL}/hello/`)
      const helloData: HelloMessage = await helloResponse.json()
      setMessage(helloData)

      // Fetch items
      const itemsResponse = await fetch(`${API_BASE_URL}/items/`)
      const itemsData: ItemsResponse = await itemsResponse.json()
      setItems(itemsData.items)

      setLoading(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Django + React App</h1>
        <p className="subtitle">Full-stack application with Django backend and React frontend</p>

        <div className="tabs">
          <button
            className={`tab ${activeTab === 'workflow' ? 'active' : ''}`}
            onClick={() => setActiveTab('workflow')}
          >
            Workflow Designer
          </button>
          <button
            className={`tab ${activeTab === 'api' ? 'active' : ''}`}
            onClick={() => setActiveTab('api')}
          >
            API Demo
          </button>
        </div>
      </header>

      <main className="main-content">
        {activeTab === 'workflow' && (
          <div className="workflow-container">
            <FlowDiagram />
          </div>
        )}

        {activeTab === 'api' && (
          <>
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
          </>
        )}
      </main>

      <footer className="footer">
        <p>Built with Django 5.2.8 + React + TypeScript + Vite</p>
      </footer>
    </div>
  )
}

export default App
