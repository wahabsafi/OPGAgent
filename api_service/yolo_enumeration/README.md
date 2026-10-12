# Tooth Enumeration Detection Tool

Tooth enumeration detection tool - using YOLOv9c model to recognize 8 tooth types in panoramic dental radiographs.

## Model Information

- **Architecture**: YOLOv9c
- **Detection Classes**: 8 tooth types (labeled 1-8)
  - 1 (Central incisor)
  - 2 (Lateral incisor)
  - 3 (Canine)
  - 4 (First premolar)
  - 5 (Second premolar)
  - 6 (First molar)
  - 7 (Second molar)
  - 8 (Third molar / Wisdom tooth)
- **Input Size**: 640x640
- **Training Data**: 634 images, 18,095 annotations

## Installation

### Using uv (Recommended)
```bash
# Install uv (if not already installed)
pip install uv

# Sync dependencies
uv sync
```

### Using pip
```bash
pip install -r requirements.txt
```

## Usage

### 1. Local Prediction (Without API Service)

```bash
# Single image detection
python predict.py --image path/to/xray.png

# Batch detection
python predict.py --dir path/to/images/

# Custom parameters
python predict.py --image xray.png --conf 0.3 --iou 0.5 --output results/

# Do not save results (display only)
python predict.py --image xray.png --no-save
```

### 2. API Service Mode

#### Start Service
```bash
# Using startup script (recommended)
bash start_api.sh

# Or directly with uvicorn
uvicorn api_server:app --host 0.0.0.0 --port 8001

# Using uv run
uv run uvicorn api_server:app --host 0.0.0.0 --port 8001
```

#### Using Python Client
```python
from api_client import ToothEnumerationClient

# Create client
client = ToothEnumerationClient("http://localhost:8001")

# Detect image
result = client.detect_from_file("xray.png", conf_threshold=0.25)
print(result)

# Formatted output
formatted = client.format_result(result)
print(formatted)
```

#### Using Agent Functions
```python
from api_client import detect_tooth_enumeration, get_tooth_enumeration_summary

# Detect and get formatted text
result_text = detect_tooth_enumeration("xray.png")
print(result_text)

# Get statistical summary
summary = get_tooth_enumeration_summary("xray.png")
print(f"Detected {summary['total_teeth']} teeth")
print(f"Count by type: {summary['tooth_count_by_type']}")
```

#### Command Line Client
```bash
# Detect single image
python api_client.py xray.png

# Custom parameters
python api_client.py xray.png --url http://localhost:8001 --conf 0.3 --save
```

### 3. API Endpoints

- `POST /detect` - Upload image file for detection
- `POST /detect_base64` - Detect using Base64 encoded image
- `GET /health` - Health check
- `GET /model/info` - Get model info

## Output Format

### Detection Result Format
```json
{
  "success": true,
  "num_detections": 15,
  "detections": [
    {
      "class_id": 0,
      "class_name": "1",
      "confidence": 0.89,
      "bbox": [100, 200, 150, 250]
    }
  ]
}
```

### Statistical Summary Format
```json
{
  "success": true,
  "total_teeth": 15,
  "tooth_count_by_type": {
    "1": 2,
    "2": 2,
    "3": 2,
    "6": 4
  },
  "num_detections": 15
}
```

## Deployment to Other Environments

1. **Copy Required Files**
```bash
# Package tool
tar -czf enumeration_tool.tar.gz enumeration_tool/

# Extract in target environment
tar -xzf enumeration_tool.tar.gz
cd enumeration_tool
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
# Or using uv sync
```

3. **Ensure Model File Exists**
   - Check if `model/best.pt` exists
   - If not, copy from training directory: `cp ../yolov9_enumeration/runs/detect/tooth_enumeration_yolov9c_*/weights/best.pt model/`

4. **Start Service**
```bash
bash start_api.sh
```

## MCP Tool Integration

This tool provides Model Context Protocol (MCP) tool definitions for environments supporting MCP:

- `detect_tooth_enumeration` - Detect tooth enumeration
- `get_tooth_enumeration_summary` - Get statistical summary

See `mcp_tools.json` for tool definitions.

## Performance

- **Inference Speed**: ~30ms/image (NVIDIA GPU)
- **Memory Footprint**: ~1GB (including model weights)
- **Accuracy**: Dependent on training results, see training logs for details

## Environment Variables

```bash
# API service configuration
export HOST=0.0.0.0        # Default: 0.0.0.0
export PORT=8001           # Default: 8001
export WORKERS=1           # Default: 1
```

## Troubleshooting

1. **Model File Not Found**
   - Ensure `model/best.pt` exists
   - Copy model file from training directory

2. **Port in Use**
   - Change `PORT` environment variable
   - Check if port 8001 is in use: `lsof -i :8001`

3. **Dependency Issues**
   - Reinstall with `pip install -r requirements.txt`
   - Or sync dependencies with `uv sync`

## License

MIT
