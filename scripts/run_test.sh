#!/bin/bash
# Test OPGAgent / Agent_v3 script

set -e

# Change to project root directory
cd "$(dirname "$0")/.."

# Check if inside a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: No virtual environment detected. Recommended to activate virtual environment first."
    echo "You can run: uv sync"
fi

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Run test
python3 scripts/test_agent.py \
    --test_data_dir ../test_data \
    --output_dir runs/test \
    --question "Please analyze this OPG panoramic radiograph and generate a comprehensive diagnostic report." \
    --generate_report

echo "Test completed! Results saved to runs/test/ directory"

