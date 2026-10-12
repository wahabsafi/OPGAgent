#!/bin/bash

# =================================================================
# TVEM MaskDINO API Service Startup Script
# Port: 6602
# GPU: Specified via CUDA_VISIBLE_DEVICES environment variable
# =================================================================

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Set default values
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-6602}"
GPU="${GPU:-0}"
DEVICE="${DEVICE:-cuda:0}"

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  TVEM MaskDINO API Service${NC}"
echo -e "${GREEN}========================================${NC}"
echo "📍 Address: http://${HOST}:${PORT}"
echo "📚 Docs: http://localhost:${PORT}/docs"
echo "🖥️  GPU: $GPU (Device: $DEVICE)"
echo ""

# Set GPU
export CUDA_VISIBLE_DEVICES=$GPU

# Try activating virtual environment
PROJECT_VENV="/data/zhaolin/tool_env/TVEM/.venv"
if [ -f "$PROJECT_VENV/bin/activate" ]; then
    echo -e "${GREEN}Using standalone virtual environment: $PROJECT_VENV${NC}"
    source "$PROJECT_VENV/bin/activate"
    python api_server.py --host "$HOST" --port "$PORT" --device "$DEVICE"
else
    echo "Standalone virtual environment not found, trying project root environment..."
    if [ -f "../../.venv/bin/activate" ]; then
        source "../../.venv/bin/activate"
        python api_server.py --host "$HOST" --port "$PORT" --device "$DEVICE"
    else
        echo "Virtual environment not found, trying uv run..."
        uv run python api_server.py --host "$HOST" --port "$PORT" --device "$DEVICE"
    fi
fi

