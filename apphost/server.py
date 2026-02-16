import asyncio
import logging
import os
import subprocess
import threading
import time
from concurrent import futures

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from playwright.async_api import async_playwright

# Import generated proto files (will be generated at runtime)
try:
    import browser_pb2
    import browser_pb2_grpc
except ImportError:
    # Generate proto files if they don't exist
    subprocess.run(
        [
            "python3",
            "-m",
            "grpc_tools.protoc",
            "-I.",
            "--python_out=.",
            "--grpc_python_out=.",
            "browser.proto",
        ],
        cwd="/app",
        check=False,
    )
    import browser_pb2
    import browser_pb2_grpc

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages Playwright browser instance and GStreamer pipeline"""

    def __init__(self, display=":99"):
        self.display = display
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.gst_pipeline = None
        self.xvfb_process = None
        self.x11vnc_process = None
        self.novnc_process = None
        self.ready = False
        self.streaming = False

    async def start(self):
        """Initialize Xvfb, browser, and GStreamer pipeline"""
        logger.info("Starting browser manager...")

        # Start Xvfb
        await self._start_xvfb()

        # Start x11vnc
        await self._start_x11vnc()

        # Start noVNC
        await self._start_novnc()

        # Start Playwright
        await self._start_browser()

        # Start GStreamer pipeline
        await self._start_gstreamer()

        self.ready = True
        logger.info("Browser manager ready")

    async def _start_xvfb(self):
        """Start Xvfb virtual display"""
        logger.info(f"Starting Xvfb on display {self.display}")
        self.xvfb_process = subprocess.Popen(
            [
                "Xvfb",
                self.display,
                "-screen",
                "0",
                "1920x1080x24",
                "-ac",
                "+extension",
                "RANDR",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Wait for X server to be ready
        await asyncio.sleep(2)
        logger.info("Xvfb started")

    async def _start_x11vnc(self):
        """Start x11vnc VNC server"""
        service_name = os.environ.get("SERVICE_NAME", "apphost")
        # Extract number from service name (e.g., apphost1 -> 1, apphost2 -> 2)
        service_num = "".join(filter(str.isdigit, service_name)) or "1"
        vnc_port = 5900 + int(service_num)  # VNC port: 5901, 5902, 5903, 5904

        logger.info(f"Starting x11vnc on port {vnc_port}...")

        self.x11vnc_process = subprocess.Popen(
            [
                "x11vnc",
                "-display",
                self.display,
                "-rfbport",
                str(vnc_port),
                "-forever",
                "-shared",
                "-nopw",  # No password for simplicity
                "-quiet",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Wait for VNC server to be ready
        await asyncio.sleep(1)
        logger.info(f"x11vnc started on port {vnc_port}")

    async def _start_novnc(self):
        """Start noVNC websocket proxy"""
        service_name = os.environ.get("SERVICE_NAME", "apphost")
        # Extract number from service name
        service_num = "".join(filter(str.isdigit, service_name)) or "1"
        vnc_port = 5900 + int(service_num)
        novnc_port = 7000 + int(service_num) - 1  # noVNC port: 7000, 7001, 7002, 7003

        logger.info(f"Starting noVNC on port {novnc_port}...")

        self.novnc_process = subprocess.Popen(
            [
                "/opt/novnc/utils/novnc_proxy",
                "--vnc",
                f"localhost:{vnc_port}",
                "--listen",
                str(novnc_port),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Wait for noVNC to be ready
        await asyncio.sleep(1)
        logger.info(f"noVNC started on port {novnc_port} (VNC backend: {vnc_port})")

    async def _start_browser(self):
        """Start Playwright browser"""
        logger.info("Starting Playwright browser...")

        os.environ["DISPLAY"] = self.display

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,  # Run headless to avoid X11 issues
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--no-gpu",
                "--window-size=1920,1080",
            ],
        )

        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            screen={"width": 1920, "height": 1080},
        )

        self.page = await self.context.new_page()

        # Navigate to blank page
        await self.page.goto("about:blank")

        logger.info("Browser started successfully")

    async def _start_gstreamer(self):
        """Start GStreamer pipeline to capture X display and output to RTP loopback"""
        logger.info("Starting GStreamer pipeline...")

        service_name = os.environ.get("SERVICE_NAME", "apphost")
        # Calculate port based on service number (apphost1 -> 2001, apphost2 -> 2002, etc.)
        apphost_num = (
            int(service_name.replace("apphost", ""))
            if service_name.startswith("apphost")
            else 1
        )
        udp_port = 2000 + apphost_num

        # GStreamer pipeline:
        # ximagesrc captures the X display
        # videoconvert ensures proper format
        # rtp provides low latency streaming to localhost
        pipeline_cmd = [
            "gst-launch-1.0",
            "-e",
            "ximagesrc",
            f"display-name={self.display}",
            "use-damage=false",
            "show-pointer=false",
            "!",
            "video/x-raw,framerate=60/1,width=1920,height=1080",
            "!",
            "videoconvert",
            "!",
            "video/x-raw,format=RGBA,width=1920,height=1080",
            "udpsink",
            "host=127.0.0.1",
            f"port={rtp_port}",
            "sync=false",
        ]

        logger.info(f"GStreamer pipeline: {' '.join(pipeline_cmd)}")
        logger.info(f"Streaming to: localhost:{rtp_port}")

        # Start pipeline in background
        self.gst_pipeline = subprocess.Popen(
            pipeline_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Give pipeline time to start
        await asyncio.sleep(1)

        if self.gst_pipeline.poll() is None:
            self.streaming = True
            logger.info("GStreamer pipeline started successfully")
        else:
            logger.error(f"GStreamer pipeline failed to start")
            raise RuntimeError(f"Failed to start GStreamer pipeline")

    async def navigate(self, url, timeout_ms=30000, wait_until_load=True):
        """Navigate to a URL"""
        if not self.page:
            raise RuntimeError("Browser not initialized")

        logger.info(f"Navigating to: {url}")

        try:
            wait_until = "networkidle" if wait_until_load else "domcontentloaded"
            await self.page.goto(url, timeout=timeout_ms, wait_until=wait_until)
            final_url = self.page.url
            logger.info(f"Navigation complete: {final_url}")
            return True, None, final_url
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False, str(e), None

    async def get_url(self):
        """Get current URL"""
        if not self.page:
            return "about:blank"
        return self.page.url

    async def screenshot(self, format="png", quality=None):
        """Take screenshot"""
        if not self.page:
            raise RuntimeError("Browser not initialized")

        options = {"type": format}
        if format == "jpeg" and quality:
            options["quality"] = quality

        data = await self.page.screenshot(**options)
        return data

    async def execute_script(self, script):
        """Execute JavaScript"""
        if not self.page:
            raise RuntimeError("Browser not initialized")

        try:
            result = await self.page.evaluate(script)
            return str(result), None
        except Exception as e:
            logger.error(f"Script execution failed: {e}")
            return None, str(e)

    async def get_status(self):
        """Get status"""
        return {
            "browser_ready": self.ready,
            "page_loaded": self.page is not None,
            "current_url": await self.get_url() if self.page else "",
            "streaming": self.streaming,
        }

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up browser manager...")

        if self.gst_pipeline:
            self.gst_pipeline.terminate()
            self.gst_pipeline.wait()

        if self.novnc_process:
            self.novnc_process.terminate()
            self.novnc_process.wait()

        if self.x11vnc_process:
            self.x11vnc_process.terminate()
            self.x11vnc_process.wait()

        if self.context:
            await self.context.close()

        if self.browser:
            await self.browser.close()

        if self.playwright:
            await self.playwright.stop()

        if self.xvfb_process:
            self.xvfb_process.terminate()
            self.xvfb_process.wait()

        logger.info("Cleanup complete")


class BrowserServiceServicer(browser_pb2_grpc.BrowserServiceServicer):
    """gRPC service for browser control"""

    def __init__(self, browser_manager, loop):
        self.browser_manager = browser_manager
        self.loop = loop

    def Navigate(self, request, context):
        """Navigate to URL"""
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.browser_manager.navigate(
                    request.url,
                    request.timeout_ms if request.timeout_ms > 0 else 30000,
                    request.wait_until_load,
                ),
                self.loop,
            )
            success, error, final_url = future.result(timeout=60)

            return browser_pb2.NavigateResponse(
                success=success, error=error or "", final_url=final_url or ""
            )
        except Exception as e:
            logger.error(f"Navigate RPC failed: {e}")
            return browser_pb2.NavigateResponse(
                success=False, error=str(e), final_url=""
            )

    def GetURL(self, request, context):
        """Get current URL"""
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.browser_manager.get_url(), self.loop
            )
            url = future.result(timeout=5)
            return browser_pb2.GetURLResponse(url=url)
        except Exception as e:
            logger.error(f"GetURL RPC failed: {e}")
            return browser_pb2.GetURLResponse(url="")

    def Screenshot(self, request, context):
        """Take screenshot"""
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.browser_manager.screenshot(
                    request.format or "png",
                    request.quality if request.quality > 0 else None,
                ),
                self.loop,
            )
            data = future.result(timeout=10)
            return browser_pb2.ScreenshotResponse(data=data, error="")
        except Exception as e:
            logger.error(f"Screenshot RPC failed: {e}")
            return browser_pb2.ScreenshotResponse(data=b"", error=str(e))

    def ExecuteScript(self, request, context):
        """Execute JavaScript"""
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.browser_manager.execute_script(request.script), self.loop
            )
            result, error = future.result(timeout=10)
            return browser_pb2.ExecuteScriptResponse(
                result=result or "", error=error or ""
            )
        except Exception as e:
            logger.error(f"ExecuteScript RPC failed: {e}")
            return browser_pb2.ExecuteScriptResponse(result="", error=str(e))

    def GetStatus(self, request, context):
        """Get browser status"""
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.browser_manager.get_status(), self.loop
            )
            status = future.result(timeout=5)
            return browser_pb2.GetStatusResponse(
                browser_ready=status["browser_ready"],
                page_loaded=status["page_loaded"],
                current_url=status["current_url"],
                streaming=status["streaming"],
            )
        except Exception as e:
            logger.error(f"GetStatus RPC failed: {e}")
            return browser_pb2.GetStatusResponse(
                browser_ready=False,
                page_loaded=False,
                current_url="",
                streaming=False,
            )


async def init_browser_manager():
    """Initialize browser manager"""
    display = os.environ.get("DISPLAY", ":99")
    manager = BrowserManager(display=display)
    await manager.start()
    return manager


def serve():
    """Start the gRPC apphost server"""
    port = os.environ.get("PORT", "3000")
    service_name = os.environ.get("SERVICE_NAME", "apphost")

    logger.info(f"Starting apphost server: {service_name} on port {port}")

    # Initialize browser manager in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    browser_manager = loop.run_until_complete(init_browser_manager())

    # Start event loop in background thread
    def run_event_loop():
        asyncio.set_event_loop(loop)
        loop.run_forever()

    loop_thread = threading.Thread(target=run_event_loop, daemon=True)
    loop_thread.start()

    # Create gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Add health check service
    health_servicer = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set("apphost", health_pb2.HealthCheckResponse.SERVING)

    # Add browser service
    browser_servicer = BrowserServiceServicer(browser_manager, loop)
    browser_pb2_grpc.add_BrowserServiceServicer_to_server(browser_servicer, server)

    server.add_insecure_port(f"[::]:{port}")
    server.start()

    logger.info(f"AppHost gRPC server started on port {port}")
    logger.info(
        f"Browser ready, streaming to localhost:{port + 1700}"
    )  # Match RTP port calculation
    print(f"AppHost {service_name} ready on port {port}")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down apphost server...")
        cleanup_future = asyncio.run_coroutine_threadsafe(
            browser_manager.cleanup(), loop
        )
        cleanup_future.result(timeout=10)
        loop.call_soon_threadsafe(loop.stop)
        server.stop(0)
        loop_thread.join(timeout=5)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    serve()
