#!/bin/bash

# =================================================================
# Agent_v3 API Services Health Check Script
# =================================================================

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Agent_v3 API Services Health Check${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Service configuration
declare -A SERVICES=(
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

# Statistics
total=0
healthy=0
unhealthy=0

for port in "${!SERVICES[@]}"; do
    service_name="${SERVICES[$port]}"
    total=$((total + 1))
    
    # Check health status
    response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "http://localhost:$port/health" 2>/dev/null)
    
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✓ $service_name (Port: $port) - Healthy${NC}"
        healthy=$((healthy + 1))
    else
        echo -e "${RED}✗ $service_name (Port: $port) - Unavailable (HTTP: $response)${NC}"
        unhealthy=$((unhealthy + 1))
    fi
done

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "Total: $total | ${GREEN}Healthy: $healthy${NC} | ${RED}Unavailable: $unhealthy${NC}"
echo -e "${CYAN}========================================${NC}"

# Return error code if any service is unavailable
if [ $unhealthy -gt 0 ]; then
    exit 1
fi

