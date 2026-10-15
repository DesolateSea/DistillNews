#!/usr/bin/env bash
# DistillNews — Fast Local Hybrid Development Runner

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

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
# 1. Find a supported Python & create the virtual environment on install
# ------------------------------------------------------------------
if [ -f "$VENV_PYTHON" ]; then
    PYTHON_BIN="$VENV_PYTHON"
elif command -v python3.13 >/dev/null 2>&1; then
    PYTHON_BIN="python3.13"
else
    PYTHON_BIN="python3"
fi

PY_VERSION=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "unknown")

if ! "$PYTHON_BIN" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"; then
    echo -e "${RED}❌ Error: Python 3.11 or newer is required!${NC}"
    echo -e "${YELLOW}Detected Python version: ${PY_VERSION} (using ${PYTHON_BIN})${NC}"
    echo -e "Please install Python 3.11 or newer (3.13 recommended)."
    exit 1
fi

if [ ! -f "$VENV_PYTHON" ]; then
  if [ "$DO_INSTALL" = true ]; then
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    PYTHON_BIN="$VENV_PYTHON"
  else
    echo -e "${RED}❌ Error: No ./venv virtual environment found!${NC}"
    echo -e "Please create a virtual environment at ./venv or run: ${CYAN}./dev.sh --install${NC}"
    exit 1
  fi
fi

# ------------------------------------------------------------------
# 2. Handle --install flag
# ------------------------------------------------------------------
if [ "$DO_INSTALL" = true ]; then
    echo -e "${CYAN}📦 Installing all Python dependencies into ./venv...${NC}"
    $VENV_PYTHON -m pip install --upgrade pip
    # Avoid downloading CUDA libraries for the local CPU embedding service.
    $VENV_PYTHON -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    $VENV_PYTHON -m pip install -r server/requirements.txt \
                               -r embedding_server/requirements.txt \
                               -r pipeline/requirements.txt \
                               -r mcp_server/requirements.txt \
                               pytest pytest-asyncio email-validator azure-storage-blob
    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
        echo -e "${CYAN}📦 Installing frontend npm dependencies...${NC}"
        (cd frontend && npm ci)
    fi
    echo -e "${GREEN}✓ All dependencies installed successfully.${NC}"
    if [ "$#" -eq 1 ]; then
        exit 0
    fi
fi

# ------------------------------------------------------------------
# 3. Start Infrastructure & Local Servers
# ------------------------------------------------------------------
echo -e "${CYAN}🚀 Starting DistillNews Local Hybrid Development Environment (Python ${PY_VERSION})...${NC}"

# Safely load configuration from .env if present
if [ -f ".env" ]; then
    ENV_EXPORTS="$($PYTHON_BIN -c "
import dotenv, re, shlex
config = dotenv.dotenv_values('.env')
for k, v in config.items():
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', k):
        raise ValueError('Invalid environment variable name')
    if v is not None:
        print(f'export {k}={shlex.quote(v)}')
")"
    eval "$ENV_EXPORTS"
fi

BACKEND_PORT="${BACKEND_PORT:-${PORT:-8000}}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
EMBEDDING_PORT="${EMBEDDING_PORT:-8001}"
MCP_PORT="${MCP_PORT:-${FASTMCP_PORT:-8002}}"
MONGO_PORT="${MONGO_PORT:-27017}"
REDIS_PORT="${REDIS_PORT:-6379}"
export BACKEND_URL="http://127.0.0.1:${BACKEND_PORT}"
# Host processes connect to published ports, not Docker's internal DNS names.
export DB_URL="${LOCAL_DB_URL:-mongodb://127.0.0.1:${MONGO_PORT}/evolution}"
export REDIS_URL="${LOCAL_REDIS_URL:-redis://127.0.0.1:${REDIS_PORT}/0}"
export EMBEDDING_SERVICE_URL="http://127.0.0.1:${EMBEDDING_PORT}"

# Fail before launching anything rather than leave a frontend without its API.
RUN_MCP=false
if "$VENV_PYTHON" -c "import mcp" 2>/dev/null; then
    RUN_MCP=true
fi
PORTS=("backend:${BACKEND_PORT}" "embedding:${EMBEDDING_PORT}")
if [ "$RUN_MCP" = true ]; then PORTS+=("mcp:${MCP_PORT}"); fi
if [ "$NO_FRONTEND" = false ]; then
    if [ ! -d frontend/node_modules ]; then
        echo -e "${RED}Frontend dependencies missing. Run ./dev.sh --install first.${NC}"
        exit 1
    fi
    PORTS+=("frontend:${FRONTEND_PORT}")
fi
"$VENV_PYTHON" - "${PORTS[@]}" <<'PY'
import socket
import sys

sockets = []
try:
    for entry in sys.argv[1:]:
        name, port = entry.split(":")
        sock = socket.socket()
        sockets.append(sock)
        try:
            sock.bind(("127.0.0.1", int(port)))
        except (OSError, ValueError, OverflowError):
            sys.exit(f"Cannot use {name} port {port}. Stop the existing service yourself "
                     f"or choose a different port in .env. No servers were launched.")
finally:
    for sock in sockets:
        sock.close()
PY
command -v setsid >/dev/null || { echo "setsid is required for server cleanup."; exit 1; }

# Start MongoDB and Redis in Docker
echo -e "${CYAN}📦 Ensuring Mongo & Redis containers are running...${NC}"
docker compose up -d --wait mongo redis

PIDS=()

cleanup() {
    status=$?
    trap - INT TERM EXIT
    echo -e "\n${CYAN}🛑 Stopping local servers...${NC}"
    for pid in "${PIDS[@]}"; do
        if kill -0 -- "-$pid" 2>/dev/null; then
            kill -TERM -- "-$pid" 2>/dev/null || true
        fi
    done
    sleep 0.3
    for pid in "${PIDS[@]}"; do
        if kill -0 -- "-$pid" 2>/dev/null; then
            kill -9 -- "-$pid" 2>/dev/null || true
        fi
    done
    echo -e "${GREEN}✓ Local services stopped.${NC}"
    exit "$status"
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

wait_for_health() {
    "$VENV_PYTHON" - "$1" "$2" "$3" <<'PY'
import os
import sys
import time
from urllib.request import urlopen

name, url, pid = sys.argv[1:]
deadline = time.monotonic() + 90
while time.monotonic() < deadline:
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        sys.exit(f"{name} exited before becoming ready. Check its startup error above.")
    try:
        with urlopen(url, timeout=2) as response:
            if response.status == 200:
                break
    except OSError:
        time.sleep(0.5)
else:
    sys.exit(f"{name} did not become healthy within 90 seconds. Check its startup logs.")
PY
}

# Start Embedding Server in background
echo -e "${CYAN}🧠 Starting Embedding Server on http://localhost:${EMBEDDING_PORT}...${NC}"
setsid "$VENV_PYTHON" -m uvicorn embedding_server.app:app --host 127.0.0.1 --port "${EMBEDDING_PORT}" &
PIDS+=($!)
wait_for_health "Embedding server" "${EMBEDDING_SERVICE_URL}/health" "${PIDS[-1]}"

# Start MCP Server (SSE) in background
if [ "$RUN_MCP" = true ]; then
    echo -e "${CYAN}🔌 Starting MCP Server (SSE) on http://localhost:${MCP_PORT}...${NC}"
    setsid "$VENV_PYTHON" -m mcp_server --transport sse --host 127.0.0.1 --port "${MCP_PORT}" &
    PIDS+=($!)
fi

# Start Web Backend Server with Hot-Reloading in background
echo -e "${CYAN}🌐 Starting Web Backend Server (hot-reloading) on http://localhost:${BACKEND_PORT}...${NC}"
setsid "$VENV_PYTHON" -m uvicorn server.app:app --reload --host 127.0.0.1 --port "${BACKEND_PORT}" &
PIDS+=($!)
wait_for_health "Backend" "${BACKEND_URL}/health" "${PIDS[-1]}"

# Start Next.js Frontend if available and not disabled
if [ "$NO_FRONTEND" = false ] && [ -d "frontend/node_modules" ]; then
    echo -e "${CYAN}🎨 Starting Next.js Frontend UI on http://localhost:${FRONTEND_PORT}...${NC}"
    (cd frontend && exec setsid npm run dev -- --hostname 127.0.0.1 -p "${FRONTEND_PORT}") &
    PIDS+=($!)
    wait_for_health "Frontend" "http://127.0.0.1:${FRONTEND_PORT}" "${PIDS[-1]}"
elif [ "$NO_FRONTEND" = false ]; then
    echo -e "${YELLOW}Frontend dependencies missing. Run ./dev.sh --install first.${NC}"
fi

echo -e "\n${GREEN}✓ Backend ready at ${BACKEND_URL}. Press Ctrl+C to stop.${NC}\n"

# Wait for background processes
status=0
wait -n "${PIDS[@]}" || status=$?
echo -e "${RED}A local service exited (status ${status}); stopping the remaining servers.${NC}"
exit 1
