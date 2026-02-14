#!/bin/bash
set -e

echo "Starting apphost container..."
echo "Port: ${PORT:-3000}"

# Start the gRPC health check server
echo "Starting gRPC apphost health check server on port ${PORT:-3000}"
cd /app

exec python3 server.py
