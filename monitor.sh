#!/bin/bash

# Define the compose file
COMPOSE_FILE="docker-compose.yaml"

# Define the network name
NETWORK_NAME="static-network"

# Start the services
echo "Starting Docker Compose services..."
docker compose -f "$COMPOSE_FILE" up -d

# Wait for containers to start
sleep 5

# Extract only containers where 'attach: true'
echo "Filtering containers with attach: true..."
ATTACHED_CONTAINERS=$(yq eval '.services | to_entries | map(select(.value.attach == true)) | .[].key' "$COMPOSE_FILE")

# If no containers are found, exit
if [ -z "$ATTACHED_CONTAINERS" ]; then
    echo "No containers with attach: true found. Exiting."
    exit 0
fi

# Open Windows Terminal with attached containers
WT_CMD="wt.exe"

COUNT=0
for CONTAINER in $ATTACHED_CONTAINERS; do
    if [ $COUNT -eq 0 ]; then
        WT_CMD+=" new-tab --title '$CONTAINER' -p 'PowerShell' docker attach $CONTAINER"
    else
        WT_CMD+=" ; new-tab --title '$CONTAINER' -p 'PowerShell' docker attach $CONTAINER"
    fi
    COUNT=$((COUNT+1))
done

# Execute the Windows Terminal command
cmd.exe /c start $WT_CMD

echo "Attached to specified containers in new terminal tabs."
