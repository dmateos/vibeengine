#!/bin/bash
set -e

# Wait for Redis
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 0.1
done
echo "Redis is ready!"

# Run migrations
if [ "$1" = "web" ]; then
  echo "Running database migrations..."
  python manage.py migrate --noinput

  echo "Starting Django web server..."
  exec gunicorn backend.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
fi

# Run Celery Worker
if [ "$1" = "worker" ]; then
  echo "Starting Celery worker..."
  exec celery -A backend worker \
    --loglevel=info \
    --concurrency=4
fi

# Run Celery Beat
if [ "$1" = "beat" ]; then
  echo "Starting Celery beat..."
  exec celery -A backend beat \
    --loglevel=info \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler
fi

# Default: execute whatever command was passed
exec "$@"
