#!/bin/bash

# =================================================================
# Agent_v3 All API Services Stop Script
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

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Agent_v3 Stopping All API Services${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# All service ports
ALL_PORTS=(6600 6602 6603 6604 6605 6606 6607 6608 6609 6610 6611)

# Port to name mapping
declare -A PORT_NAMES=(
    [6600]="yolo_enumeration"
    [6602]="tvem"
    [6603]="medsam"
    [6604]="oral_gpt_0"
    [6605]="oral_gpt_1"
    [6606]="oral_gpt_2"
    [6607]="oral_gpt_3"
    [6608]="dental_gpt_0"
    [6609]="dental_gpt_1"
    [6610]="dental_gpt_2"
    [6611]="dental_gpt_3"
)

for port in "${ALL_PORTS[@]}"; do
    service_name="${PORT_NAMES[$port]}"
    pid=$(lsof -t -i:$port 2>/dev/null)
    
    if [ -n "$pid" ]; then
        echo -e "${YELLOW}Stopping $service_name (Port: $port, PID: $pid)${NC}"
        kill $pid 2>/dev/null
        sleep 0.5
        
        # Check if still running
        if kill -0 $pid 2>/dev/null; then
            echo -e "${RED}  Force killing PID: $pid${NC}"
            kill -9 $pid 2>/dev/null
        fi
        
        echo -e "${GREEN}  ✓ Stopped${NC}"
    else
        echo "No service running on port $port ($service_name)"
    fi
done

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  All services stopped!${NC}"
echo -e "${CYAN}========================================${NC}"

