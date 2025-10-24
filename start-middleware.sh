#!/bin/bash

# Start OpenAI-compatible middleware service
# Usage: ./start-middleware.sh [port]

PORT=${1:-8000}

echo "=================================================="
echo "  OpenAI-Compatible Middleware Service"
echo "=================================================="
echo ""
echo "Starting middleware on port $PORT..."
echo "Press Ctrl+C to stop"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found"
    echo "   Run: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found"
    echo "   Make sure you have configured:"
    echo "   - OPENAI_API_KEY"
    echo "   - TYPESENSE_API_KEY"
    echo "   - TYPESENSE_HOST"
    echo ""
fi

# Start the service using Python module syntax
# This ensures proper module imports
cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}$(pwd)"
./venv/bin/uvicorn src.openai_middleware:app --host 0.0.0.0 --port $PORT --reload
