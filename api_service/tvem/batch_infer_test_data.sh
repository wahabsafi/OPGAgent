#!/bin/bash

# Batch inference script for processing all samples under test_data directory
# Usage: bash batch_infer_test_data.sh <test_data_dir>

set -e

# Argument parsing
TEST_DATA_DIR="${1:-test_data}"
CONFIDENCE=0.3

# Script directory (for resolving configs and weights)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🦷 Batch inference on all data in test_data directory"
echo "Data directory: $TEST_DATA_DIR"
echo "Confidence threshold: $CONFIDENCE"
echo ""

# Activate virtual environment
PROJECT_VENV="/data/zhaolin/tool_env/TVEM/.venv"
if [ -f "$PROJECT_VENV/bin/activate" ]; then
    echo "Using standalone virtual environment: $PROJECT_VENV"
    source "$PROJECT_VENV/bin/activate"
elif [ -f "$SCRIPT_DIR/../../.venv/bin/activate" ]; then
    echo "Using project root virtual environment"
    source "$SCRIPT_DIR/../../.venv/bin/activate"
elif [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

# Switch to script directory
cd "$SCRIPT_DIR"

# Statistics variables
TOTAL=0
SUCCESS=0
FAILED=0

# Iterate over all subdirectories in test_data
for DATA_DIR in "$TEST_DATA_DIR"/*/; do
    DATA_NAME=$(basename "$DATA_DIR")
    IMAGE_PATH="$DATA_DIR/image_1.png"
    OUTPUT_BASE="$DATA_DIR/tvem_results"
    
    # Check if image exists
    if [ ! -f "$IMAGE_PATH" ]; then
        echo "⚠️  Skipping $DATA_NAME: image_1.png not found"
        continue
    fi
    
    TOTAL=$((TOTAL + 1))
    
    echo ""
    echo "=========================================="
    echo "📂 Processing: $DATA_NAME ($TOTAL)"
    echo "=========================================="
    echo "Input image: $IMAGE_PATH"
    echo "Output directory: $OUTPUT_BASE"
    
    # Create output directory
    mkdir -p "$OUTPUT_BASE"
    
    # Execute inference for 4 models
    (
        echo ""
        echo "  [1/4] 11 Diseases Detection..."
        python infer_with_json.py \
            --config configs/11diseases.yaml \
            --checkpoint weights/11diseases.pth \
            --image "$IMAGE_PATH" \
            --output-dir "$OUTPUT_BASE/11diseases" \
            --category-file categories/11diseases_category.json \
            --confidence $CONFIDENCE
        
        echo "  [2/4] 4 Quadrants Segmentation..."
        python infer_with_json.py \
            --config configs/4quadrants.yaml \
            --checkpoint weights/4quadrants.pth \
            --image "$IMAGE_PATH" \
            --output-dir "$OUTPUT_BASE/4quadrants" \
            --category-file categories/4quadrants_category.json \
            --confidence $CONFIDENCE
        
        echo "  [3/4] Mandibular Canal and Maxillary Sinus..."
        python infer_with_json.py \
            --config configs/mandibular_maxillary.yaml \
            --checkpoint weights/mandibular_maxillary.pth \
            --image "$IMAGE_PATH" \
            --output-dir "$OUTPUT_BASE/mandibular_maxillary" \
            --category-file categories/mandibular_maxillary_category.json \
            --confidence $CONFIDENCE
        
        echo "  [4/4] Bone Loss Detection..."
        python infer_with_json.py \
            --config configs/bone_loss.yaml \
            --checkpoint weights/bone_loss.pth \
            --image "$IMAGE_PATH" \
            --output-dir "$OUTPUT_BASE/bone_loss" \
            --category-file categories/bone_loss_category.json \
            --confidence $CONFIDENCE
    ) && {
        # Generate summary JSON
        python - "$OUTPUT_BASE" << 'PYTHON_SCRIPT'
import json
import sys
from pathlib import Path

results_dir = Path(sys.argv[1])
all_results = {}

for json_file in results_dir.glob("*/*_results.json"):
    model_name = json_file.parent.name
    with open(json_file, 'r') as f:
        data = json.load(f)
    all_results[model_name] = {
        "total_detections": data["total_detections"],
        "category_counts": data["category_counts"]
    }

with open(results_dir / "summary.json", 'w') as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)

print(f"  ✅ Summary results saved: {results_dir}/summary.json")
PYTHON_SCRIPT
        
        SUCCESS=$((SUCCESS + 1))
        echo "  ✅ $DATA_NAME completed"
    } || {
        FAILED=$((FAILED + 1))
        echo "  ❌ $DATA_NAME failed"
    }
done

echo ""
echo "=========================================="
echo "📊 Batch Processing Completed"
echo "=========================================="
echo "Total: $TOTAL"
echo "Success: $SUCCESS"
echo "Failed: $FAILED"
echo ""

