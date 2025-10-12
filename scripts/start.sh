#!/bin/bash

# Start both backend and frontend services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting ScriptGrabber services...${NC}"

# Check if .env exists in backend
if [ ! -f "apps/backend/.env" ]; then
    echo -e "${YELLOW}Warning: apps/backend/.env not found${NC}"
    echo "Creating from .env.sample..."
    cp apps/backend/.env.sample apps/backend/.env
    echo -e "${GREEN}Created apps/backend/.env${NC}"
    echo "Please edit apps/backend/.env if needed"
fi

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo -e "${GREEN}Services stopped${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
echo -e "${GREEN}Starting backend on http://localhost:8000${NC}"
cd apps/backend
uv run python server.py &
BACKEND_PID=$!
cd ../..

# Wait a bit for backend to start
sleep 2

# Start frontend
echo -e "${GREEN}Starting frontend on http://localhost:5173${NC}"
cd apps/frontend
npm run dev &
FRONTEND_PID=$!
cd ../..

echo -e "${GREEN}✅ Services started!${NC}"
echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop both services${NC}"

# Wait for processes
wait $BACKEND_PID $FRONTEND_PID
