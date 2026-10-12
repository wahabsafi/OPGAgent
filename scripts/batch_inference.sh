#!/bin/bash
# =============================================================================
# OPGAgent / Agent_v3 Batch Inference Script
# 
# Purpose: Perform OPG diagnostic analysis on all samples under dataset directory
# Output: runs/inference_<Melbourne_timestamp>/ directory
#
# Usage:
#   bash scripts/batch_inference.sh                    # Use default data directory
#   bash scripts/batch_inference.sh /path/to/data      # Specify data directory
#   bash scripts/batch_inference.sh --help             # Show help
# =============================================================================

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DEFAULT_DATA_DIR="test_data"
QUESTION="Analyze this OPG image and provide a diagnostic report."

# Show help
show_help() {
    echo -e "${BLUE}OPGAgent Batch Inference Script${NC}"
    echo ""
    echo "Usage:"
    echo "  bash $0 [data_dir] [options]"
    echo ""
    echo "Arguments:"
    echo "  data_dir    Path containing sample subdirectories (default: $DEFAULT_DATA_DIR)"
    echo ""
    echo "Options:"
    echo "  --help          Show this help message"
    echo "  --no-langsmith  Disable LangSmith tracing"
    echo ""
    echo "Examples:"
    echo "  bash $0                                # Use default data directory"
    echo "  bash $0 /path/to/my_data               # Specify custom data directory"
    echo "  bash $0 --no-langsmith                 # Disable LangSmith"
    echo ""
    echo "Output directory structure:"
    echo "  runs/inference_YYYYMMDD_HHMMSS/"
    echo "    ├── <sample_id_1>/"
    echo "    │   ├── agent_io.json"
    echo "    │   └── answer.txt"
    echo "    ├── <sample_id_2>/"
    echo "    │   ├── agent_io.json"
    echo "    │   └── answer.txt"
    echo "    ├── ..."
    echo "    └── summary.json"
}

# Parse arguments
DATA_DIR="$DEFAULT_DATA_DIR"
USE_LANGSMITH=true

for arg in "$@"; do
    case $arg in
        --help|-h)
            show_help
            exit 0
            ;;
        --no-langsmith)
            USE_LANGSMITH=false
            ;;
        *)
            if [[ -d "$arg" ]]; then
                DATA_DIR="$arg"
            fi
            ;;
    esac
done

# Check data directory
if [[ ! -d "$DATA_DIR" ]]; then
    echo -e "${RED}Error: Data directory does not exist: $DATA_DIR${NC}"
    exit 1
fi

# Generate Melbourne timestamp
MELBOURNE_TIMESTAMP=$(TZ='Australia/Melbourne' date '+%Y%m%d_%H%M%S')
OUTPUT_DIR="$PROJECT_DIR/runs/inference_${MELBOURNE_TIMESTAMP}"
mkdir -p "$OUTPUT_DIR"

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}OPGAgent Batch Inference${NC}"
echo -e "${BLUE}============================================================${NC}"
echo -e "Data directory: ${GREEN}$DATA_DIR${NC}"
echo -e "Output directory: ${GREEN}$OUTPUT_DIR${NC}"
echo -e "Melbourne time: ${YELLOW}$(TZ='Australia/Melbourne' date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "LangSmith: ${YELLOW}$USE_LANGSMITH${NC}"
echo -e "${BLUE}------------------------------------------------------------${NC}"

# Collect all sample directories
SAMPLES=()
for sample_dir in "$DATA_DIR"/*/; do
    if [[ -d "$sample_dir" ]]; then
        # Check if directory contains image_1.png
        if [[ -f "${sample_dir}image_1.png" ]]; then
            SAMPLES+=("$sample_dir")
        fi
    fi
done

TOTAL_SAMPLES=${#SAMPLES[@]}
if [[ $TOTAL_SAMPLES -eq 0 ]]; then
    echo -e "${RED}Error: No valid samples found (requires image_1.png in folder)${NC}"
    exit 1
fi

echo -e "Found ${GREEN}$TOTAL_SAMPLES${NC} samples"
echo -e "${BLUE}------------------------------------------------------------${NC}"

# Initialize statistics
SUCCESS_COUNT=0
FAIL_COUNT=0
RESULTS=()

# Switch to project directory
cd "$PROJECT_DIR"

# Iterate over each sample
for i in "${!SAMPLES[@]}"; do
    sample_dir="${SAMPLES[$i]}"
    sample_id=$(basename "$sample_dir")
    image_path="${sample_dir}image_1.png"
    
    # Create output directory for sample
    sample_output_dir="$OUTPUT_DIR/${sample_id}"
    mkdir -p "$sample_output_dir"
    output_file="$sample_output_dir/agent_io.json"
    
    current=$((i + 1))
    echo -e "\n${YELLOW}[$current/$TOTAL_SAMPLES]${NC} Processing: ${GREEN}$sample_id${NC}"
    
    # Build command
    CMD="uv run python -m opgagent.cli"
    CMD+=" --question \"$QUESTION\""
    CMD+=" --image_path \"$image_path\""
    CMD+=" --output \"$output_file\""

    if [[ "$USE_LANGSMITH" == false ]]; then
        CMD+=" --no-langsmith"
    fi
    
    # Execute inference
    START_TIME=$(date +%s)
    
    if eval "$CMD" 2>&1; then
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        echo -e "  ${GREEN}✓ Success${NC} (Elapsed: ${DURATION}s)"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        RESULTS+=("{\"sample_id\": \"$sample_id\", \"status\": \"success\", \"duration_s\": $DURATION}")
    else
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        echo -e "  ${RED}✗ Failed${NC} (Elapsed: ${DURATION}s)"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        RESULTS+=("{\"sample_id\": \"$sample_id\", \"status\": \"failed\", \"duration_s\": $DURATION}")
    fi
done

# Generate summary report
SUMMARY_FILE="$OUTPUT_DIR/summary.json"
MELBOURNE_END_TIME=$(TZ='Australia/Melbourne' date '+%Y-%m-%d %H:%M:%S')

cat > "$SUMMARY_FILE" << EOF
{
  "batch_info": {
    "timestamp_melbourne": "$(TZ='Australia/Melbourne' date '+%Y-%m-%d %H:%M:%S')",
    "timestamp_utc": "$(date -u '+%Y-%m-%d %H:%M:%S')",
    "data_directory": "$DATA_DIR",
    "output_directory": "$OUTPUT_DIR",
    "question": "$QUESTION",
    "langsmith_enabled": $USE_LANGSMITH
  },
  "statistics": {
    "total_samples": $TOTAL_SAMPLES,
    "success": $SUCCESS_COUNT,
    "failed": $FAIL_COUNT,
    "success_rate": $(echo "scale=2; $SUCCESS_COUNT * 100 / $TOTAL_SAMPLES" | bc)
  },
  "results": [
    $(IFS=,; echo "${RESULTS[*]}")
  ]
}
EOF

# Output summary
echo -e "\n${BLUE}============================================================${NC}"
echo -e "${BLUE}Batch Inference Completed${NC}"
echo -e "${BLUE}============================================================${NC}"
echo -e "Total samples: ${YELLOW}$TOTAL_SAMPLES${NC}"
echo -e "Success: ${GREEN}$SUCCESS_COUNT${NC}"
echo -e "Failed: ${RED}$FAIL_COUNT${NC}"
echo -e "Success rate: ${YELLOW}$(echo "scale=1; $SUCCESS_COUNT * 100 / $TOTAL_SAMPLES" | bc)%${NC}"
echo -e "${BLUE}------------------------------------------------------------${NC}"
echo -e "Output directory: ${GREEN}$OUTPUT_DIR${NC}"
echo -e "Summary file: ${GREEN}$SUMMARY_FILE${NC}"
echo -e "Completion time (Melbourne): ${YELLOW}$MELBOURNE_END_TIME${NC}"
echo -e "${BLUE}============================================================${NC}"
