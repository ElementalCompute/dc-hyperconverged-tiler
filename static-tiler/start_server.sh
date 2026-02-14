#!/bin/bash
set -e

echo "Starting static-tiler container..."
echo "Port: ${PORT:-6000}"

# Start the gRPC health check server
echo "Starting gRPC static-tiler health check server on port ${PORT:-6000}"
cd /app

exec python3 server.py
