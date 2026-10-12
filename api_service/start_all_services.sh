#!/bin/bash

# =================================================================
# Agent_v3 All API Services Startup Script
# Start all tool services (Test environment, GPU 0-3)
# =================================================================

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
cd "$SCRIPT_DIR"

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Log directory
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Agent_v3 API Services All Starting${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo "Port allocation:"
echo "  - yolo_enumeration:      6600 (GPU 0)"
echo "  - tvem:                   6602 (GPU 2)"
echo "  - medsam:                 6603 (GPU 3)"
echo "  - oral_gpt:               6604-6607 (GPU 0-3)"
echo "  - dental_gpt:             6608-6611 (GPU 0-3)"
echo ""

# Service startup function
start_service() {
    local name=$1
    local dir=$2
    local port=$3
    local gpu=$4
    local log_file="$LOG_DIR/${name}.log"
    
    echo -e "${GREEN}Starting $name (Port: $port, GPU: $gpu)...${NC}"
    cd "$SCRIPT_DIR/$dir"
    PORT=$port GPU=$gpu nohup bash start_api.sh > "$log_file" 2>&1 &
    echo "  PID: $!, Log: $log_file"
    cd "$SCRIPT_DIR"
}

# Start YOLO service
echo -e "${YELLOW}=== Starting YOLO Service ===${NC}"
start_service "yolo_enumeration" "yolo_enumeration" 6600 0
sleep 2

# Start TVEM
echo ""
echo -e "${YELLOW}=== Starting TVEM Service ===${NC}"
start_service "tvem" "tvem" 6602 2
sleep 2

# Start MedSAM
echo ""
echo -e "${YELLOW}=== Starting MedSAM Service ===${NC}"
start_service "medsam" "medsam" 6603 3
sleep 2

# Start VLM Services (Multi-replica)
echo ""
echo -e "${YELLOW}=== Starting OralGPT Service (4 Replicas) ===${NC}"
cd "$SCRIPT_DIR/oral_gpt"
bash start_all_replicas.sh
cd "$SCRIPT_DIR"
sleep 5

echo ""
echo -e "${YELLOW}=== Starting DentalGPT Service (4 Replicas) ===${NC}"
cd "$SCRIPT_DIR/dental_gpt"
bash start_all_replicas.sh
cd "$SCRIPT_DIR"
sleep 5

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  All services started successfully!${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo "Once services are ready, you can run a health check:"
echo "  bash check_health.sh"
echo ""
echo "Stop all services:"
echo "  bash stop_all_services.sh"

