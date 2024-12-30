#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up development environment...${NC}"

# Check for Python 3.8+
python3 --version | grep "Python 3.[89]" > /dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}Python 3.8+ is required${NC}"
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install required packages
echo "Installing system packages..."
sudo apt-get update
sudo apt-get install -y \
    python3-tflite-runtime \
    python3-coral \
    libedgetpu1-std \
    python3-dev \
    build-essential

# Install Python packages
echo "Installing Python packages..."
pip install --upgrade pip
pip install \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu \
    transformers \
    optimum-habana \
    fastapi \
    uvicorn \
    watchfiles \
    psutil \
    numpy \
    websockets \
    pytest \
    black \
    isort \
    mypy

# Add Redis and aiohttp to requirements
pip install redis aiohttp

# Create necessary directories
echo "Creating project directories..."
mkdir -p \
    models \
    backups \
    logs \
    src/templates \
    src/static \
    tests

# Download models
echo "Downloading and preparing models..."
python3 scripts/prepare_models.py

# Setup pre-commit hooks
echo "Setting up git hooks..."
cp scripts/pre-commit .git/hooks/
chmod +x .git/hooks/pre-commit

echo -e "${GREEN}Setup complete!${NC}" 