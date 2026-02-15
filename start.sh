#!/bin/bash

set -e

# Default configuration
DEFAULT_NUM_INPUTS=16
DEFAULT_NUM_APPHOSTS=16
DEFAULT_GRID_COLS=4
DEFAULT_GRID_ROWS=4

# Parse command line arguments
NUM_INPUTS="${1:-$DEFAULT_NUM_INPUTS}"
NUM_APPHOSTS="${2:-$DEFAULT_NUM_APPHOSTS}"
GRID_COLS="${3:-$DEFAULT_GRID_COLS}"
GRID_ROWS="${4:-$DEFAULT_GRID_ROWS}"

# Validate inputs
if ! [[ "$NUM_INPUTS" =~ ^[0-9]+$ ]] || [ "$NUM_INPUTS" -lt 1 ]; then
    echo "Error: NUM_INPUTS must be a positive integer"
    exit 1
fi

if ! [[ "$NUM_APPHOSTS" =~ ^[0-9]+$ ]] || [ "$NUM_APPHOSTS" -lt 1 ]; then
    echo "Error: NUM_APPHOSTS must be a positive integer"
    exit 1
fi

if ! [[ "$GRID_COLS" =~ ^[0-9]+$ ]] || [ "$GRID_COLS" -lt 1 ]; then
    echo "Error: GRID_COLS must be a positive integer"
    exit 1
fi

if ! [[ "$GRID_ROWS" =~ ^[0-9]+$ ]] || [ "$GRID_ROWS" -lt 1 ]; then
    echo "Error: GRID_ROWS must be a positive integer"
    exit 1
fi

# Validate that NUM_INPUTS equals GRID_COLS * GRID_ROWS
EXPECTED_INPUTS=$((GRID_COLS * GRID_ROWS))
if [ "$NUM_INPUTS" -ne "$EXPECTED_INPUTS" ]; then
    echo "Error: NUM_INPUTS ($NUM_INPUTS) must equal GRID_COLS * GRID_ROWS ($GRID_COLS * $GRID_ROWS = $EXPECTED_INPUTS)"
    exit 1
fi

# Validate that NUM_APPHOSTS >= NUM_INPUTS
if [ "$NUM_APPHOSTS" -lt "$NUM_INPUTS" ]; then
    echo "Error: NUM_APPHOSTS ($NUM_APPHOSTS) must be >= NUM_INPUTS ($NUM_INPUTS)"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE_FILE="$SCRIPT_DIR/.build_cache"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose-generated.yml"

echo "=========================================="
echo "Starting Tiler-v3 with configuration:"
echo "  NUM_INPUTS:    $NUM_INPUTS"
echo "  NUM_APPHOSTS:  $NUM_APPHOSTS"
echo "  GRID:          ${GRID_COLS}x${GRID_ROWS}"
echo "  OUTPUT:        4K (3840x2160)"
echo "=========================================="
echo ""

# Function to calculate hash of directory contents
calculate_dir_hash() {
    local dir=$1
    if [ ! -d "$dir" ]; then
        echo "0"
        return
    fi
    find "$dir" -type f -not -path "*/.git/*" -not -name "*.pyc" -not -name "__pycache__" | \
    xargs sha256sum 2>/dev/null | \
    awk '{print $1}' | \
    sort | \
    sha256sum | \
    cut -d' ' -f1
}

# Function to check if rebuild is needed
needs_rebuild() {
    local service=$1
    local current_hash
    local cached_hash

    current_hash=$(calculate_dir_hash "$SCRIPT_DIR/$service")
    cached_hash=$(grep "^${service}:" "$CACHE_FILE" 2>/dev/null | cut -d: -f2 || echo "")

    if [ "$current_hash" != "$cached_hash" ]; then
        return 0
    fi
    return 1
}

# Function to update cache
update_cache() {
    local service=$1
    local hash=$2

    if [ -f "$CACHE_FILE" ]; then
        sed -i "/^${service}:/d" "$CACHE_FILE" 2>/dev/null || true
    fi
    echo "${service}:${hash}" >> "$CACHE_FILE"
}

# Bring down existing services
echo "Bringing down existing containers..."
docker-compose -f "$COMPOSE_FILE" down 2>/dev/null || true

# Rebuild services if needed
SERVICES=("static-tiler" "apphost" "controller")

for service in "${SERVICES[@]}"; do
    if needs_rebuild "$service"; then
        echo "Detected changes in $service, rebuilding..."
        docker-compose -f "$SCRIPT_DIR/docker-compose.yml" build "$service"
        update_cache "$service" "$(calculate_dir_hash "$SCRIPT_DIR/$service")"
    else
        echo "$service unchanged, skipping rebuild"
    fi
done

# Generate dynamic docker-compose file
echo "Generating docker-compose configuration..."

cat > "$COMPOSE_FILE" << EOF
version: '3.8'

services:
  static-tiler:
    build: ./static-tiler
    container_name: static-tiler
    ports:
      - "6000:6000"
      - "4000:4000"
    networks:
      - tiler-network
    volumes:
      - ./static-tiler:/app
EOF

# Add volume mappings for all apphosts
for i in $(seq 1 $NUM_APPHOSTS); do
    cat >> "$COMPOSE_FILE" << EOF
      - apphost${i}-shm:/dev/shm/apphost${i}
EOF
done

# Add environment variables for static-tiler
cat >> "$COMPOSE_FILE" << EOF
    environment:
      - PORT=6000
      - NUM_INPUTS=$NUM_INPUTS
      - NUM_APPHOSTS=$NUM_APPHOSTS
      - GRID_COLS=$GRID_COLS
      - GRID_ROWS=$GRID_ROWS
      - GST_DEBUG=3
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped

  controller:
    build: ./controller
    container_name: controller
    ports:
      - "5000:5000"
    networks:
      - tiler-network
    environment:
      - PORT=5000
    restart: unless-stopped
    depends_on:
      - static-tiler
EOF

# Add apphost dependencies to controller
for i in $(seq 1 $NUM_APPHOSTS); do
    cat >> "$COMPOSE_FILE" << EOF
      - apphost${i}
EOF
done

# Generate apphost services
for i in $(seq 1 $NUM_APPHOSTS); do
    port=$((3000 + i - 1))
    grpc_port=$((7000 + i - 1))
    cat >> "$COMPOSE_FILE" << EOF

  apphost${i}:
    build: ./apphost
    container_name: apphost${i}
    environment:
      - DISPLAY=:99
      - PORT=$port
      - SERVICE_NAME=apphost${i}
    ports:
      - "$port:$port"
      - "$grpc_port:$grpc_port"
    networks:
      - tiler-network
    volumes:
      - apphost${i}-shm:/dev/shm
    restart: unless-stopped
EOF
done

# Add networks section
cat >> "$COMPOSE_FILE" << EOF

networks:
  tiler-network:
    driver: bridge

volumes:
EOF

# Generate volume definitions for all apphosts
for i in $(seq 1 $NUM_APPHOSTS); do
    cat >> "$COMPOSE_FILE" << EOF
  apphost${i}-shm:
    driver: local
    driver_opts:
      type: tmpfs
      device: tmpfs
      o: size=1g
EOF
done

echo "Docker compose file generated: $COMPOSE_FILE"
echo ""

# Start all services
echo "Starting services..."
docker-compose -f "$COMPOSE_FILE" up -d

# Show status
echo ""
echo "=========================================="
echo "Services started!"
echo "=========================================="
echo ""
docker-compose -f "$COMPOSE_FILE" ps
echo ""
echo "Configuration:"
echo "  - Static Tiler:  http://localhost:6000 (TCP stream output)"
echo "  - Controller:    http://localhost:5000"
echo "  - Apphosts:      http://localhost:3000-$((3000 + NUM_APPHOSTS - 1))"
echo ""
echo "To view logs:"
echo "  docker-compose -f $COMPOSE_FILE logs -f [service-name]"
echo ""
echo "To stop:"
echo "  docker-compose -f $COMPOSE_FILE down"
echo ""
echo "Setup complete!"
