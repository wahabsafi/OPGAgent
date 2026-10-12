#!/bin/bash

# TVEM 4Quadrants API Service Startup Script (uv version)

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Set port
PORT=${API_PORT:-8001}
HOST=${API_HOST:-0.0.0.0}

echo "🚀 Starting TVEM 4Quadrants API Service..."
echo "📍 Address: http://${HOST}:${PORT}"
echo "📚 Docs: http://localhost:${PORT}/docs"
echo ""

# Run using uv / virtual environment
PROJECT_VENV="/data/zhaolin/tool_env/TVEM/.venv"
if [ -f "$PROJECT_VENV/bin/activate" ]; then
    echo "Using standalone virtual environment: $PROJECT_VENV"
    source "$PROJECT_VENV/bin/activate"
    python api_server_4quadrants.py --host "$HOST" --port "$PORT"
else
    echo "Standalone virtual environment not found, trying project root environment..."
    if [ -f "../../.venv/bin/activate" ]; then
        source "../../.venv/bin/activate"
        python api_server_4quadrants.py --host "$HOST" --port "$PORT"
    else
        echo "Virtual environment not found, trying uv run..."
        uv run python api_server_4quadrants.py --host "$HOST" --port "$PORT"
    fi
fi


