#!/bin/bash

# Create and start Podman pod with 1 master + 3 grabbers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

POD_NAME="script-grabber-pod"
VOLUME_NAME="cluster-data"
NETWORK_NAME="grabber-net"

echo -e "${GREEN}Creating ScriptGrabber Pod...${NC}"

# Create volume if it doesn't exist
if ! podman volume exists "$VOLUME_NAME"; then
    echo "Creating volume: $VOLUME_NAME"
    podman volume create "$VOLUME_NAME"
else
    echo "Volume $VOLUME_NAME already exists"
fi

# Stop and remove existing pod if it exists
if podman pod exists "$POD_NAME"; then
    echo -e "${YELLOW}Stopping existing pod...${NC}"
    podman pod stop "$POD_NAME"
    podman pod rm "$POD_NAME"
fi

# Create pod with shared network
echo "Creating pod: $POD_NAME"
podman pod create \
    --name "$POD_NAME" \
    --publish 8000:8000 \
    --publish 5173:5173

# Build container image if it doesn't exist
if ! podman image exists script-grabber:latest; then
    echo "Building container image..."
    podman build -t script-grabber:latest .
fi

# Start master container
echo -e "${GREEN}Starting master container...${NC}"
podman run -dt \
    --pod "$POD_NAME" \
    --name script-grabber-master \
    -v "$VOLUME_NAME:/cluster:Z" \
    -v "./apps/backend:/app/backend:Z" \
    -w /app/backend \
    --env CLUSTER_PATH=/cluster \
    --env HOST=0.0.0.0 \
    --env PORT=8000 \
    python:3.12-slim \
    bash -c "pip install -q fastapi uvicorn python-multipart python-dotenv pydantic aiofiles pytest pytest-timeout pytest-cov pytest-mock pytest-asyncio && python server.py"

# Start frontend container
echo -e "${GREEN}Starting frontend container...${NC}"
podman run -dt \
    --pod "$POD_NAME" \
    --name script-grabber-frontend \
    -v "./apps/frontend:/app/frontend:Z" \
    -w /app/frontend \
    --env VITE_API_URL=http://localhost:8000 \
    node:20-slim \
    bash -c "npm install && npm run dev -- --host 0.0.0.0"

# Start grabber containers
for i in {1..3}; do
    echo -e "${GREEN}Starting grabber${i} container...${NC}"
    podman run -dt \
        --pod "$POD_NAME" \
        --name "script-grabber-grabber${i}" \
        -v "$VOLUME_NAME:/cluster:Z" \
        script-grabber:latest \
        "grabber${i}" /cluster --job-timeout 3600
done

echo ""
echo -e "${GREEN}✅ Pod created successfully!${NC}"
echo ""
echo "Pod: $POD_NAME"
echo "Volume: $VOLUME_NAME"
echo "Containers: 1 master + 1 frontend + 3 grabbers"
echo ""
echo "Services:"
echo "  Frontend:    http://localhost:5173"
echo "  Backend API: http://localhost:8000"
echo "  API Docs:    http://localhost:8000/docs"
echo ""
echo "Management commands:"
echo "  podman pod ps                         # View pod status"
echo "  podman pod logs $POD_NAME             # View all logs"
echo "  podman logs script-grabber-master     # View backend logs"
echo "  podman logs script-grabber-frontend   # View frontend logs"
echo "  podman logs script-grabber-grabber1   # View grabber logs"
echo "  podman pod stop $POD_NAME             # Stop pod"
echo "  podman pod start $POD_NAME            # Start pod"
echo "  podman pod rm $POD_NAME               # Remove pod"
echo ""
