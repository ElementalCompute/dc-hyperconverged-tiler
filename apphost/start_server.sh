#!/bin/bash
set -e

# Set DISPLAY environment variable for headed browser mode
export DISPLAY=:99
# No need to start Xvfb here - it will be handled by the server.py if headed mode is used
sleep 1


echo "Starting apphost container..."
echo "Port: ${PORT:-3000}"
echo "Service: ${SERVICE_NAME:-apphost}"
echo "Display: ${DISPLAY:-:99}"
echo "X Server validated at: $DISPLAY"

# Generate proto files if they don't exist
if [ ! -f "/app/browser_pb2.py" ] || [ ! -f "/app/browser_pb2_grpc.py" ]; then
    echo "Generating proto files..."
    cd /app
    python3 -m grpc_tools.protoc \
        -I. \
        --python_out=. \
        --grpc_python_out=. \
        browser.proto
    echo "Proto files generated"
fi

# Start the gRPC apphost server
echo "Starting apphost gRPC server..."
cd /app

exec python3 server.py
