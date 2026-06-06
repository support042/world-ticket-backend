#!/usr/bin/env bash

# 1. Apply database migrations to sync the schema
alembic upgrade head

# Start the FastAPI web server in the foreground
uvicorn app.main:app --host 0.0.0.0 --port $PORT