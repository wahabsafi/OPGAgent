#!/bin/bash

# =================================================================
# OralGPT-Omni API Service Startup Script
# Ports: 6604-6607 (4 replicas)
# GPU: Specified via CUDA_VISIBLE_DEVICES environment variable (test: GPU 0-3)
# =================================================================

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
cd "$SCRIPT_DIR"

# Set default values
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-6604}"
GPU="${GPU:-0}"

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  OralGPT-Omni API Service${NC}"
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

# Set GPU
export CUDA_VISIBLE_DEVICES=$GPU

# Start service
PROJECT_VENV="/data/zhaolin/tool_env/OralGPT-omni/.venv"
if [ -f "$PROJECT_VENV/bin/activate" ]; then
    echo -e "${GREEN}Using standalone virtual environment: $PROJECT_VENV${NC}"
    source "$PROJECT_VENV/bin/activate"
    python api_server.py --host "$HOST" --port "$PORT"
else
    echo "Standalone virtual environment not found, trying project root environment..."
    if [ -f "../../.venv/bin/activate" ]; then
        source "../../.venv/bin/activate"
        python api_server.py --host "$HOST" --port "$PORT"
    else
        echo "Virtual environment not found, trying uv run..."
        uv run api_server.py --host "$HOST" --port "$PORT"
    fi
fi

