#!/bin/bash

# Stop and remove the Podman pod

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

POD_NAME="script-grabber-pod"

echo -e "${YELLOW}Stopping ScriptGrabber Pod...${NC}"

if podman pod exists "$POD_NAME"; then
    podman pod stop "$POD_NAME"
    podman pod rm "$POD_NAME"
    echo -e "${GREEN}✅ Pod stopped and removed${NC}"
else
    echo "Pod $POD_NAME does not exist"
fi
