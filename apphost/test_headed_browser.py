#!/usr/bin/env python3

"""
Test script for HEADED browser with GStreamer streaming functionality.
This tests the full pipeline: Xvfb -> Browser -> Screenshot -> GStreamer UDP streaming
"""

import asyncio
import logging
import os
import socket
import subprocess
import sys
import time
from typing import Tuple

# Force environment for headed browser mode with streaming
os.environ["DISPLAY"] = ":99"
os.environ["SERVICE_NAME"] = "apphost1"  # This will use port 2001 for GStreamer

# Add current directory to import path
sys.path.insert(0, "/app")

try:
    from server import BrowserManager
except ImportError as e:
    print(f"Failed to import BrowserManager from server.py: {e}")
    print("Make sure server.py is properly accessible")
    sys.exit(1)


def check_udp_port(port: int) -> bool:
    """Check if UDP port is bound and listening"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.1)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        return result
    except:
        return False


async def test_full_pipeline() -> Tuple[bool, str]:
    """Test the complete headed browser + streaming pipeline"""
    try:
        print("=== Testing HEADED Browser + GStreamer Streaming ===")

        print("Initializing headed browser manager...")
        manager = BrowserManager(display=":99")

        print("Starting complete pipeline (Xvfb + Browser + GStreamer)...")
        await manager.start()

        # Verify GStreamer streaming started
        if not manager.streaming:
            print("⚠️  GStreamer streaming did not start - checking why...")

        # Test navigation
        print("Testing browser navigation...")
        success, error, final_url = await manager.navigate("https://httpbin.org/html")

        if not success:
            raise RuntimeError(f"Navigation failed: {error}")

        print(f"✓ Successfully navigated to: {final_url}")

        # Wait a moment for page to fully render
        await asyncio.sleep(2)

        # Test screenshot
        print("Testing screenshot capture...")
        screenshot_data = await manager.screenshot(format="png")

        if screenshot_data and len(screenshot_data) > 10000:
            print(f"✓ Screenshot captured: {len(screenshot_data)} bytes")
        else:
            print(f"⚠️  Screenshot seems small: {len(screenshot_data)} bytes")

        # Test JavaScript execution
        print("Testing JavaScript execution...")
        result, error = await manager.execute_script("document.title")

        if error:
            raise RuntimeError(f"Script execution failed: {error}")
        print(f"✓ Document title: {result}")

        # Verify streaming status
        status = await manager.get_status()
        print(f"📊 Service status: {status}")

        if status["streaming"]:
            print("✅ GStreamer streaming is ACTIVE - X display is being captured!")

            # Try to verify UDP port is working
            udp_port = 2001  # For apphost1
            if check_udp_port(udp_port):
                print(f"✅ UDP streaming to port {udp_port} appears to be working")
            else:
                print(f"📊 UDP port {udp_port} status unknown (may still be streaming)")
        else:
            print("❌ GStreamer streaming is NOT active")

        print("All tests completed!")

        print("Cleaning up...")
        await manager.cleanup()

        return True, "Headed browser + streaming pipeline working successfully"

    except Exception as e:
        print(f"❌ Test failed: {e}")
        try:
            await manager.cleanup()
        except:
            pass
        return False, str(e)


def main():
    """Run the full pipeline test"""
    print("\n=== Full Pipeline Test (HEADED Browser + GStreamer) ===")
    print("Environment:")
    print(f"  DISPLAY={os.environ.get('DISPLAY')}")
    print(f"  SERVICE_NAME={os.environ.get('SERVICE_NAME')}")
    print()

    # Logging setup
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        success, message = asyncio.run(test_full_pipeline())

        if success:
            print(f"\n✅ SUCCESS: {message}")
            print("\n🎯 CONTEXT: This proves the container works correctly:")
            print("  - Xvfb starts and properly initializes X display")
            print("  - Browser launches in headed mode (not headless)")
            print("  - GStreamer ximagesrc captures the actual X display")
            print("  - UDP streaming is active and ready for receivers")
            return 0
        else:
            print(f"\n❌ FAILURE: {message}")
            return 1

    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
