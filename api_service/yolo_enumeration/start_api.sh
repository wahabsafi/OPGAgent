#!/bin/bash

# =================================================================
# YOLO Tooth Enumeration Detection API Service Startup Script
# Port: 6600
# GPU: Specified via CUDA_VISIBLE_DEVICES environment variable
# =================================================================

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
cd "$SCRIPT_DIR"

# Set default values
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-6600}"
WORKERS="${WORKERS:-1}"
GPU="${GPU:-0}"

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  YOLO Tooth Enumeration Detection API Service${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Host: $HOST"
echo "Port: $PORT"
echo "GPU: $GPU"
echo "Workers: $WORKERS"
echo ""

# Set GPU
export CUDA_VISIBLE_DEVICES=$GPU

# Try activating virtual environment
PROJECT_VENV="/data/zhaolin/tool_env/yolo_enumeration/.venv"
if [ -f "$PROJECT_VENV/bin/activate" ]; then
    echo -e "${GREEN}Using standalone virtual environment: $PROJECT_VENV${NC}"
    source "$PROJECT_VENV/bin/activate"
elif [ -f "../../.venv/bin/activate" ]; then
    echo -e "${GREEN}Using project root virtual environment${NC}"
    source "../../.venv/bin/activate"
fi

# Start service
if command -v uv > /dev/null 2>&1 && [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${GREEN}Starting service using uv${NC}"
    uv run uvicorn api_server:app \
        --host "$HOST" \
        --port "$PORT" \
        --workers "$WORKERS" \
        --log-level info
else
    python -m uvicorn api_server:app \
        --host "$HOST" \
        --port "$PORT" \
        --workers "$WORKERS" \
        --log-level info
fi

