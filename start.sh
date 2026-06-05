#!/usr/bin/env bash

# Start the FastAPI web server in the foreground
uvicorn app.main:app --host 0.0.0.0 --port $PORT