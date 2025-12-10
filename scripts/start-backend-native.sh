#!/bin/bash
# =======================================================================
# i3T4AN (Ethan Blair)
# Project:      Vector Knowledge Base
# File:         Native backend startup script (Unix/macOS)
# =======================================================================

# Exit on error
set -e

echo "=== Vector Knowledge Base - Native Backend Startup ==="
echo ""

# Configuration
VENV_DIR="venv"
BACKEND_DIR="backend"
PORT=8000

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker services are running
echo "Checking Docker services..."
if ! docker ps | grep -q vkb-qdrant; then
    echo -e "${YELLOW}WARNING: Qdrant container not running.${NC}"
    echo "Starting Qdrant and Frontend containers..."
    docker-compose up -d qdrant frontend
    echo "Waiting for Qdrant to be ready..."
    sleep 5
else
    echo -e "${GREEN}✓ Qdrant container is running${NC}"
fi

# Check Python version
PYTHON_CMD=""
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo -e "${RED}ERROR: Python 3 not found. Please install Python 3.11+${NC}"
    exit 1
fi

echo "Using Python: $PYTHON_CMD ($($PYTHON_CMD --version))"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv $VENV_DIR
fi

# Activate virtual environment
echo "Activating virtual environment..."
source $VENV_DIR/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Check GPU availability
echo ""
echo "Detecting compute device..."
python3 -c "
import torch
if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
    print('  GPU: Apple MPS (Metal Performance Shaders) ✓')
elif torch.cuda.is_available():
    print(f'  GPU: CUDA ({torch.cuda.get_device_name(0)}) ✓')
else:
    print('  GPU: Not available, using CPU')
print(f'  PyTorch version: {torch.__version__}')
"

# Set environment variables for native mode
export QDRANT_HOST="localhost"
export QDRANT_PORT="6333"

echo ""
echo -e "${GREEN}Starting backend server on http://localhost:$PORT${NC}"
echo "Press Ctrl+C to stop"

# Display MCP status
echo ""
echo "MCP Server Configuration:"
if [ "${MCP_ENABLED:-true}" = "true" ]; then
    echo -e "  ${GREEN}MCP Endpoint: http://localhost:$PORT${MCP_PATH:-/mcp}${NC}"
    echo "  Connect Claude Desktop or other MCP clients to this URL"
else
    echo -e "  ${YELLOW}MCP Server: Disabled${NC}"
fi
echo ""

# Change to backend directory and start
cd $BACKEND_DIR
uvicorn main:app --host 0.0.0.0 --port $PORT --reload
