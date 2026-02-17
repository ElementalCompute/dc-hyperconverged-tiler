#!/usr/bin/env python3

"""
Test script to verify the browser manager works correctly with the new headless configuration.
This tests the key interfaces: browser launch, navigation, and screenshots.
"""

import asyncio
import logging
import os
import sys
from typing import Tuple

# Test configuration - will use the new headless mode by default
os.environ["BROWSER_HEADLESS"] = "true"
os.environ["DISPLAY"] = ":99"

# Add current directory to import path
sys.path.insert(0, "/app")

try:
    from server import BrowserManager
except ImportError as e:
    print(f"Failed to import BrowserManager from server.py: {e}")
    print(
        "Make sure to run 'python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. browser.proto' first"
    )
    sys.exit(1)


async def test_browser_manager() -> Tuple[bool, str]:
    """Test the browser manager functionality"""
    try:
        print("Initializing browser manager...")
        manager = BrowserManager(display=":99")

        print("Starting browser manager...")
        await manager.start()

        print("Testing basic page navigation...")
        success, error, final_url = await manager.navigate("https://httpbin.org/html")

        if not success:
            raise RuntimeError(f"Navigation failed: {error}")

        print(f"Successfully navigated to: {final_url}")

        # Test screenshot capability
        print("Testing screenshot functionality...")
        screenshot_data = await manager.screenshot(format="png")

        if screenshot_data and len(screenshot_data) > 1000:
            print(f"Screenshot taken successfully: {len(screenshot_data)} bytes")
        else:
            raise RuntimeError("Screenshot failed or got invalid data")

        # Test JavaScript execution
        print("Testing JavaScript execution...")
        result, error = await manager.execute_script("1 + 1")

        if error:
            raise RuntimeError(f"Script execution failed: {error}")

        if result != "2":
            raise RuntimeError(f"Unexpected script result: {result}, expected '2'")

        print("JavaScript execution successful")

        # Test status
        status = await manager.get_status()
        print(f"Browser status: {status}")

        if not status["browser_ready"] or not status["page_loaded"]:
            raise RuntimeError("Unexpected browser status")

        print("All tests passed!")

        print("Cleaning up...")
        await manager.cleanup()

        return True, "All tests passed successfully"

    except Exception as e:
        print(f"Test failed with error: {e}")

        # Try to cleanup on error
        try:
            await manager.cleanup()
        except:
            pass

        return False, str(e)


def main():
    """Run the browser test"""
    print("\\n=== Browser Manager Test ===")
    print("Testing headless browser functionality...")

    # Basic logging setup
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        success, message = asyncio.run(test_browser_manager())

        if success:
            print(f"\n✅ SUCCESS: {message}")
            return 0
        else:
            print(f"\n❌ FAILURE: {message}")
            return 1

    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
