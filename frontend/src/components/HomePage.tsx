import { useEffect, useRef } from 'react'
import './HomePage.css'

interface HomePageProps {
  onNavigateToFlow: () => void
}

interface Particle {
  x: number
  y: number
  size: number
  speedX: number
  speedY: number
  opacity: number
}

function HomePage({ onNavigateToFlow }: HomePageProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const mouseGlowRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    canvas.width = window.innerWidth
    canvas.height = window.innerHeight

    const particles: Particle[] = []
    const particleCount = 80

    // Create particles
    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        size: Math.random() * 2 + 0.5,
        speedX: (Math.random() - 0.5) * 0.5,
        speedY: (Math.random() - 0.5) * 0.5,
        opacity: Math.random() * 0.5 + 0.3
      })
    }

    let animationFrameId: number

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      particles.forEach((particle, index) => {
        particle.x += particle.speedX
        particle.y += particle.speedY

        // Wrap around edges
        if (particle.x < 0) particle.x = canvas.width
        if (particle.x > canvas.width) particle.x = 0
        if (particle.y < 0) particle.y = canvas.height
        if (particle.y > canvas.height) particle.y = 0

        // Draw particle
        ctx.beginPath()
        ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(168, 85, 247, ${particle.opacity})`
        ctx.fill()

        // Draw connections
        particles.forEach((otherParticle, otherIndex) => {
          if (index === otherIndex) return
          const dx = particle.x - otherParticle.x
          const dy = particle.y - otherParticle.y
          const distance = Math.sqrt(dx * dx + dy * dy)

          if (distance < 150) {
            ctx.beginPath()
            ctx.moveTo(particle.x, particle.y)
            ctx.lineTo(otherParticle.x, otherParticle.y)
            ctx.strokeStyle = `rgba(168, 85, 247, ${0.15 * (1 - distance / 150)})`
            ctx.lineWidth = 0.5
            ctx.stroke()
          }
        })
      })

      animationFrameId = requestAnimationFrame(animate)
    }

    animate()

    const handleResize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }

    window.addEventListener('resize', handleResize)

    return () => {
      cancelAnimationFrame(animationFrameId)
      window.removeEventListener('resize', handleResize)
    }
  }, [])

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (mouseGlowRef.current) {
        mouseGlowRef.current.style.left = `${e.clientX}px`
        mouseGlowRef.current.style.top = `${e.clientY}px`
      }
    }

    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [])

  return (
    <div className="homepage">
      <canvas ref={canvasRef} className="particle-canvas" />
      <div ref={mouseGlowRef} className="mouse-glow" />

      <div className="hero-section">
        <div className="floating-orbs">
          <div className="orb orb-1"></div>
          <div className="orb orb-2"></div>
          <div className="orb orb-3"></div>
        </div>

        <div className="hero-content">
          <div className="hero-badge">
            <span className="badge-icon">✨</span>
            <span>AI-Powered Workflow Engine</span>
          </div>

          <h1 className="hero-title">
            Build Intelligent
            <br />
            <span className="gradient-text">AI Workflows</span>
          </h1>

          <p className="hero-description">
            Design, orchestrate, and deploy powerful AI agents with visual workflows.
            Connect multiple LLMs, add tools, and create intelligent automation pipelines.
          </p>

          <div className="hero-actions">
            <button className="btn-primary-large" onClick={onNavigateToFlow}>
              <span>Start Building</span>
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M7.5 15l5-5-5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>

          <div className="hero-stats">
            <div className="stat-item">
              <div className="stat-number">25+</div>
              <div className="stat-label">Node Types</div>
            </div>
            <div className="stat-divider"></div>
            <div className="stat-item">
              <div className="stat-number">4</div>
              <div className="stat-label">LLM Providers</div>
            </div>
            <div className="stat-divider"></div>
            <div className="stat-item">
              <div className="stat-number">Visual</div>
              <div className="stat-label">Drag & Drop</div>
            </div>
          </div>
        </div>
      </div>

      <div className="features-section">
        <h2 className="section-title">Powerful Features</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">🤖</div>
            <h3>Multi-LLM Support</h3>
            <p>OpenAI, Claude, Ollama, and HuggingFace models with dynamic configuration</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">🗄️</div>
            <h3>Database Integration</h3>
            <p>Read/write to Redis, PostgreSQL, and MySQL directly from workflows</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">🎨</div>
            <h3>AI Generation</h3>
            <p>Create embeddings and generate images with DALL-E, Stable Diffusion</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">🐍</div>
            <h3>Code Execution</h3>
            <p>Run Python code and SSH commands on remote servers</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">⏰</div>
            <h3>Scheduled Workflows</h3>
            <p>Trigger workflows on schedule with cron expressions</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">🔌</div>
            <h3>MCP Integration</h3>
            <p>Connect to Model Context Protocol servers for extended capabilities</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">⚡</div>
            <h3>Parallel Execution</h3>
            <p>Run multiple workflow branches simultaneously for faster processing</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">📱</div>
            <h3>Notifications</h3>
            <p>Send push notifications via Pushover and output HTML previews</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">🧠</div>
            <h3>Persistent Memory</h3>
            <p>Give your agents memory to maintain state across executions</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">🔀</div>
            <h3>Smart Routing</h3>
            <p>Conditional logic and dynamic routing based on context</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">💬</div>
            <h3>Multi-Agent Chat</h3>
            <p>Create consensus and conversation flows between multiple agents</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3>Live Monitoring</h3>
            <p>Track workflow execution in real-time with detailed traces and logs</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default HomePage
