#!/bin/bash

# Production startup script for Render

# Set default PORT if not provided
export PORT=${PORT:-8000}

# Start the FastAPI application with uvicorn
exec uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1