#!/bin/bash

# =================================================================
# DentalGPT API Service Startup Script
# Ports: 6608-6611 (4 replicas)
# GPU: Specified via CUDA_VISIBLE_DEVICES environment variable (test: GPU 0-3)
# =================================================================

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
cd "$SCRIPT_DIR"

# Set default values
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-6608}"
GPU="${GPU:-0}"

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  DentalGPT API Service${NC}"
echo -e "${GREEN}========================================${NC}"
echo "📍 Address: http://${HOST}:${PORT}"
echo "📚 Docs: http://localhost:${PORT}/docs"
echo "🖥️  GPU: $GPU"
echo ""

# Check if uv is installed
if ! command -v uv > /dev/null 2>&1; then
    echo -e "${YELLOW}Error: uv is not installed. Please install uv first.${NC}"
    echo "Install command: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Get host local IP
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo "Host IP: $LOCAL_IP"

# Set GPU
export CUDA_VISIBLE_DEVICES=$GPU

# Start service
PROJECT_VENV="/data/zhaolin/tool_env/dentalGPT/.venv"
if [ -f "$PROJECT_VENV/bin/activate" ]; then
    echo -e "${GREEN}Using standalone virtual environment: $PROJECT_VENV${NC}"
    source "$PROJECT_VENV/bin/activate"
    API_PORT=$PORT API_HOST=$HOST python api_server.py
else
    echo "Standalone virtual environment not found, trying project root environment..."
    if [ -f "../../.venv/bin/activate" ]; then
        source "../../.venv/bin/activate"
        API_PORT=$PORT API_HOST=$HOST python api_server.py
    else
        echo "Virtual environment not found, trying uv run..."
        API_PORT=$PORT API_HOST=$HOST uv run api_server.py
    fi
fi

