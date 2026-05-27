#!/bin/bash

# Visual styling
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${CYAN}${BOLD}"
echo "=========================================================="
echo "      AGENTIC RAG - FINANCIAL ANALYST SYSTEM STARTUP      "
echo "=========================================================="
echo -e "${NC}"

# Get the script workspace directory
WORKSPACE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$WORKSPACE_DIR"

# 1. Check Python installation
echo -e "${BLUE}[1/5] Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python3 was not found on your system.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Found Python3: $(python3 --version)${NC}"

# 2. Check and activate Virtual Environment
echo -e "${BLUE}[2/5] Checking Python Virtual Environment (venv)...${NC}"
if [ ! -d "backend/venv" ]; then
    echo -e "${YELLOW}No venv detected. Automatically initializing at backend/venv...${NC}"
    python3 -m venv backend/venv
fi
source backend/venv/bin/activate
echo -e "${GREEN}✓ Activated virtual environment successfully.${NC}"

# Install python dependencies
echo -e "${BLUE}Updating Backend packages (pip install)...${NC}"
pip install --upgrade pip -q
pip install -r backend/requirements.txt -q
echo -e "${GREEN}✓ Python packages update completed.${NC}"

# 3. Check and update Node dependencies
echo -e "${BLUE}[3/5] Checking Frontend Node.js packages (npm install)...${NC}"
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}No node_modules directory found. Running npm install...${NC}"
    cd frontend && npm install && cd ..
else
    echo -e "${GREEN}✓ node_modules exists.${NC}"
fi

# 4. Check Ollama server state
echo -e "${BLUE}[4/5] Checking local Ollama service...${NC}"
OLLAMA_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:11434/api/tags || true)
if [ "$OLLAMA_CHECK" != "200" ]; then
    echo -e "${RED}Warning: Could not connect to Ollama at port 11434.${NC}"
    echo -e "${YELLOW}Note: Make sure to launch the Ollama desktop app before querying the AI Agent.${NC}"
else
    echo -e "${GREEN}✓ Successfully connected to Ollama (Port 11434).${NC}"
    
    # Check if configured model exists
    MODEL_CHECK=$(curl -s http://localhost:11434/api/tags | grep -q "qwen2.5" && echo "yes" || echo "no")
    if [ "$MODEL_CHECK" == "yes" ]; then
        echo -e "${GREEN}✓ Detected model 'qwen2.5' in Ollama.${NC}"
    else
        echo -e "${YELLOW}Note: Could not find model 'qwen2.5' in your local Ollama models list.${NC}"
        echo -e "${CYAN}Suggestion: Run 'ollama pull qwen2.5' in a separate terminal to download it.${NC}"
    fi
fi

# 5. Launch both servers concurrently and trap exit
echo -e "${BLUE}[5/5] Launching workstation (Backend & Frontend concurrently)...${NC}"

# Setup exit trap to kill both background processes on Ctrl+C
cleanup() {
    echo -e "\n${YELLOW}Stopping background processes...${NC}"
    kill "$BACKEND_PID" 2>/dev/null
    kill "$FRONTEND_PID" 2>/dev/null
    echo -e "${GREEN}Workstation stopped. See you next time!${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Start Backend (FastAPI)
echo -e "${CYAN}Starting Backend FastAPI at http://localhost:8000...${NC}"
cd "$WORKSPACE_DIR/backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > uvicorn.log 2>&1 &
BACKEND_PID=$!

# Wait a moment for backend to warm up
sleep 2

# Start Frontend (Vite)
echo -e "${CYAN}Starting Frontend Vite React at http://localhost:5173...${NC}"
cd "$WORKSPACE_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo -e "${GREEN}${BOLD}"
echo "=========================================================="
echo "  WORKSTATION LAUNCHED SUCCESSFULLY!"
echo "  - User Interface:  http://localhost:5173"
echo "  - Swagger API Doc: http://localhost:8000/docs"
echo "=========================================================="
echo -e "${NC}Press ${RED}Ctrl + C${NC} to shut down all server ports."

# Keep script running
while true; do
    sleep 1
done
