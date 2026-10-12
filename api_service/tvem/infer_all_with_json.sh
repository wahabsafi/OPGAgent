#!/bin/bash

# Batch inference on all MaskDINO models and generate JSON results
# Usage: bash infer_all_with_json.sh <image_path>

set -e

IMAGE_PATH="${1:-examples/sample.jpg}"
OUTPUT_BASE="./results"
CONFIDENCE=0.3

echo "🦷 Batch inference on all MaskDINO models (generating JSON results)"
echo "Input image: $IMAGE_PATH"
echo "Output directory: $OUTPUT_BASE"
echo "Confidence threshold: $CONFIDENCE"
echo ""

# Activate virtual environment
PROJECT_VENV="/data/zhaolin/tool_env/TVEM/.venv"
if [ -f "$PROJECT_VENV/bin/activate" ]; then
    echo "Using standalone virtual environment: $PROJECT_VENV"
    source "$PROJECT_VENV/bin/activate"
elif [ -f "../../.venv/bin/activate" ]; then
     echo "Using project root virtual environment"
    source "../../.venv/bin/activate"
elif [ -f ".venv/bin/activate" ]; then
    source ".venv/bin/activate"
fi

# Create output directory
mkdir -p "$OUTPUT_BASE"

echo "=========================================="
echo "1/4: 11 Diseases Detection"
echo "=========================================="
python infer_with_json.py \
  --config configs/11diseases.yaml \
  --checkpoint weights/11diseases.pth \
  --image "$IMAGE_PATH" \
  --output-dir "$OUTPUT_BASE/11diseases" \
  --category-file categories/11diseases_category.json \
  --confidence $CONFIDENCE

echo ""
echo "=========================================="
echo "2/4: 4 Quadrants Segmentation"
echo "=========================================="
python infer_with_json.py \
  --config configs/4quadrants.yaml \
  --checkpoint weights/4quadrants.pth \
  --image "$IMAGE_PATH" \
  --output-dir "$OUTPUT_BASE/4quadrants" \
  --category-file categories/4quadrants_category.json \
  --confidence $CONFIDENCE

echo ""
echo "=========================================="
echo "3/4: Mandibular Canal and Maxillary Sinus"
echo "=========================================="
python infer_with_json.py \
  --config configs/mandibular_maxillary.yaml \
  --checkpoint weights/mandibular_maxillary.pth \
  --image "$IMAGE_PATH" \
  --output-dir "$OUTPUT_BASE/mandibular_maxillary" \
  --category-file categories/mandibular_maxillary_category.json \
  --confidence $CONFIDENCE

echo ""
echo "=========================================="
echo "4/4: Bone Loss Detection"
echo "=========================================="
python infer_with_json.py \
  --config configs/bone_loss.yaml \
  --checkpoint weights/bone_loss.pth \
  --image "$IMAGE_PATH" \
  --output-dir "$OUTPUT_BASE/bone_loss" \
  --category-file categories/bone_loss_category.json \
  --confidence $CONFIDENCE

echo ""
echo "=========================================="
echo "✅ All inferences completed!"
echo "=========================================="
echo ""
echo "View results:"
echo "  Visualization images: ls -lh $OUTPUT_BASE/*/*.jpg"
echo "  JSON results:         ls -lh $OUTPUT_BASE/*/*.json"
echo ""
echo "Merging all results:"
cat << PYTHON > /tmp/merge_results_$$.py
import json
import glob
from pathlib import Path

results_dir = Path("$OUTPUT_BASE")
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

print(f"✅ Summary results saved: {results_dir}/summary.json")
PYTHON

python /tmp/merge_results_$$.py
rm /tmp/merge_results_$$.py

