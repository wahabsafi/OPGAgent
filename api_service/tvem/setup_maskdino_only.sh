#!/bin/bash

# Simplified installation - sets up MaskDINO only

set -e

WORK_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$WORK_DIR"

echo "=========================================="
echo "🦷 Setting up MaskDINO inference environment"
echo "=========================================="
echo ""

# Activate virtual environment
echo "📦 Activating virtual environment..."
source .venv/bin/activate
echo ""

# Clone MaskDINO
echo "📦 Cloning MaskDINO..."
if [ ! -d "MaskDINO" ]; then
    git clone https://github.com/IDEA-Research/MaskDINO.git
    echo "✅ MaskDINO clone completed"
else
    echo "✅ MaskDINO already exists"
fi
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
cd MaskDINO

echo "   Installing requirements..."
uv pip install numpy==2.2.6
uv pip install setuptools
uv pip install torch==2.9.1
echo "   Installing Detectron2..."
uv pip install 'git+https://github.com/facebookresearch/detectron2.git@fd27788985af0f4ca800bca563acdb700bb890e2' --no-build-isolation
uv pip install 'git+https://github.com/cocodataset/cocoapi.git@8c9bcc3cf640524c4c20a9c40e89cb6a2f2fa0e9#subdirectory=PythonAPI' --no-build-isolation
uv pip install 'git+https://github.com/cocodataset/panopticapi.git@7bb4655548f98f3fedc07bf37e9040a992b054b0'
uv pip install -r requirements.txt


echo "   Compiling MaskDINO CUDA ops..."
cd MaskDINO/maskdino/modeling/pixel_decoder/ops
sh make.sh
cd "$WORK_DIR"

echo ""
echo "=========================================="
echo "✅ MaskDINO environment setup completed!"
echo "=========================================="
echo ""
echo "📋 Available MaskDINO segmentation models (4):"
echo ""
echo "   1. 11 Diseases Segmentation"
echo "      configs/11diseases.yaml + weights/11diseases.pth"
echo ""
echo "   2. 4 Quadrants Segmentation"
echo "      configs/4quadrants.yaml + weights/4quadrants.pth"
echo ""
echo "   3. Mandibular Canal and Maxillary Sinus"
echo "      configs/mandibular_maxillary.yaml + weights/mandibular_maxillary.pth"
echo ""
echo "   4. Bone Loss"
echo "      configs/bone_loss.yaml + weights/bone_loss.pth"
echo ""
echo "🚀 Usage Examples:"
echo ""
echo "# Single model inference"
echo "uv run python infer_with_json.py \\"
echo "  --config configs/11diseases.yaml \\"
echo "  --checkpoint weights/11diseases.pth \\"
echo "  --image examples/sample.jpg \\"
echo "  --output-dir ./results \\"
echo "  --category-file categories/11diseases_category.json \\"
echo "  --confidence 0.3"
echo ""
echo "# Batch inference on all models"
echo "bash infer_all_with_json.sh examples/sample.jpg"
echo ""
echo "=========================================="

