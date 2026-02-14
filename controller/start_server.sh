#!/bin/bash
set -e

echo "Starting controller container..."
echo "Port: ${PORT:-5000}"

# Start the gRPC health check server
echo "Starting gRPC controller health check server on port ${PORT:-5000}"
cd /app

exec python3 server.py
