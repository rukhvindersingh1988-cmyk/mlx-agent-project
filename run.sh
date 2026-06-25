#!/bin/bash
set -e

# Change directory to the script's directory
cd "$(dirname "$0")"

echo "=== MLX Local Agent Bootstrap ==="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install it first."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment in .venv..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing required Python packages..."
# mlx-lm: Apple Silicon MLX framework for LLMs
# fastapi, uvicorn: backend web framework and server
# websockets: real-time streaming communication
# duckduckgo-search: web searching capabilities
# beautifulsoup4, httpx: web scraping capabilities
# markdown: formatting helpers
# pywebview: native macOS desktop window wrapper
pip install mlx-lm fastapi uvicorn websockets duckduckgo-search beautifulsoup4 httpx markdown pywebview

echo "All dependencies installed successfully!"
echo "Starting Antigravity MLX Desktop App..."
python3 app.py
