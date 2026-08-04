#!/usr/bin/env bash
# DistillNews — Fast Local Hybrid Development Runner

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

VENV_DIR="./venv"
VENV_PYTHON="$VENV_DIR/bin/python"

# Parse arguments
DO_INSTALL=false
NO_FRONTEND=false
for arg in "$@"; do
  if [ "$arg" == "--install" ]; then
    DO_INSTALL=true
  fi
  if [ "$arg" == "--no-frontend" ]; then
    NO_FRONTEND=true
  fi
done

# ------------------------------------------------------------------
# 1. Enforce Python 3.13 & Virtual Environment
# ------------------------------------------------------------------
if [ -f "$VENV_PYTHON" ]; then
    PYTHON_BIN="$VENV_PYTHON"
else
    PYTHON_BIN="python3"
fi

PY_VERSION=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "unknown")

if [ "$PY_VERSION" != "3.13" ]; then
    echo -e "${RED}❌ Error: Python 3.13 is strictly required!${NC}"
    echo -e "${YELLOW}Detected Python version: ${PY_VERSION} (using ${PYTHON_BIN})${NC}"
    echo -e "Please ensure ./venv is created with Python 3.13."
    exit 1
fi

if [ ! -f "$VENV_PYTHON" ]; then
    echo -e "${RED}❌ Error: No ./venv virtual environment found!${NC}"
    echo -e "Please create a Python 3.13 virtual environment at ./venv or run: ${CYAN}./dev.sh --install${NC}"
    exit 1
fi

# ------------------------------------------------------------------
# 2. Handle --install flag
# ------------------------------------------------------------------
if [ "$DO_INSTALL" = true ]; then
    echo -e "${CYAN}📦 Installing all Python dependencies into ./venv...${NC}"
    $VENV_PYTHON -m pip install --upgrade pip
    $VENV_PYTHON -m pip install -r server/requirements.txt \
                               -r embedding_server/requirements.txt \
                               -r pipeline/requirements.txt \
                               -r mcp_server/requirements.txt \
                               pytest pytest-asyncio email-validator azure-storage-blob
    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
        echo -e "${CYAN}📦 Installing frontend npm dependencies...${NC}"
        (cd frontend && npm install)
    fi
    echo -e "${GREEN}✓ All dependencies installed successfully.${NC}"
    if [ "$#" -eq 1 ]; then
        exit 0
    fi
fi

# ------------------------------------------------------------------
# 3. Start Infrastructure & Local Servers
# ------------------------------------------------------------------
echo -e "${CYAN}🚀 Starting DistillNews Local Hybrid Development Environment (Python 3.13)...${NC}"

# Start MongoDB and Redis in Docker
echo -e "${CYAN}📦 Ensuring Mongo & Redis containers are running...${NC}"
docker compose up -d mongo redis

PIDS=()

cleanup() {
    trap - INT TERM EXIT
    echo -e "\n${CYAN}D Stopping local servers...${NC}"
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid" 2>/dev/null || true
        fi
    done
    sleep 0.3
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid" 2>/dev/null || true
        fi
    done
    echo -e "${GREEN}✓ Local services stopped.${NC}"
    exit 0
}

trap cleanup INT TERM EXIT

# Start Embedding Server in background
echo -e "${CYAN}🧠 Starting Embedding Server on http://localhost:8001...${NC}"
$VENV_PYTHON -m uvicorn embedding_server.app:app --host 0.0.0.0 --port 8001 &
PIDS+=($!)

# Start MCP Server (SSE) in background
if $VENV_PYTHON -c "import mcp" 2>/dev/null; then
    echo -e "${CYAN}🔌 Starting MCP Server (SSE) on http://localhost:8002...${NC}"
    $VENV_PYTHON -c "from mcp_server.app import mcp; mcp.run(transport='sse', port=8002)" &
    PIDS+=($!)
fi

# Start Web Backend Server with Hot-Reloading in background
echo -e "${CYAN}🌐 Starting Web Backend Server (hot-reloading) on http://localhost:8000...${NC}"
$VENV_PYTHON -m uvicorn server.app:app --reload --host 0.0.0.0 --port 8000 &
PIDS+=($!)

# Start Next.js Frontend if available and not disabled
if [ "$NO_FRONTEND" = false ] && [ -d "frontend/node_modules" ]; then
    echo -e "${CYAN}🎨 Starting Next.js Frontend UI on http://localhost:3000...${NC}"
    (cd frontend && npm run dev) &
    PIDS+=($!)
fi

echo -e "\n${GREEN}✓ All services active! Press Ctrl+C to stop all servers.${NC}\n"

# Wait for background processes
wait "${PIDS[@]}" 2>/dev/null || true
