#!/bin/bash

# DentalGPT API Server Startup Script (uv version)

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
cd "$SCRIPT_DIR"

echo "================================="
echo "DentalGPT API Server Startup Script"
echo "================================="

# Check if uv is installed
echo ""
echo "Checking uv environment..."
if ! command -v uv > /dev/null 2>&1; then
    echo "Error: uv is not installed. Please install uv first."
    echo "Install command: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Get host local IP
echo ""
echo "Fetching host IP address..."
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo "Host IP: $LOCAL_IP"

# Set port
PORT=${API_PORT:-8566}
HOST=${API_HOST:-0.0.0.0}

echo ""
echo "Service configuration:"
echo "  - Package manager: uv"
echo "  - Access URL: http://$LOCAL_IP:$PORT"
echo "  - API Docs: http://$LOCAL_IP:$PORT/docs"
echo "  - Health check: http://$LOCAL_IP:$PORT/health"
echo ""

# Start server
echo "Starting server..."

# Use dedicated virtual environment
PROJECT_VENV="/data/zhaolin/tool_env/dentalGPT/.venv"
if [ -f "$PROJECT_VENV/bin/activate" ]; then
    echo "Using standalone virtual environment: $PROJECT_VENV"
    source "$PROJECT_VENV/bin/activate"
    python api_server.py
else
    echo "Standalone virtual environment not found, trying project root environment..."
    if [ -f "../../.venv/bin/activate" ]; then
        source "../../.venv/bin/activate"
        python api_server.py
    else
        echo "Virtual environment not found, trying uv run..."
        uv run api_server.py
    fi
fi


