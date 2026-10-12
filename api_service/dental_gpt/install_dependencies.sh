#!/bin/bash

# DentalGPT API Server Dependency Installation Script
# Installs all required dependencies in conda environment zl_dentalGPT

echo "================================="
echo "DentalGPT API Dependency Installation Script"
echo "================================="

# Activate conda environment
echo ""
echo "Activating conda environment: zl_dentalGPT"
source $(conda info --base)/etc/profile.d/conda.sh
conda activate zl_dentalGPT

# Check if activated successfully
if [[ $CONDA_DEFAULT_ENV != "zl_dentalGPT" ]]; then
    echo "Error: Unable to activate conda environment zl_dentalGPT"
    echo "Please ensure the environment exists. Check with:"
    echo "  conda env list"
    exit 1
fi

echo "✓ Conda environment activated: $CONDA_DEFAULT_ENV"

# Display Python version
echo ""
echo "Python Version:"
python --version

# Install dependencies
echo ""
echo "Installing dependency packages..."
echo "================================="

pip install fastapi==0.109.0
pip install "uvicorn[standard]==0.27.0"
pip install python-multipart==0.0.6

echo ""
echo "================================="
echo "✓ Dependencies installed successfully!"
echo ""
echo "Note: The following packages should already be installed in your environment:"
echo "  - torch"
echo "  - transformers"
echo "  - qwen-vl-utils"
echo "  - Pillow"
echo ""
echo "If missing, install them manually:"
echo "  pip install torch transformers qwen-vl-utils Pillow"
echo ""
echo "You can now start the server:"
echo "  ./start_server.sh"
echo "================================="

