# VibeEngine

AI-Powered Workflow Engine - Design, orchestrate, and deploy powerful AI agents with visual workflows.

## Features

- 🤖 **Multi-Agent Orchestration** - Coordinate OpenAI, Claude, and Ollama agents
- 🔧 **Custom Tools** - Extend agent capabilities with custom tools and integrations
- 🧠 **Persistent Memory** - Give your agents memory to learn and improve
- ⚡ **Parallel Execution** - Run multiple workflow branches simultaneously
- 🔀 **Conditional Logic** - Smart routing and decision-making
- 📊 **Live Monitoring** - Real-time workflow execution tracking with polling
- 🔐 **User Authentication** - Secure multi-user support with personal workflows
- 🌐 **API Triggers** - Trigger workflows via REST API with API keys
- 📜 **Execution History** - Track and review all workflow executions

## Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- (Optional) Ollama installed locally for local LLM support

## Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd vibeengine
```

### 2. Backend Setup

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Copy environment variables template
cp .env.example .env

# Edit .env and add your API keys
# At minimum, add OPENAI_API_KEY and/or ANTHROPIC_API_KEY

# Run database migrations
python manage.py migrate

# Create superuser (for Django admin access)
python manage.py createsuperuser

# Start Django development server
python manage.py runserver
```

The backend will be available at `http://localhost:8000`

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Environment Variables

Copy `.env.example` to `.env` and configure:

### Required (at least one AI provider):
- `OPENAI_API_KEY` - OpenAI API key for GPT models
- `ANTHROPIC_API_KEY` - Anthropic API key for Claude models

### Optional:
- `OLLAMA_BASE_URL` - Ollama API URL (default: http://localhost:11434)
- `OLLAMA_MODEL` - Default Ollama model (default: llama3.1:8b-instruct)
- `GOOGLE_API_KEY` - For Google Search tool
- `GOOGLE_CSE_ID` - Google Custom Search Engine ID
- `REDIS_URL` - Redis connection URL for distributed memory
- `DEBUG_TOOL_CALLS` - Enable debug logging for tool calls

## Project Structure

```
vibeengine/
├── api/                    # Django REST API
│   ├── drivers/           # Node execution drivers
│   │   ├── openai_agent.py
│   │   ├── claude_agent.py
│   │   ├── ollama_agent.py
│   │   ├── huggingface.py
│   │   ├── text_transform.py
│   │   ├── memory.py
│   │   ├── tool.py
│   │   └── ...
│   ├── orchestration/     # Workflow execution engine
│   │   ├── workflow_executor.py
│   │   └── polling_executor.py
│   ├── migrations/        # Database migrations
│   ├── models.py          # Database models
│   ├── views.py           # API endpoints
│   ├── serializers.py     # DRF serializers
│   └── urls.py            # URL routing
├── frontend/              # React + TypeScript UI
│   ├── src/
│   │   ├── components/   # React components
│   │   │   ├── FlowDiagram.tsx
│   │   │   ├── Login.tsx
│   │   │   ├── Signup.tsx
│   │   │   └── nodes/    # Custom node components
│   │   ├── contexts/     # React contexts
│   │   │   └── AuthContext.tsx
│   │   ├── hooks/        # Custom React hooks
│   │   │   └── usePolling.ts
│   │   └── main.tsx      # Entry point
│   └── package.json
├── backend/               # Django project settings
│   └── settings.py
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── db.sqlite3            # SQLite database
└── manage.py             # Django management script
```

## Usage

### Getting Started

1. Navigate to `http://localhost:5173`
2. Sign up for an account or log in
3. Click "Start Building" to open the workflow designer

### Creating Your First Workflow

1. Add nodes from the toolbar:
   - **Input** - Entry point with static data
   - **AI Agents** - OpenAI, Claude, or Ollama
   - **Tools** - HTTP requests, text manipulation
   - **Output** - Workflow exit point

2. Connect nodes by dragging from output handles to input handles

3. Configure each node by clicking on it:
   - Set AI agent system prompts
   - Configure model parameters
   - Set input values

4. Save your workflow with a name

5. Run it with the "▶️ Run" button and see results in the right sidebar

### Available Node Types

#### AI Agents
- **OpenAI Agent** - GPT-3.5, GPT-4, GPT-4o models
- **Claude Agent** - Claude 3 models (Opus, Sonnet, Haiku) with native tool support
- **Ollama Agent** - Local LLMs via Ollama (Llama, Mistral, etc.)
- **Hugging Face** - Transformers models (sentiment analysis, NER, text classification)

#### Logic & Flow Control
- **Router** - Conditional branching (yes/no decisions)
- **Parallel** - Execute multiple branches concurrently
- **Join** - Merge parallel execution results

#### Data Processing
- **Input** - Static data entry point
- **Output** - Workflow exit point
- **Text Transform** - String manipulation (upper, lower, replace, split, etc.)
- **Validator** - JSON schema validation

#### Tools & Memory
- **Tool** - HTTP requests, append/prepend operations, Google Search
- **Memory** - Read/write persistent key-value storage

### API Access

Enable API access for a workflow:

1. Open your workflow in the designer
2. Click the "⚡ Triggers" button in the toolbar
3. Enable "API Access"
4. Copy the generated API key

Trigger your workflow via API:

```bash
curl -X POST http://localhost:8000/api/workflows/<workflow-id>/trigger/ \
  -H "X-API-Key: <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello World"}'
```

Response includes execution ID, status, and results:

```json
{
  "execution_id": "abc123...",
  "status": "completed",
  "final": "Processed output",
  "trace": [...],
  "execution_time": 2.5
}
```

### Viewing Execution History

1. Click the "📊 History" button in the toolbar
2. Browse all past executions with:
   - Input data
   - Final output
   - Status (completed/error)
   - Execution time
   - Detailed trace of each step

3. Click on the "📜 History" tab in the right sidebar to see per-node execution history

## API Endpoints

### Authentication
- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/` - Login and get token
- `POST /api/auth/logout/` - Logout (invalidate token)
- `GET /api/auth/user/` - Get current user info

### Workflows
- `GET /api/workflows/` - List user's workflows (authenticated)
- `POST /api/workflows/` - Create workflow (authenticated)
- `GET /api/workflows/<id>/` - Get workflow details (owner only)
- `PUT /api/workflows/<id>/` - Update workflow (owner only)
- `DELETE /api/workflows/<id>/` - Delete workflow (owner only)
- `POST /api/workflows/<id>/trigger/` - Trigger workflow via API key
- `POST /api/workflows/<id>/regenerate-api-key/` - Generate new API key
- `GET /api/workflows/<id>/executions/` - Get execution history

### Execution
- `POST /api/execute-workflow-async/` - Execute workflow (async with polling)
- `GET /api/execution/<id>/status/` - Poll execution status
- `POST /api/execute-node/` - Execute single node (testing)

### Node Types
- `GET /api/node-types/` - List all available node types

## Development

### Running Tests

```bash
# Backend tests
python manage.py test

# Run specific test
python manage.py test api.tests.test_drivers
```

### Database Management

```bash
# Create new migration after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Access Django admin
# Navigate to http://localhost:8000/admin
# Login with superuser credentials
```

### Adding New Node Types

1. Create a new driver in `api/drivers/`:

```python
from .base import BaseDriver, DriverResponse

class MyCustomDriver(BaseDriver):
    def execute(self, data: Dict[str, Any], context: Dict[str, Any]) -> DriverResponse:
        # Your logic here
        return DriverResponse(
            output="result",
            final="final result"
        )
```

2. Register in `api/drivers/__init__.py`

3. Add node type definition in `api/node_types.py`

4. Create frontend component in `frontend/src/components/nodes/`

### Building for Production

```bash
# Build frontend
cd frontend
npm run build

# Collect static files (Django)
cd ..
python manage.py collectstatic

# Run with production server (gunicorn)
pip install gunicorn
gunicorn backend.wsgi:application --bind 0.0.0.0:8000
```

For production deployment, also configure:
- Use PostgreSQL or MySQL instead of SQLite
- Set `DEBUG=False` in settings.py
- Configure proper SECRET_KEY
- Set up HTTPS/SSL
- Configure ALLOWED_HOSTS
- Use Redis for caching and memory
- Set up proper CORS origins

## Troubleshooting

### Port already in use
```bash
# Backend - change port
python manage.py runserver 8001

# Frontend - change port
npm run dev -- --port 5174
```

### Database issues
Reset database:
```bash
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

### CORS errors
Ensure frontend URL is in `CORS_ALLOWED_ORIGINS` in `backend/settings.py`:
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
]
```

### API Key Issues
- OpenAI: Ensure `OPENAI_API_KEY` is set in `.env`
- Claude: Ensure `ANTHROPIC_API_KEY` is set in `.env`
- Ollama: Make sure Ollama is running (`ollama serve`)

### Module not found errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r requirements.txt
```

## Technology Stack

### Backend
- Django 5.2.8 - Web framework
- Django REST Framework 3.16.1 - API framework
- django-cors-headers 4.9.0 - CORS support
- transformers 4.57.2 - Hugging Face models
- torch 2.9.1 - PyTorch for ML models
- requests 2.32.5 - HTTP client for API calls

### Frontend
- React 19.2.0 - UI framework
- TypeScript 5.9.3 - Type safety
- Vite 7.2.4 - Build tool
- @xyflow/react 12.9.3 - Workflow diagram library

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]
