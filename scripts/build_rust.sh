#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🦀 Building SomaBrain Rust Core...${NC}"

# Check for Python virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${RED}Error: No virtual environment active. Please activate your venv first.${NC}"
    exit 1
fi

# Install maturin if missing
if ! python3 -c "import maturin" &> /dev/null; then
    echo -e "${GREEN}📦 Installing maturin...${NC}"
    python3 -m pip install maturin
fi

# Build
cd rust_core
echo -e "${GREEN}🔨 Compiling (release mode)...${NC}"
maturin develop --release

echo -e "${GREEN}✅ Build complete! SomaBrain Rust core is ready.${NC}"
