#!/bin/bash
# =============================================================================
# Setup isolated virtual environments for all OPGAgent backend API services
# Uses `uv` to manage environments and dependencies.
# =============================================================================

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}  Setting up Virtual Environments for All API Services${NC}"
echo -e "${CYAN}============================================================${NC}"

# Check for uv
if ! command -v uv > /dev/null 2>&1; then
    echo -e "${RED}Error: 'uv' is not installed.${NC}"
    echo "Please install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

if [ -n "$MIRROR" ]; then
    export UV_DEFAULT_INDEX="$MIRROR"
elif [ -n "$PIP_INDEX_URL" ] && [ -z "$UV_DEFAULT_INDEX" ]; then
    export UV_DEFAULT_INDEX="$PIP_INDEX_URL"
fi

if [ -n "$UV_DEFAULT_INDEX" ]; then
    echo -e "Using PyPI mirror: ${YELLOW}$UV_DEFAULT_INDEX${NC}"
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
echo -e "Using Python interpreter: ${YELLOW}$PYTHON_BIN${NC}"
echo ""

create_venv() {
    local target_dir=$1
    cd "$target_dir"
    if [ ! -d ".venv" ]; then
        uv venv --python "$PYTHON_BIN" .venv
    fi
}

# 1. YOLO Enumeration
echo -e "${GREEN}[1/5] Setting up yolo_enumeration environment...${NC}"
cd "$SCRIPT_DIR/yolo_enumeration"
if [ -f "pyproject.toml" ]; then
    uv sync
else
    create_venv "$SCRIPT_DIR/yolo_enumeration"
    uv pip install -r requirements.txt
fi
echo -e "${GREEN}✓ yolo_enumeration environment ready${NC}\n"

# 2. TVEM (MaskDINO)
echo -e "${GREEN}[2/5] Setting up tvem environment...${NC}"
create_venv "$SCRIPT_DIR/tvem"
VIRTUAL_ENV="$SCRIPT_DIR/tvem/.venv" uv pip install -r requirements-uv.txt
echo -e "${GREEN}✓ tvem environment ready${NC}\n"

# 3. MedSAM
echo -e "${GREEN}[3/5] Setting up medsam environment...${NC}"
create_venv "$SCRIPT_DIR/medsam"
VIRTUAL_ENV="$SCRIPT_DIR/medsam/.venv" uv pip install -r requirements.txt
echo -e "${GREEN}✓ medsam environment ready${NC}\n"

# 4. OralGPT
echo -e "${GREEN}[4/5] Setting up oral_gpt environment...${NC}"
create_venv "$SCRIPT_DIR/oral_gpt"
VIRTUAL_ENV="$SCRIPT_DIR/oral_gpt/.venv" uv pip install -r requirements-uv.txt
echo -e "${GREEN}✓ oral_gpt environment ready${NC}\n"

# 5. DentalGPT
echo -e "${GREEN}[5/5] Setting up dental_gpt environment...${NC}"
create_venv "$SCRIPT_DIR/dental_gpt"
VIRTUAL_ENV="$SCRIPT_DIR/dental_gpt/.venv" uv pip install -r requirements-uv.txt
echo -e "${GREEN}✓ dental_gpt environment ready${NC}\n"

cd "$SCRIPT_DIR"
echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}  All API service environments have been created successfully!${NC}"
echo -e "${CYAN}============================================================${NC}"
