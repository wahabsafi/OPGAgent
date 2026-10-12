# Agent_v3 API Services

This directory contains all the tool API services used by Agent_v3 / OPGAgent.

## Port Allocation

| Service | Port | GPU | Description |
|------|------|-----|------|
| yolo_enumeration | 6600 | Configurable | Tooth enumeration detection |
| tvem | 6602 | Configurable | MaskDINO multi-model detection |
| medsam | 6603 | Configurable | MedSAM medical image segmentation |
| oral_gpt | 6604-6607 | 0-3 | OralGPT-Omni VLM (4 replicas) |
| dental_gpt | 6608-6611 | 0-3 | DentalGPT VLM (4 replicas) |

## Quick Start

### Test Environment (GPU 0-3)

```bash
# Start all services (test environment)
bash start_all_services.sh

# Stop all services
bash stop_all_services.sh
```

### Starting Services Individually

```bash
# YOLO tooth enumeration detection
cd yolo_enumeration && bash start_api.sh

# TVEM MaskDINO
cd tvem && bash start_api.sh

# MedSAM
cd medsam && bash start_api.sh

# OralGPT (Single replica)
cd oral_gpt && bash start_api.sh

# OralGPT (All 4 replicas)
cd oral_gpt && bash start_all_replicas.sh

# DentalGPT (Single replica)
cd dental_gpt && bash start_api.sh

# DentalGPT (All 4 replicas)
cd dental_gpt && bash start_all_replicas.sh
```

### Specifying Port and GPU

All services support configuring port and GPU via environment variables:

```bash
# Specify both port and GPU
PORT=6700 GPU=1 bash start_api.sh

# Specify GPU only
GPU=2 bash start_api.sh
```

## Service Details

### 1. YOLO Tooth Enumeration Detection (yolo_enumeration)
- **Port**: 6600
- **Function**: Identifies tooth numbers (1-8) in dental panoramic radiographs
- **Virtual Environment**: Isolated `uv` venv
- **API Documentation**: http://localhost:6600/docs
- **Key Endpoints**:
  - `POST /detect` - Detect image
  - `GET /health` - Health check
  - `POST /load_model` - Load model
  - `POST /unload_model` - Unload model

### 2. TVEM MaskDINO (tvem)
- **Port**: 6602
- **Function**: High-precision dental image segmentation, supporting multiple detection tasks
- **Virtual Environment**: Isolated `uv` venv
- **API Documentation**: http://localhost:6602/docs
- **Supported Models**:
  - `4quadrants` - 4-quadrant segmentation
  - `11diseases` - 11 dental disease categories detection
  - `bone_loss` - Alveolar bone loss detection
  - `mandibular_maxillary` - Mandibular canal and maxillary sinus detection
- **Key Endpoints**:
  - `POST /detect/{model}` - Detect with specified model
  - `GET /models` - List available models
  - `GET /health` - Health check
  - `POST /load/{model}` - Load specified model
  - `POST /unload/{model}` - Unload specified model

### 3. MedSAM (medsam)
- **Port**: 6603
- **Function**: Medical image segmentation, precise segmentation guided by bounding boxes
- **Virtual Environment**: `./medsam/.venv`
- **API Documentation**: http://localhost:6603/docs
- **Key Endpoints**:
  - `POST /segment` - Segment image
  - `GET /health` - Health check

### 4. OralGPT-Omni (oral_gpt)
- **Port**: 6604-6607 (4 replicas)
- **Function**: Multimodal dental diagnostic vision-language model
- **Virtual Environment**: Isolated `uv` venv
- **API Documentation**: http://localhost:6604/docs
- **Load Balancing**: Round-robin strategy
- **Key Endpoints**:
  - `POST /analyze` - Analyze image
  - `GET /health` - Health check

### 5. DentalGPT (dental_gpt)
- **Port**: 6608-6611 (4 replicas)
- **Function**: Specialized dental VLM analysis model
- **Virtual Environment**: Isolated `uv` venv
- **API Documentation**: http://localhost:6608/docs
- **Load Balancing**: Round-robin strategy
- **Key Endpoints**:
  - `POST /analyze` - Analyze image
  - `GET /health` - Health check
  - `POST /load_model` - Load model
  - `POST /unload_model` - Unload model

## GPU Allocation Recommendations

### Testing Environment (4 GPUs)

For testing across GPU 0-3:

| GPU | Services | Estimated VRAM |
|-----|----------|----------------|
| 0 | yolo_enumeration + oral_gpt_0 | ~14GB |
| 1 | oral_gpt_1 | ~12GB |
| 2 | tvem + oral_gpt_2 | ~20GB |
| 3 | medsam + oral_gpt_3 | ~16GB |

Or dedicated to VLMs:

| GPU | Services | Estimated VRAM |
|-----|----------|----------------|
| 0 | oral_gpt_0 + dental_gpt_0 | ~24GB |
| 1 | oral_gpt_1 + dental_gpt_1 | ~24GB |
| 2 | oral_gpt_2 + dental_gpt_2 | ~24GB |
| 3 | oral_gpt_3 + dental_gpt_3 | ~24GB |

### Production Environment

Adjust configuration based on the available number of GPUs and VRAM.

## Health Checks

```bash
# Check status of all services
bash check_health.sh

# Manually check individual services
curl http://localhost:6600/health  # yolo_enumeration
curl http://localhost:6602/health  # tvem
curl http://localhost:6603/health  # medsam
curl http://localhost:6604/health  # oral_gpt replica 0
curl http://localhost:6608/health  # dental_gpt replica 0
```

## Logs

Logs for VLM services are stored under their respective `logs/` directories:
- `oral_gpt/logs/oral_gpt_replica_*.log`
- `dental_gpt/logs/dental_gpt_replica_*.log`

## Troubleshooting

1. **Port in use**: Check running processes using `lsof -i:<port_number>`
2. **Out of GPU Memory (OOM)**: Check GPU usage using `nvidia-smi`
3. **Model loading failure**: Check model file paths and permissions
4. **Virtual environment issues**: Ensure virtual environments exist and dependencies are installed

