#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE_FILE="$SCRIPT_DIR/.build_cache"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

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
        docker-compose -f "$COMPOSE_FILE" build "$service"
        update_cache "$service" "$(calculate_dir_hash "$SCRIPT_DIR/$service")"
    else
        echo "$service unchanged, skipping rebuild"
    fi
done

# Create extended compose file for 4 apphosts
EXTENDED_COMPOSE_FILE="$SCRIPT_DIR/docker-compose-extended.yml"

cat > "$EXTENDED_COMPOSE_FILE" << 'EOF'
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
      - apphost1-shm:/dev/shm/apphost1
      - apphost2-shm:/dev/shm/apphost2
      - apphost3-shm:/dev/shm/apphost3
      - apphost4-shm:/dev/shm/apphost4
    environment:
      - PORT=6000
    restart: unless-stopped

  controller:
    extends:
      file: docker-compose.yml
      service: controller
    depends_on:
      - static-tiler
      - apphost1
      - apphost2
      - apphost3
      - apphost4

EOF

# Add 4 apphost services
for i in {1..4}; do
    port=$((3000 + i - 1))
    cat << EOF >> "$EXTENDED_COMPOSE_FILE"
  apphost$i:
    build: ./apphost
    container_name: apphost$i
    environment:
      - DISPLAY=:99
      - PORT=$port
      - SERVICE_NAME=apphost${i}
    ports:
      - "$port:$port"
    networks:
      - tiler-network
    volumes:
      - apphost${i}-shm:/dev/shm
EOF
done

# Add networks and volumes section
cat << 'EOF' >> "$EXTENDED_COMPOSE_FILE"

networks:
  tiler-network:
    driver: bridge

volumes:
  apphost1-shm:
    driver: local
    driver_opts:
      type: tmpfs
      device: tmpfs
      o: size=1g
  apphost2-shm:
    driver: local
    driver_opts:
      type: tmpfs
      device: tmpfs
      o: size=1g
  apphost3-shm:
    driver: local
    driver_opts:
      type: tmpfs
      device: tmpfs
      o: size=1g
  apphost4-shm:
    driver: local
    driver_opts:
      type: tmpfs
      device: tmpfs
      o: size=1g
EOF

# Start all services
echo "Starting services..."
docker-compose -f "$EXTENDED_COMPOSE_FILE" up -d

# Show status
echo ""
echo "Services started!"
echo ""
docker-compose -f "$EXTENDED_COMPOSE_FILE" ps
echo ""
echo "Setup complete!"
