# 🦷 Teeth Visual Experts Models (TVEM)

MaskDINO-based dental disease detection and segmentation model collection.

## 📋 Available Models

### MaskDINO Segmentation Models (4 models)

| Model | Config File | Weight File | Purpose |
|------|---------|---------|------|
| **11 Diseases Detection** | `configs/11diseases.yaml` | `weights/11diseases.pth` | Caries, filling, impaction, periapical lesion, deep caries, retained root, implant, crown, residual crown, pontic, denture |
| **4 Quadrants Segmentation** | `configs/4quadrants.yaml` | `weights/4quadrants.pth` | Upper right, upper left, lower left, lower right quadrants |
| **Anatomical Structures** | `configs/mandibular_maxillary.yaml` | `weights/mandibular_maxillary.pth` | Mandibular canal, maxillary sinus |
| **Bone Loss** | `configs/bone_loss.yaml` | `weights/bone_loss.pth` | Alveolar bone loss detection |

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Install dependencies (first-time setup)
bash setup_maskdino_only.sh
```

This will:
- Create virtual environment (`.venv`)
- Clone MaskDINO repository
- Install all required Python dependencies

### 2. Run Inference

**Batch inference on all models (Recommended):**

```bash
bash infer_all_with_json.sh examples/sample.jpg
```

This will run all 4 models and generate:
- Visualized images and JSON results for each model
- Summary file `results/summary.json`

**Single Model:**

```bash
source .venv/bin/activate

# 11 Diseases Detection
uv run python infer_with_json.py \
  --config configs/11diseases.yaml \
  --checkpoint weights/11diseases.pth \
  --image examples/sample.jpg \
  --output-dir ./results \
  --category-file categories/11diseases_category.json \
  --confidence 0.3
```

### 3. View Results

```bash
# View all results
ls -lh results/*/

# View summary
cat results/summary.json
```

Output files:
- `{model}/sample_visualization.jpg` - Visualization image (outline only)
- `{model}/sample_results.json` - Detailed detection results
- `summary.json` - Aggregated results across all models

## 📊 Output Format

### JSON Structure Example

```json
{
  "image": "sample.jpg",
  "timestamp": "2026-01-07T18:00:00",
  "confidence_threshold": 0.3,
  "total_detections": 11,
  "category_counts": {
    "Filling": 7,
    "Crown": 2,
    "Pontic": 1,
    "Impacted": 1
  },
  "detections": [
    {
      "id": 1,
      "category_id": 2,
      "category_name": "Filling",
      "confidence": 0.825,
      "bbox": {"x": 100, "y": 200, "width": 50, "height": 60},
      "mask_area": 2057,
      "mask_shape": [976, 1976]
    }
  ]
}
```

### Summary File (summary.json)

```json
{
  "11diseases": {
    "total_detections": 11,
    "category_counts": {
      "Filling": 7,
      "Crown": 2,
      "Pontic": 1,
      "Impacted": 1
    }
  },
  "4quadrants": {
    "total_detections": 4,
    "category_counts": {
      "Upper Left": 1,
      "Upper Right": 1,
      "Lower Left": 1,
      "Lower Right": 1
    }
  },
  "mandibular_maxillary": {
    "total_detections": 4,
    "category_counts": {
      "Mandibular Canal": 2,
      "Maxillary Sinus": 2
    }
  },
  "bone_loss": {
    "total_detections": 2,
    "category_counts": {
      "Bone Loss": 2
    }
  }
}
```

## ⚙️ Parameter Description

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--config` | Model configuration file | Required |
| `--checkpoint` | Model checkpoint weight file | Required |
| `--image` | Input image path | Required |
| `--output-dir` | Output directory | `./results` |
| `--category-file` | Category mapping file | Optional |
| `--confidence` | Confidence threshold | 0.3 |
| `--device` | Compute device | `cuda` |

### Confidence Threshold Recommendations

- **0.3-0.4**: Balanced mode (recommended) - comprehensive detection
- **0.5-0.6**: Strict mode - high-confidence results only
- **0.2-0.3**: Loose mode - capture more potential detections

## 📁 File Structure

```
TVEM/
├── README.md                          # This document
├── setup_maskdino_only.sh            # Environment setup script
├── infer_with_json.py                # Single model inference script (outline visualization)
├── infer_all_with_json.sh            # Batch inference script
├── create_category_files.py          # Category file generator
│
├── configs/                           # Configuration files
│   ├── 11diseases.yaml
│   ├── 4quadrants.yaml
│   ├── mandibular_maxillary.yaml
│   └── bone_loss.yaml
│
├── weights/                           # Model weights (~10GB)
│   ├── 11diseases.pth
│   ├── 4quadrants.pth
│   ├── mandibular_maxillary.pth
│   └── bone_loss.pth
│
├── categories/                        # Category mappings
│   ├── 11diseases_category.json
│   ├── 4quadrants_category.json
│   ├── mandibular_maxillary_category.json
│   └── bone_loss_category.json
│
├── examples/                          # Sample files
│   └── sample.jpg
│
└── MaskDINO/                         # MaskDINO framework (auto-cloned)
```

## 📝 File Naming Reference Table

To simplify usage, functional shorthand names are used:

### Configuration Files (configs/)

| Shorthand Name | Original Name | Function |
|----------------|---------------|----------|
| `11diseases.yaml` | `maskdino_SwinL_bs16_50ep_4s_dowsample1_2048_x-ray_11diseases.yaml` | 11 dental disease detection |
| `4quadrants.yaml` | `maskdino_SwinL_bs16_50ep_4s_dowsample1_2048_panoramic_x-ray_4quadrants.yaml` | 4-quadrant segmentation |
| `mandibular_maxillary.yaml` | `maskdino_Swinl_bs16_50ep_4s_dowsample1_2048_panoramic_x-ray_Mandibular_Canal_Maxillary_Sinus.yaml` | Mandibular canal and maxillary sinus |
| `bone_loss.yaml` | `maskdino_SwinL_bs16_50ep_4s_dowsample1_2048_x-ray_bone_loss_1diseases.yaml` | Alveolar bone loss detection |

### Model Weights (weights/)

| Shorthand Name | Original Name | Size |
|----------------|---------------|------|
| `11diseases.pth` | `Teeth_Visual_Experts_Maskdino_Swinl_x-ray_11diseases.pth` | ~2.5GB |
| `4quadrants.pth` | `Teeth_Visual_Experts_Maskdino_Swinl_panoramic_x-ray_4quadrants.pth` | ~2.5GB |
| `mandibular_maxillary.pth` | `Teeth_Visual_Experts_Maskdino_Swinl_panoramic_x-ray_Mandibular_Canal_Maxillary_Sinus.pth` | ~2.5GB |
| `bone_loss.pth` | `Teeth_Visual_Experts_Maskdino_Swinl_x-ray_bone_loss_1disease.pth` | ~2.5GB |

## ✨ Key Features

### 1. Outline Visualization
- ✅ Displays outline borders only for masks (no semi-transparent fill)
- ✅ Displays category names (rather than category_ids)
- ✅ Custom visualizer `OutlineOnlyVisualizer`

### 2. JSON Output
- ✅ Detailed detection information (bounding boxes, mask areas, confidences)
- ✅ Category statistics
- ✅ Automatic aggregation across all models

### 3. Confidence Filtering
- ✅ Configurable confidence thresholds
- ✅ Filters low-quality detections
- ✅ Summary statistics based on filtered results

## 🔧 Troubleshooting

### 1. Dependency Errors

```bash
# Reinstall key dependencies
cd MaskDINO
uv pip install timm==0.6.13 numpy==1.26.4
uv pip install 'git+https://github.com/facebookresearch/detectron2.git'
```

### 2. CUDA Out of Memory

- Terminate other GPU processes
- Reduce input image dimensions
- Run in CPU mode: `--device cpu`

### 3. Config Path Errors

If encountering `_BASE_` path errors, verify that YAML paths point to `../MaskDINO/...`:

```yaml
_BASE_: ../MaskDINO/configs/coco/instance-segmentation/Base-COCO-InstanceSegmentation.yaml
```

### 4. Missing Category Mapping Files

```bash
# Regenerate category files
source .venv/bin/activate
python create_category_files.py
```

## 💡 Usage Examples

### Example 1: Batch Detection

```bash
# Run all models on a single image
bash infer_all_with_json.sh patient001.jpg

# View summary results
cat results/summary.json
```

### Example 2: Single Model - 11 Diseases Detection

```bash
source .venv/bin/activate

uv run python infer_with_json.py \
  --config configs/11diseases.yaml \
  --checkpoint weights/11diseases.pth \
  --image patient_panoramic.jpg \
  --output-dir ./results/patient001 \
  --category-file categories/11diseases_category.json \
  --confidence 0.3
```

### Example 3: Quadrant Segmentation (High Confidence)

```bash
source .venv/bin/activate

uv run python infer_with_json.py \
  --config configs/4quadrants.yaml \
  --checkpoint weights/4quadrants.pth \
  --image patient_panoramic.jpg \
  --output-dir ./results/quadrants \
  --category-file categories/4quadrants_category.json \
  --confidence 0.5
```

## 📚 References

- **Original Project**: [OralGPT](https://github.com/isbrycee/OralGPT)
- **Model Repository**: [HuggingFace - Teeth_Visual_Experts_Models](https://huggingface.co/Bryceee/Teeth_Visual_Experts_Models)
- **MaskDINO**: [IDEA-Research/MaskDINO](https://github.com/IDEA-Research/MaskDINO)
- **Detectron2**: [facebookresearch/detectron2](https://github.com/facebookresearch/detectron2)

## 📄 License

Subject to original model licenses. Intended for research and educational purposes.

## 🙏 Acknowledgements

- Pretrained models provided by the OralGPT team
- MaskDINO framework by IDEA Research
- Detectron2 by Facebook Research

---

**Version**: 2.0  
**Last Updated**: 2026-01-07  
**Main Improvements**:
- ✨ File structure reorganized (configs/, weights/, categories/)
- ✨ Simplified file naming
- ✨ Outline-only mask visualization
- ✨ Automatic summary output
