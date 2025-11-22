# Django + React + TypeScript Full-Stack Application

A modern full-stack web application built with Django (backend) and React + TypeScript (frontend).

## Project Structure

```
.
├── backend/           # Django project configuration
├── api/              # Django REST API app
├── frontend/         # React frontend (Vite)
├── manage.py         # Django management script
└── README.md
```

## Technology Stack

### Backend
- Django 5.2.8
- Django REST Framework 3.16.1
- django-cors-headers 4.9.0
- SQLite (default database)

### Frontend
- React 18
- TypeScript
- Vite (build tool)
- Modern CSS with responsive design

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 24+ and npm
- Virtual environment activated

### Backend Setup

1. Install Python dependencies (already installed in your venv):
   ```bash
   pip install django djangorestframework django-cors-headers
   ```

2. Run migrations:
   ```bash
   python manage.py migrate
   ```

3. Start the Django development server:
   ```bash
   python manage.py runserver
   ```

   The backend will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies (if not already done):
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:5173`

## API Endpoints

The Django backend exposes the following API endpoints:

- `GET /api/hello/` - Returns a hello message with timestamp
- `GET /api/items/` - Returns a list of sample items

## Features

- **Full-stack integration**: React + TypeScript frontend communicates with Django backend via REST API
- **Type safety**: TypeScript interfaces for API responses ensure compile-time type checking
- **CORS enabled**: Properly configured for local development
- **Modern UI**: Clean, responsive design with gradient headers and card layouts
- **Error handling**: Graceful error messages and retry functionality
- **Real-time data**: Fetch and refresh data from the backend

## Development Workflow

1. Keep both servers running in separate terminal windows:
   - Terminal 1: Django backend (`python manage.py runserver`)
   - Terminal 2: React frontend (`cd frontend && npm run dev`)

2. Access the application at `http://localhost:5173`

3. The React app will automatically connect to the Django API at `http://localhost:8000`

## Next Steps

- Add database models in `api/models.py`
- Create serializers in `api/serializers.py`
- Expand API views in `api/views.py`
- Add more React components in `frontend/src/`
- Implement authentication (JWT, OAuth, etc.)
- Add form handling and data persistence

## Project Settings

### CORS Configuration
The backend is configured to accept requests from:
- `http://localhost:5173` (Vite default port)
- `http://localhost:3000` (Alternative React port)

Modify `backend/settings.py` to add additional origins if needed.

### API Configuration
REST Framework is configured with:
- AllowAny permissions (for development)
- JSON-only rendering

Update `backend/settings.py` for production settings.
