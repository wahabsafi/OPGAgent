#!/bin/bash

# =================================================================
# OPGAgent All API Services Startup Script (Single-GPU Mode)
# Starts all 5 tool services on GPU 0 (for 1x A100 / RTX GPU)
# =================================================================

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

echo -e "${CYAN}====================================================${NC}"
echo -e "${CYAN}  OPGAgent API Services (Single GPU Mode - GPU 0)${NC}"
echo -e "${CYAN}====================================================${NC}"
echo ""
echo "Port allocation:"
echo "  - yolo_enumeration: 6600 (GPU 0)"
echo "  - tvem:             6602 (GPU 0)"
echo "  - medsam:           6603 (GPU 0)"
echo "  - oral_gpt:         6604 (GPU 0 - Single Replica)"
echo "  - dental_gpt:       6608 (GPU 0 - Single Replica)"
echo ""

start_service() {
    local name=$1
    local dir=$2
    local port=$3
    local gpu=$4
    local extra_env=$5
    local log_file="$LOG_DIR/${name}.log"
    
    echo -e "${GREEN}Starting $name (Port: $port, GPU: $gpu)...${NC}"
    cd "$SCRIPT_DIR/$dir"
    eval "PORT=$port GPU=$gpu $extra_env nohup bash start_api.sh > \"$log_file\" 2>&1 &"
    echo "  PID: $!, Log: $log_file"
    cd "$SCRIPT_DIR"
}

# Check if GGUF llama-server should be started
GGUF_DIR="$PROJECT_ROOT/weights/dental_gpt_gguf"
if [ -d "$GGUF_DIR" ] || [ "$USE_LLAMA_SERVER" = "1" ] || [ -n "$LLAMA_SERVER_URL" ]; then
    echo -e "${YELLOW}=== Checking / Starting llama-server for GGUF model ===${NC}"
    export LLAMA_SERVER_URL="${LLAMA_SERVER_URL:-http://127.0.0.1:8090}"
    if ! curl -s -o /dev/null -w "%{http_code}" --connect-timeout 1 "$LLAMA_SERVER_URL/health" 2>/dev/null | grep -q "200"; then
        echo "Launching llama-server on port 8090..."
        bash "$SCRIPT_DIR/start_llama_server.sh"
        echo "Waiting for llama-server to load model and report healthy..."
        for i in {1..20}; do
            if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 1 "$LLAMA_SERVER_URL/health" 2>/dev/null | grep -q "200"; then
                echo -e "${GREEN}✓ llama-server is ready!${NC}"
                break
            fi
            sleep 1
        done
    else
        echo -e "${GREEN}✓ llama-server is already running and healthy at $LLAMA_SERVER_URL${NC}"
    fi
fi

# 1. Start YOLO (Tooth Enumeration)
echo -e "${YELLOW}=== [1/5] Starting YOLO Enumeration ===${NC}"
start_service "yolo_enumeration" "yolo_enumeration" 6600 0
sleep 2

# 2. Start TVEM (MaskDINO)
echo -e "${YELLOW}=== [2/5] Starting TVEM MaskDINO ===${NC}"
start_service "tvem" "tvem" 6602 0 "DEVICE=cuda:0" "TVEM_WEIGHTS_DIR=${TVEM_WEIGHTS_DIR:-$HOME/tvem}"
sleep 2

# 3. Start MedSAM
echo -e "${YELLOW}=== [3/5] Starting MedSAM ===${NC}"
start_service "medsam" "medsam" 6603 0
sleep 2

# 4. Start OralGPT (Single Replica on Port 6604)
echo -e "${YELLOW}=== [4/5] Starting OralGPT (Single Replica) ===${NC}"
start_service "oral_gpt" "oral_gpt" 6604 0 "${LLAMA_SERVER_URL:+LLAMA_SERVER_URL=$LLAMA_SERVER_URL}"
sleep 3

# 5. Start DentalGPT (Single Replica on Port 6608)
echo -e "${YELLOW}=== [5/5] Starting DentalGPT (Single Replica) ===${NC}"
start_service "dental_gpt" "dental_gpt" 6608 0 "${LLAMA_SERVER_URL:+LLAMA_SERVER_URL=$LLAMA_SERVER_URL}"
sleep 3

echo ""
echo -e "${CYAN}====================================================${NC}"
echo -e "${CYAN}  All 5 services initiated in background!${NC}"
echo -e "${CYAN}====================================================${NC}"
echo ""
echo "Wait ~1-2 minutes for VLMs to load into VRAM, then run:"
echo "  bash check_health.sh"
echo ""
echo "To stop all services:"
echo "  bash stop_all_services.sh"
