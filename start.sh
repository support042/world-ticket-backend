#!/usr/bin/env bash

# Start the Celery worker in the background (&)
celery -A app.infrastructure.celery_app worker --loglevel=info &

# Start the Web API in the foreground (keeps the container alive)
uvicorn app.main:app --host 0.0.0.0 --port $PORT