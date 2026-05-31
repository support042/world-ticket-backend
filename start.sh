#!/usr/bin/env bash

# Start Celery in the background, limited to exactly 1 worker to save RAM!
celery -A app.infrastructure.celery_app worker --loglevel=info --concurrency=1 &

# Start the FastAPI web server in the foreground
uvicorn app.main:app --host 0.0.0.0 --port $PORT