# VibeEngine

A visual workflow orchestration platform for building and deploying AI-powered automation. Design complex workflows with drag-and-drop simplicity, integrate multiple AI providers, and scale with confidence.

## Features

### AI & Integration
- **Multi-Model AI Support** - OpenAI GPT, Claude, Ollama, and Hugging Face models
- **Tool Calling** - Native tool support for Claude agents and custom tools
- **API Integrations** - HTTP requests, webhooks, external services
- **Database Drivers** - SQL, Redis, and in-memory storage
- **Web Scraping** - Extract data from websites
- **Email (SMTP)** - Send automated emails
- **SSH Execution** - Run remote commands securely

### Workflow Control
- **Visual Flow Designer** - Intuitive drag-and-drop interface built with ReactFlow
- **Conditional Logic** - Smart routing and decision-making with router nodes
- **Parallel Execution** - Run multiple branches simultaneously
- **Loops & Iteration** - For-each and counter-based loops for repeated tasks
- **Sleep/Delay** - Add pauses between workflow steps
- **Error Handling** - Graceful failure management

### Automation & Scheduling
- **Background Processing** - Celery-based async task execution
- **Scheduled Workflows** - Cron-style scheduling with Celery Beat
- **API Triggers** - Secure webhook triggers with API keys
- **Real-time Monitoring** - Live execution tracking with polling
- **Execution History** - Complete audit trail of all workflow runs

### Enterprise Ready
- **Multi-User Support** - User authentication and personal workspaces
- **Docker Deployment** - Production-ready containerization with nginx
- **Scalable Architecture** - Redis-backed message queue for distributed processing
- **Security** - Token authentication, API key management, rate limiting

## Quick Start

### Option 1: Docker (Recommended)

**Development Mode** (with hot reload):
```bash
./docker-start-dev.sh

# Access:
# Frontend: http://localhost:5173 (auto-reload on changes)
# API: http://localhost:8000
```

**Production Mode**:
```bash
./docker-start.sh

# Access everything at: http://localhost
```

See [DOCKER.md](DOCKER.md) and [DOCKER-DEV.md](DOCKER-DEV.md) for detailed documentation.

### Option 2: Manual Setup

**Prerequisites:**
- Python 3.11+
- Node.js 20+
- Redis (for Celery)

**Backend:**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup database
python manage.py migrate
python manage.py createsuperuser

# Start services
python manage.py runserver  # Django server
celery -A backend worker -l info  # Celery worker
celery -A backend beat -l info  # Celery beat (scheduler)
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Access at http://localhost:5173

## Docker Architecture

### Production Setup
```
nginx (port 80)
  ├── Frontend (static files)
  ├── API (proxy to Django)
  └── Admin (proxy to Django)

Django + Gunicorn (port 8000)
  └── Web server

Celery Worker
  └── Background tasks

Celery Beat
  └── Scheduled tasks

Redis
  └── Message broker
```

All services behind nginx on a single port for clean deployment.

### Development Setup
- Frontend: Vite dev server with HMR (port 5173)
- Backend: Django runserver with auto-reload (port 8000)
- Celery: Worker and beat for background tasks
- Optional nginx proxy for unified access

## Workflow Nodes

### AI Agents
- **OpenAI Agent** - GPT-3.5, GPT-4, GPT-4o, o1 models
- **Claude Agent** - Claude 3 (Opus, Sonnet, Haiku) with native tool calling
- **Ollama Agent** - Local LLMs (Llama, Mistral, Qwen, etc.)
- **Hugging Face** - Sentiment analysis, NER, classification, generation

### Control Flow
- **Router** - Conditional branching (if/else logic)
- **Condition** - Boolean evaluation for routing
- **Parallel** - Execute multiple paths concurrently
- **Join** - Merge parallel execution results
- **Loop** - Counter-based iteration (for i in range)
- **For Each** - Iterate over arrays/collections
- **Sleep** - Add delays (milliseconds to hours)

### Data Operations
- **Input** - Static or dynamic data entry
- **Output** - Workflow exit points
- **Text Transform** - String manipulation (case, trim, split, replace)
- **Validator** - JSON schema validation
- **Memory** - Persistent key-value storage

### External Services
- **HTTP Tool** - REST API calls (GET, POST, PUT, DELETE)
- **Web Scraper** - Extract content from websites
- **Email (SMTP)** - Send emails with attachments
- **SQL Database** - Query and modify databases
- **Redis** - Cache and data store operations
- **SSH** - Execute remote commands

## Configuration

Create a `.env` file in the project root:

```bash
# AI Provider Keys (at least one required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Ollama (if using local models)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b-instruct

# Google Search (optional)
GOOGLE_API_KEY=...
GOOGLE_CSE_ID=...

# Redis (required for Celery)
REDIS_URL=redis://localhost:6379/0

# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Email (optional, for SMTP node)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-password
```

## Usage

### Building a Workflow

1. **Create New Workflow**
   - Click "Start Building" or "New Workflow"
   - Give it a name

2. **Add Nodes**
   - Drag nodes from the left sidebar
   - Categories: Triggers, AI Agents, Tools, Control Flow, Data

3. **Connect Nodes**
   - Click and drag from output handles (bottom/right) to input handles (top)
   - Multiple connections supported for parallel execution

4. **Configure Nodes**
   - Click a node to open configuration panel
   - Set prompts, parameters, API keys, etc.
   - Use `{input}` to reference previous node output

5. **Save & Run**
   - Click "Save" to persist workflow
   - Click "Run" to execute
   - View results in right sidebar

### Example: AI Content Pipeline

```
Input (topic)
  → Claude Agent (research)
    → OpenAI Agent (write article)
      → Text Transform (format)
        → Output
```

### Example: Scheduled Email Reports

```
Trigger (cron: daily at 9am)
  → SQL Database (fetch data)
    → OpenAI Agent (generate summary)
      → Email SMTP (send report)
```

### API Access

Enable external triggers:

1. Click "Triggers" button in workflow editor
2. Enable "API Access"
3. Copy the API key

Trigger via HTTP:

```bash
curl -X POST http://localhost/api/workflows/{id}/trigger/ \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"input": "your data"}'
```

### Scheduled Execution

1. Click "Schedules" in workflow editor
2. Add cron expression (e.g., `0 9 * * *` for daily at 9am)
3. Enable the schedule
4. Celery Beat will trigger automatically

## Development

### Project Structure

```
vibeengine/
├── api/                     # Django app
│   ├── drivers/            # Node execution logic
│   ├── orchestration/      # Workflow engine
│   ├── models.py           # Database models
│   ├── views.py            # API endpoints
│   └── tasks.py            # Celery tasks
├── backend/                # Django project
│   ├── settings.py         # Configuration
│   ├── celery.py          # Celery setup
│   └── wsgi.py            # WSGI entry
├── frontend/               # React frontend
│   └── src/
│       ├── components/     # UI components
│       ├── contexts/       # React contexts
│       └── hooks/          # Custom hooks
├── Dockerfile              # Production image
├── Dockerfile.dev          # Development image
├── docker-compose.yml      # Production setup
├── docker-compose.dev.yml  # Development setup
├── nginx.conf              # Production nginx
└── nginx.dev.conf          # Development nginx
```

### Adding Custom Nodes

1. **Create Driver** (`api/drivers/my_node.py`):

```python
from .base import BaseDriver, DriverResponse

class MyNodeDriver(BaseDriver):
    type = "my_node"

    def execute(self, node, context):
        input_data = context.get("input")
        # Your logic here
        result = process(input_data)
        return DriverResponse({
            "status": "ok",
            "output": result
        })
```

2. **Register Driver** (`api/drivers/__init__.py`):

```python
from .my_node import MyNodeDriver

DRIVERS = {
    # ...
    MyNodeDriver.type: MyNodeDriver(),
}
```

3. **Add Node Type** (`api/node_types.py`):

```python
'my_node': {
    'display_name': 'My Node',
    'icon': '🔧',
    'color': '#10b981',
    'description': 'Does something cool',
    'category': 'Tools',
}
```

4. **Create Frontend Component** (`frontend/src/components/nodes/MyNode.tsx`):

```tsx
function MyNode({ data }) {
  return (
    <div className="custom-node">
      <Handle type="target" position={Position.Top} />
      <div className="node-icon">{data.icon}</div>
      <div className="node-label">{data.label}</div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
}
```

### Running Tests

```bash
# Backend
python manage.py test

# Frontend
cd frontend
npm run test
```

### Database Migrations

```bash
# Create migration
python manage.py makemigrations

# Apply migration
python manage.py migrate

# View migrations
python manage.py showmigrations
```

## Deployment

### Production Checklist

- [ ] Set `DEBUG=False` in settings
- [ ] Configure secure `SECRET_KEY`
- [ ] Set proper `ALLOWED_HOSTS`
- [ ] Use PostgreSQL (not SQLite)
- [ ] Configure SSL/HTTPS in nginx
- [ ] Set up proper backup strategy
- [ ] Configure monitoring and logging
- [ ] Set rate limits in nginx
- [ ] Use environment variables for secrets
- [ ] Enable firewall rules
- [ ] Set up health checks

### Docker Production

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Scale workers
docker-compose up -d --scale celery-worker=3

# Stop
docker-compose down
```

See [DOCKER.md](DOCKER.md) for comprehensive deployment guide.

## Technology Stack

### Backend
- Django 5.2.8 - Web framework
- Django REST Framework - API
- Celery 5.4.0 - Task queue
- Redis 5.0.1 - Message broker
- Gunicorn - WSGI server

### Frontend
- React 19.2.0 - UI framework
- TypeScript 5.9.3 - Type safety
- Vite 7.2.4 - Build tool
- ReactFlow 12.9.3 - Workflow diagrams

### AI & ML
- OpenAI 2.8.1 - GPT models
- Anthropic SDK - Claude models
- Transformers 4.57.2 - Hugging Face
- PyTorch 2.9.1 - ML framework

### Infrastructure
- Docker & Docker Compose
- Nginx - Reverse proxy
- SQLite (dev) / PostgreSQL (prod)

## Troubleshooting

**Port conflicts:**
```bash
# Check what's using a port
lsof -i :8000

# Change ports in docker-compose.yml
```

**Redis connection failed:**
```bash
# Check Redis is running
docker-compose ps redis
docker-compose exec redis redis-cli ping
```

**Frontend not updating:**
```bash
# Development mode - should auto-reload
docker-compose -f docker-compose.dev.yml restart frontend

# Production mode - rebuild
docker-compose up -d --build
```

**Celery tasks not processing:**
```bash
# Check worker status
docker-compose logs celery-worker

# Restart worker
docker-compose restart celery-worker
```

**Database locked (SQLite):**
- Use PostgreSQL for production
- Reduce Celery worker concurrency
- Avoid concurrent writes

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

- Documentation: See docs/ folder
- Issues: GitHub Issues
- Docker: [DOCKER.md](DOCKER.md) and [DOCKER-DEV.md](DOCKER-DEV.md)
