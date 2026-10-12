#!/bin/bash
# Resume inference: Only process samples in output directory that do not have answer.txt yet

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

DATA_DIR="${1:-dataset}"
OUTPUT_DIR="${2:-$PROJECT_DIR/runs/inference}"
QUESTION="Analyze this OPG image and provide a diagnostic report."

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}OPGAgent Resume Inference${NC}"
echo -e "${BLUE}============================================================${NC}"
echo -e "Data directory: ${GREEN}$DATA_DIR${NC}"
echo -e "Output directory: ${GREEN}$OUTPUT_DIR${NC}"
echo -e "${BLUE}------------------------------------------------------------${NC}"

SAMPLES=()
for sample_dir in "$DATA_DIR"/*/; do
    if [[ -d "$sample_dir" && -f "${sample_dir}image_1.png" ]]; then
        sample_id=$(basename "$sample_dir")
        if [[ -f "$OUTPUT_DIR/$sample_id/answer.txt" ]]; then
            continue
        fi
        SAMPLES+=("$sample_dir")
    fi
done

TOTAL_SAMPLES=${#SAMPLES[@]}
echo -e "Pending: ${GREEN}$TOTAL_SAMPLES${NC} samples"
echo -e "${BLUE}------------------------------------------------------------${NC}"

cd "$PROJECT_DIR"

SUCCESS_COUNT=0
FAIL_COUNT=0

for i in "${!SAMPLES[@]}"; do
    sample_dir="${SAMPLES[$i]}"
    sample_id=$(basename "$sample_dir")
    image_path="${sample_dir}image_1.png"

    sample_output_dir="$OUTPUT_DIR/${sample_id}"
    mkdir -p "$sample_output_dir"
    output_file="$sample_output_dir/agent_io.json"

    current=$((i + 1))
    echo -e "\n${YELLOW}[$current/$TOTAL_SAMPLES]${NC} Processing: ${GREEN}$sample_id${NC}"

    START_TIME=$(date +%s)

    if uv run python -m opgagent.cli \
        --question "$QUESTION" \
        --image_path "$image_path" \
        --output "$output_file" \
        --tool-service api_service 2>&1; then
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        echo -e "  ${GREEN}✓ Success${NC} (Elapsed: ${DURATION}s)"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        echo -e "  ${RED}✗ Failed${NC} (Elapsed: ${DURATION}s)"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
done

echo -e "\n${BLUE}============================================================${NC}"
echo -e "${BLUE}Inference Completed${NC}"
echo -e "${BLUE}============================================================${NC}"
echo -e "Total samples: ${YELLOW}$TOTAL_SAMPLES${NC}"
echo -e "Success: ${GREEN}$SUCCESS_COUNT${NC}"
echo -e "Failed: ${RED}$FAIL_COUNT${NC}"

