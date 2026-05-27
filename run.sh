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
echo -e "${BLUE}[1/5] Kiểm tra Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Lỗi: Không tìm thấy Python3 trên máy tính của bạn.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Đã tìm thấy Python3: $(python3 --version)${NC}"

# 2. Check and activate Virtual Environment
echo -e "${BLUE}[2/5] Kiểm tra môi trường ảo Python (venv)...${NC}"
if [ ! -d "backend/venv" ]; then
    echo -e "${YELLOW}Chưa phát hiện venv. Đang tự động khởi tạo venv tại backend/venv...${NC}"
    python3 -m venv backend/venv
fi
source backend/venv/bin/activate
echo -e "${GREEN}✓ Đã kích hoạt venv thành công.${NC}"

# Install python dependencies
echo -e "${BLUE}Đang cập nhật các thư viện Backend (pip install)...${NC}"
pip install --upgrade pip -q
pip install -r backend/requirements.txt -q
echo -e "${GREEN}✓ Cập nhật thư viện Python hoàn tất.${NC}"

# 3. Check and update Node dependencies
echo -e "${BLUE}[3/5] Kiểm tra thư viện Frontend Node.js (npm install)...${NC}"
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}Chưa phát hiện thư mục node_modules. Đang chạy npm install...${NC}"
    cd frontend && npm install && cd ..
else
    echo -e "${GREEN}✓ node_modules đã tồn tại.${NC}"
fi

# 4. Check Ollama server state
echo -e "${BLUE}[4/5] Kiểm tra dịch vụ Ollama cục bộ...${NC}"
OLLAMA_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:11434/api/tags || true)
if [ "$OLLAMA_CHECK" != "200" ]; then
    echo -e "${RED}Cảnh báo: Không thể kết nối với Ollama tại cổng 11434.${NC}"
    echo -e "${YELLOW}Lưu ý: Bạn hãy bật ứng dụng Ollama trên máy tính của mình trước khi gửi tin nhắn cho Agent.${NC}"
else
    echo -e "${GREEN}✓ Đã kết nối thành công với Ollama (Port 11434).${NC}"
    
    # Check if configured model exists
    MODEL_CHECK=$(curl -s http://localhost:11434/api/tags | grep -q "qwen2.5" && echo "yes" || echo "no")
    if [ "$MODEL_CHECK" == "yes" ]; then
        echo -e "${GREEN}✓ Đã phát hiện mô hình qwen2.5 trong Ollama.${NC}"
    else
        echo -e "${YELLOW}Lưu ý: Chưa tìm thấy mô hình 'qwen2.5' trong danh sách Ollama.${NC}"
        echo -e "${CYAN}Gợi ý: Hãy chạy lệnh 'ollama pull qwen2.5' ở cửa sổ terminal mới để tải mô hình về máy.${NC}"
    fi
fi

# 5. Launch both servers concurrently and trap exit
echo -e "${BLUE}[5/5] Đang khởi chạy hệ thống (Backend & Frontend)...${NC}"

# Setup exit trap to kill both background processes on Ctrl+C
cleanup() {
    echo -e "\n${YELLOW}Đang dừng các dịch vụ đang chạy...${NC}"
    kill "$BACKEND_PID" 2>/dev/null
    kill "$FRONTEND_PID" 2>/dev/null
    echo -e "${GREEN}Hệ thống đã dừng hoàn toàn. Hẹn gặp lại bạn!${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Start Backend (FastAPI)
echo -e "${CYAN}Đang khởi động Backend FastAPI tại http://localhost:8000...${NC}"
cd "$WORKSPACE_DIR/backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > uvicorn.log 2>&1 &
BACKEND_PID=$!

# Wait a moment for backend to warm up
sleep 2

# Start Frontend (Vite)
echo -e "${CYAN}Đang khởi động Frontend Vite React tại http://localhost:5173...${NC}"
cd "$WORKSPACE_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo -e "${GREEN}${BOLD}"
echo "=========================================================="
echo "  HỆ THỐNG KHỞI CHẠY THÀNH CÔNG!"
echo "  - Giao diện người dùng: http://localhost:5173"
echo "  - API Backend Swagger:  http://localhost:8000/docs"
echo "=========================================================="
echo -e "${NC}Nhấn ${RED}Ctrl + C${NC} để tắt tất cả các cổng máy chủ."

# Keep script running
while true; do
    sleep 1
done
