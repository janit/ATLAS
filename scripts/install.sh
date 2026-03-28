#!/bin/bash
set -euo pipefail

#===========================================
# ATLAS Install (ROCm / Docker Compose)
#===========================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load config
if [ -f "$PROJECT_DIR/atlas.conf" ]; then
    source "$PROJECT_DIR/atlas.conf"
    info "Loaded atlas.conf"
else
    error "atlas.conf not found. Run: cp atlas.conf.example atlas.conf"
fi

MODELS_DIR="${ATLAS_MODELS_DIR:-/opt/atlas/models}"

#-------------------------------------------
# Pre-flight checks
#-------------------------------------------
info "Running pre-flight checks..."

# Docker
command -v docker >/dev/null 2>&1 || error "Docker not found. Install: https://docs.docker.com/engine/install/"
docker compose version >/dev/null 2>&1 || error "Docker Compose V2 not found."

# ROCm
if [ ! -d /dev/dri ]; then
    error "/dev/dri not found. ROCm drivers not installed."
fi
if [ ! -e /dev/kfd ]; then
    error "/dev/kfd not found. ROCm kernel driver (amdgpu) not loaded."
fi
info "ROCm devices found: /dev/kfd, /dev/dri"

# Check GPU access
if command -v rocm-smi >/dev/null 2>&1; then
    GPU_COUNT=$(rocm-smi --showid 2>/dev/null | grep -c "GPU" || echo "0")
    info "Detected $GPU_COUNT AMD GPU(s)"
else
    warn "rocm-smi not found on host. GPU detection skipped (will work inside container)."
fi

# Models
if [ ! -d "$MODELS_DIR" ]; then
    error "Models directory not found: $MODELS_DIR"
fi
if [ ! -f "$MODELS_DIR/Qwen3-14B-Q4_K_M.gguf" ]; then
    error "Main model not found: $MODELS_DIR/Qwen3-14B-Q4_K_M.gguf"
fi
if [ ! -f "$MODELS_DIR/Qwen3-0.6B-Q8_0.gguf" ]; then
    warn "Draft model not found: $MODELS_DIR/Qwen3-0.6B-Q8_0.gguf (spec decode disabled)"
fi
info "Models directory: $MODELS_DIR"

#-------------------------------------------
# Build and start
#-------------------------------------------
info "Building containers..."
cd "$PROJECT_DIR"
docker compose build

info "Starting services..."
docker compose up -d

info "Waiting for services to become healthy..."
TIMEOUT=300
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    HEALTHY=$(docker compose ps --format json 2>/dev/null | grep -c '"healthy"' || echo "0")
    TOTAL=$(docker compose ps --format json 2>/dev/null | wc -l || echo "0")
    if [ "$HEALTHY" -eq "$TOTAL" ] && [ "$TOTAL" -gt 0 ]; then
        break
    fi
    echo -n "."
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done
echo ""

if [ $ELAPSED -ge $TIMEOUT ]; then
    warn "Timeout waiting for all services. Check: docker compose ps"
    docker compose ps
    exit 1
fi

info "All services healthy!"
docker compose ps

echo ""
info "ATLAS is running. Endpoints:"
info "  rag-api:   http://localhost:${ATLAS_RAG_API_PORT:-8001}/v1/chat/completions"
info "  llm-proxy: http://localhost:${ATLAS_LLM_PROXY_PORT:-8080}/v1/chat/completions"
info "  llama:     http://localhost:${ATLAS_LLAMA_PORT:-8000}/health"
echo ""
info "Test with:"
info "  curl http://localhost:${ATLAS_RAG_API_PORT:-8001}/v1/chat/completions \\"
info "    -H 'Content-Type: application/json' \\"
info "    -d '{\"model\":\"Qwen3-14B-Q4_K_M\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}]}'"
