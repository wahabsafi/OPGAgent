# DentalGPT REST API Documentation

## 📋 Table of Contents
- [Introduction](#introduction)
- [Environment Requirements](#environment-requirements)
- [Installation Steps](#installation-steps)
- [Starting the Service](#starting-the-service)
- [API Endpoints](#api-endpoints)
- [Client Calls](#client-calls)
- [Frequently Asked Questions](#frequently-asked-questions)

---

## Introduction

DentalGPT REST API provides a FastAPI-based web service to run dental image analysis using the DentalGPT model over local network or localhost.

**Key Features:**
- ✅ Supports image file upload
- ✅ Supports Base64 encoded images
- ✅ Automatic GPU acceleration (if available)
- ✅ Local network access support
- ✅ Full API documentation (Swagger UI)
- ✅ Health check endpoints

---

## Environment Requirements

### Server Side
- **OS**: Linux (Ubuntu 20.04+ recommended)
- **Python**: 3.9+
- **GPU**: NVIDIA GPU with CUDA support (Recommended)
- **VRAM**: ≥16GB
- **RAM**: ≥32GB

### Client Side
- **Python**: 3.7+
- **Network**: Network access to the host server

---

## Installation Steps

### 1. Install Dependencies

Install the required Python packages:

```bash
cd /path/to/dentalGPT
pip install -r requirements.txt
```

If you already have `transformers`, `torch`, etc., you can install only the FastAPI-related dependencies:

```bash
pip install fastapi uvicorn[standard] python-multipart
```

### 2. Verify Model Path

Ensure the model path in `api_server.py` (or environment variable `DENTAL_GPT_MODEL_PATH`) is set properly.

---

## Starting the Service

### Method 1: Using the Startup Script (Recommended)

```bash
./start_api.sh
```

### Method 2: Running via Python Directly

```bash
python api_server.py
```

### Method 3: Using uvicorn

```bash
# Basic start
uvicorn api_server:app --host 0.0.0.0 --port 8566

# Production (with workers)
uvicorn api_server:app --host 0.0.0.0 --port 8566 --workers 1

# Development (reload mode)
uvicorn api_server:app --host 0.0.0.0 --port 8566 --reload
```

### Startup Success Indicators

When you see the following log lines, the service has initialized:

```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO - Starting DentalGPT API service...
INFO - Loading processor...
INFO - Processor loaded successfully
INFO - Loading DentalGPT model...
INFO - Model loaded successfully
INFO - Service startup completed
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8566 (Press CTRL+C to quit)
```

---

## API Endpoints

### 1. Root Path - GET `/`

Returns basic API service info.

**Request:**
```bash
curl http://localhost:8566/
```

**Response:**
```json
{
  "service": "DentalGPT API",
  "version": "1.0.0",
  "status": "running",
  "endpoints": {
    "health": "/health",
    "analyze": "/analyze (POST)",
    "analyze_base64": "/analyze/base64 (POST)"
  }
}
```

### 2. Health Check - GET `/health`

Checks service status and model load status.

**Request:**
```bash
curl http://localhost:8566/health
```

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "device": "cuda",
  "timestamp": "2026-10-12T10:30:00.123456"
}
```

### 3. Image Analysis (File Upload) - POST `/analyze`

Upload an image file for analysis.

**Parameters:**
- `image` (Required): Image file
- `question` (Optional): Query to ask about the image
- `max_new_tokens` (Optional): Maximum generated tokens, default 4096

**Request Example (curl):**
```bash
curl -X POST http://localhost:8566/analyze \
  -F "image=@/path/to/dental_image.jpg" \
  -F "question=Please analyze the teeth in this image using FDI notation."
```

**Request Example (Python):**
```python
import requests

files = {'image': open('dental_image.jpg', 'rb')}
data = {'question': 'Please analyze the teeth with issues in this image.'}

response = requests.post(
    'http://localhost:8566/analyze',
    files=files,
    data=data
)
print(response.json())
```

**Response:**
```json
{
  "success": true,
  "question": "Please analyze the teeth with issues in this image.",
  "answer": "Based on the image analysis, the following issues were found...",
  "timestamp": "2026-10-12T10:30:00.123456"
}
```

### 4. Image Analysis (Base64) - POST `/analyze/base64`

Analyze using a Base64 encoded image string.

**Parameters:**
- `image_base64` (Required): Base64 encoded image string
- `question` (Optional): Query to ask
- `max_new_tokens` (Optional): Maximum generated tokens, default 4096

**Request Example (Python):**
```python
import requests
import base64

with open('dental_image.jpg', 'rb') as f:
    image_base64 = base64.b64encode(f.read()).decode('utf-8')

data = {
    'image_base64': image_base64,
    'question': 'Please analyze teeth with issues in this image.'
}

response = requests.post(
    'http://localhost:8566/analyze/base64',
    data=data
)
print(response.json())
```

### 5. API Documentation - GET `/docs`

Interactive Swagger UI documentation at:
```
http://localhost:8566/docs
```

---

## Client Calls

### Method 1: Using curl

```bash
# Health check
curl http://localhost:8566/health

# Analyze image
curl -X POST http://localhost:8566/analyze \
  -F "image=@dental_image.jpg" \
  -F "question=Please analyze this dental image."
```

### Method 2: Using Python requests

```python
import requests

# Health check
response = requests.get('http://localhost:8566/health')
print(response.json())

# Analyze image
files = {'image': open('dental_image.jpg', 'rb')}
data = {'question': 'Please analyze this dental image.'}
response = requests.post(
    'http://localhost:8566/analyze',
    files=files,
    data=data
)
print(response.json())
```

---

## Frequently Asked Questions

### Q1: Cannot connect to server
1. Verify the server is running.
2. Check IP address and port.
3. Check firewall rules:
   ```bash
   sudo ufw allow 8566/tcp
   ```

### Q2: Model failed to load
- Verify model path or HF cache exists.
- Check GPU memory with `nvidia-smi`.
- Check dependencies: `pip install -r requirements.txt`.

### Q3: Inference is slow
- Ensure GPU is utilized: check `device` field in `/health`.
- Reduce `max_new_tokens`.
- Check if other processes are utilizing GPU resources.

---

## File Overview

- `api_server.py` - FastAPI server implementation
- `start_api.sh` - Startup script
- `start_all_replicas.sh` - Script to start multiple replicas
- `stop_all_replicas.sh` - Script to stop replicas
- `API_README.md` - This documentation

---

**Version**: 1.0.0  
**Author**: DentalGPT Team
