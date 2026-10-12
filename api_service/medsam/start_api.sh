#!/bin/bash

# =================================================================
# MedSAM Segmentation API Service Startup Script
# Port: 6603
# GPU: Specified via CUDA_VISIBLE_DEVICES environment variable
# =================================================================

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Set default values
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-6603}"
GPU="${GPU:-0}"

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  MedSAM Segmentation API Service${NC}"
echo -e "${GREEN}========================================${NC}"
echo "📍 Address: http://${HOST}:${PORT}"
echo "📚 Docs: http://localhost:${PORT}/docs"
echo "🖥️  GPU: $GPU"
echo ""

# Set GPU
export CUDA_VISIBLE_DEVICES=$GPU

# Activate virtual environment
if [ -d ".venv" ]; then
    echo -e "${GREEN}Using virtual environment: $SCRIPT_DIR/.venv${NC}"
    source .venv/bin/activate
else
    echo -e "${YELLOW}⚠️  Virtual environment does not exist. Please run first: uv venv --python 3.10${NC}"
    exit 1
fi

# Check model file
MODEL_PATH="MedSAM/work_dir/MedSAM/medsam_vit_b.pth"
if [ ! -f "$MODEL_PATH" ]; then
    echo -e "${YELLOW}⚠️  Model file not found: $MODEL_PATH${NC}"
    echo "Please download the model from:"
    echo "https://github.com/bowang-lab/MedSAM"
    echo ""
fi

# Start service
echo "Starting FastAPI service..."
export API_PORT=$PORT
export API_HOST=$HOST
python api_server.py

