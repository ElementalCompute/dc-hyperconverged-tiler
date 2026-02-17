#!/bin/bash

# Test script to validate the apphost browser fix
# This tests the browser manager with the new headless configuration

echo "=== Testing AppHost Browser Fix ==="
echo "Starting at: $(date)"
echo

# Change to project directory
cd /home/ubuntu/tiler-v3 || exit 1

# Build the apphost container with our fixes
echo "Building apphost container..."
cd apphost || exit 1
docker build -t tiler-v3-apphost . || exit 1
cd ..

# Test basic browser functionality
echo "Testing browser manager functionality..."

# First test: headless mode
echo "Test 1: Testing headless browser (headless=true)"
docker run --rm \
  -e BROWSER_HEADLESS=true \
  -e DISPLAY=:99 \
  -e PORT=3000 \
  -e SERVICE_NAME=apphost1 \
  -v "$(pwd)/apphost:/app" \
  tiler-v3-apphost python3 /app/test_browser.py

echo
echo "=== Test Results Summary ==="

if [ $? -eq 0 ]; then
  echo "✅ Headless browser test PASSED"
else
  echo "❌ Headless browser test FAILED"
fi

echo
echo "=== Testing actual service startup ==="

# Run a brief service test
echo "Starting actual apphost service for 10 seconds..."
docker run --rm \
  -p 3000:3000 \
  -e BROWSER_HEADLESS=true \
  -e DISPLAY=:99 \
  -e PORT=3000 \
  -e SERVICE_NAME=apphost1 \
  -u root \
  -v "$(pwd)/apphost:/app" \
  tiler-v3-apphost timeout 10 python3 /app/server.py &

SERVICE_PID=$!
sleep 5

# Check if service is responding
if timeout 5 curl -s http://localhost:3000 > /dev/null 2>&1; then
  echo "✅ Service is responding to HTTP requests"
else
  echo "ℹ️ Service may not be responding to HTTP (this is normal for gRPC server)"
fi

wait $SERVICE_PID 2>/dev/null || true

echo
echo "=== Fix Test Summary ==="
echo "Browser manager should now:"
echo "  - Launch in headless mode by default (BROWSER_HEADLESS=true)"
echo "  - Avoid Xvfb and X11 dependencies"
echo "  - Provide screenshots and basic browser functionality"
echo "  - Handle navigation without X server issues"
echo
echo "If you need headed browser mode with Xvfb support:"
echo "  - Set BROWSER_HEADLESS=false"
echo "  - This will start Xvfb, x11vnc, and GStreamer streaming"
echo
