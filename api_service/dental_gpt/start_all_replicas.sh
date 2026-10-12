#!/bin/bash

# =================================================================
# DentalGPT All Replicas Startup Script (4 replicas)
# Ports: 6608-6611
# GPU: Assigned to GPU 0-3
# =================================================================

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
cd "$SCRIPT_DIR"

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Replica configuration
declare -A REPLICAS=(
    [0]="6608:0"  # Replica 0: Port 6608, GPU 0
    [1]="6609:1"  # Replica 1: Port 6609, GPU 1
    [2]="6610:2"  # Replica 2: Port 6610, GPU 2
    [3]="6611:3"  # Replica 3: Port 6611, GPU 3
)

# Log directory
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  DentalGPT Multi-Replica Startup${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Number of replicas: ${#REPLICAS[@]}"
echo "Port range: 6608-6611"
echo "GPU assignment: 0-3"
echo ""

# Startup function
start_replica() {
    local replica_id=$1
    local config="${REPLICAS[$replica_id]}"
    local port="${config%:*}"
    local gpu="${config#*:}"
    local log_file="$LOG_DIR/dental_gpt_replica_${replica_id}.log"
    
    echo -e "${GREEN}Starting replica $replica_id: Port=$port, GPU=$gpu${NC}"
    
    # Start in background
    PORT=$port GPU=$gpu nohup bash start_api.sh > "$log_file" 2>&1 &
    echo "PID: $!, Log: $log_file"
}

# Start all replicas
for replica_id in "${!REPLICAS[@]}"; do
    start_replica $replica_id
    sleep 2  # Wait 2 seconds before starting next replica
done

echo ""
echo -e "${GREEN}All replicas started!${NC}"
echo ""
echo "Health check commands:"
for replica_id in "${!REPLICAS[@]}"; do
    config="${REPLICAS[$replica_id]}"
    port="${config%:*}"
    echo "  curl http://localhost:$port/health"
done
echo ""
echo "Stop all replicas: bash stop_all_replicas.sh"

