#!/bin/bash

# =================================================================
# DentalGPT Stop All Replicas Script
# =================================================================

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Stopping All DentalGPT Replicas${NC}"
echo -e "${GREEN}========================================${NC}"

# Port list
PORTS=(6608 6609 6610 6611)

for port in "${PORTS[@]}"; do
    # Find process using the port
    pid=$(lsof -t -i:$port 2>/dev/null)
    
    if [ -n "$pid" ]; then
        echo -e "${YELLOW}Stopping process on port $port (PID: $pid)${NC}"
        kill $pid 2>/dev/null
        sleep 1
        
        # Check if still running
        if kill -0 $pid 2>/dev/null; then
            echo -e "${RED}Force killing PID: $pid${NC}"
            kill -9 $pid 2>/dev/null
        fi
        
        echo -e "${GREEN}✓ Port $port released${NC}"
    else
        echo "No service running on port $port"
    fi
done

echo ""
echo -e "${GREEN}All replicas stopped!${NC}"

