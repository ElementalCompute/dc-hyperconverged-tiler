import logging
import os
import threading
import time
from concurrent import futures

import grpc
from flask import Flask, jsonify, request
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

logger = logging.getLogger(__name__)


class ControllerService:
    """Controller service for managing apphost browsers"""

    def __init__(self):
        self.apphost_urls = {
            "apphost1": "about:blank",
            "apphost2": "about:blank",
            "apphost3": "about:blank",
            "apphost4": "about:blank",
        }
        self.apphost_clients = {}
        self._setup_apphost_connections()

    def _setup_apphost_connections(self):
        """Set up gRPC connections to all apphosts"""
        # Import browser proto files
        try:
            import sys

            sys.path.append("/app")
            import browser_pb2
            import browser_pb2_grpc

            self.browser_pb2 = browser_pb2
            self.browser_pb2_grpc = browser_pb2_grpc
        except ImportError:
            logger.warning("Browser proto files not available, will generate on demand")
            self.browser_pb2 = None
            self.browser_pb2_grpc = None

        # Connect to each apphost
        apphost_ports = {
            "apphost1": 3000,
            "apphost2": 3001,
            "apphost3": 3002,
            "apphost4": 3003,
        }

        for apphost_name, port in apphost_ports.items():
            try:
                channel = grpc.insecure_channel(f"{apphost_name}:{port}")
                if self.browser_pb2_grpc:
                    stub = self.browser_pb2_grpc.BrowserServiceStub(channel)
                    self.apphost_clients[apphost_name] = stub
                    logger.info(f"Connected to {apphost_name} on port {port}")
            except Exception as e:
                logger.error(f"Failed to connect to {apphost_name}: {e}")

    def navigate_apphost(
        self, apphost_name, url, timeout_ms=30000, wait_until_load=False
    ):
        """Navigate a specific apphost to a URL"""
        if apphost_name not in self.apphost_clients:
            return False, f"Apphost {apphost_name} not found"

        if not self.browser_pb2:
            return False, "Browser proto not available"

        try:
            stub = self.apphost_clients[apphost_name]
            request = self.browser_pb2.NavigateRequest(
                url=url, timeout_ms=timeout_ms, wait_until_load=wait_until_load
            )
            response = stub.Navigate(request, timeout=60)

            if response.success:
                self.apphost_urls[apphost_name] = response.final_url or url
                logger.info(f"{apphost_name} navigated to {url}")
                return True, response.final_url
            else:
                return False, response.error
        except Exception as e:
            logger.error(f"Navigation failed for {apphost_name}: {e}")
            return False, str(e)

    def get_apphost_url(self, apphost_name):
        """Get the current URL of a specific apphost"""
        if apphost_name not in self.apphost_clients:
            return None, f"Apphost {apphost_name} not found"

        if not self.browser_pb2:
            return self.apphost_urls.get(apphost_name, "about:blank"), None

        try:
            stub = self.apphost_clients[apphost_name]
            request = self.browser_pb2.GetURLRequest()
            response = stub.GetURL(request, timeout=5)

            # Update cached URL
            self.apphost_urls[apphost_name] = response.url
            return response.url, None
        except Exception as e:
            logger.error(f"Get URL failed for {apphost_name}: {e}")
            # Return cached URL on error
            return self.apphost_urls.get(apphost_name, "about:blank"), str(e)

    def get_all_urls(self):
        """Get URLs of all apphosts"""
        result = {}
        for apphost_name in self.apphost_clients.keys():
            url, error = self.get_apphost_url(apphost_name)
            result[apphost_name] = {"url": url, "error": error}
        return result

    def navigate_all(self, url, timeout_ms=30000, wait_until_load=False):
        """Navigate all apphosts to the same URL"""
        results = {}
        for apphost_name in self.apphost_clients.keys():
            success, message = self.navigate_apphost(
                apphost_name, url, timeout_ms, wait_until_load
            )
            results[apphost_name] = {"success": success, "message": message}
        return results


def create_http_api(controller):
    """Create Flask HTTP API for controller"""
    app = Flask(__name__)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "healthy"}), 200

    @app.route("/apphosts", methods=["GET"])
    def get_all_apphosts():
        """Get all apphost URLs"""
        urls = controller.get_all_urls()
        return jsonify(urls), 200

    @app.route("/apphost/<apphost_name>", methods=["GET"])
    def get_apphost(apphost_name):
        """Get specific apphost URL"""
        url, error = controller.get_apphost_url(apphost_name)
        if error:
            return jsonify({"url": url, "error": error}), 200
        return jsonify({"url": url}), 200

    @app.route("/apphost/<apphost_name>", methods=["POST"])
    def set_apphost(apphost_name):
        """Navigate specific apphost to URL"""
        data = request.get_json()
        if not data or "url" not in data:
            return jsonify({"error": "Missing 'url' in request body"}), 400

        url = data["url"]
        timeout_ms = data.get("timeout_ms", 30000)
        wait_until_load = data.get("wait_until_load", False)

        success, message = controller.navigate_apphost(
            apphost_name, url, timeout_ms, wait_until_load
        )

        if success:
            return jsonify({"success": True, "url": message}), 200
        else:
            return jsonify({"success": False, "error": message}), 500

    @app.route("/apphosts/navigate", methods=["POST"])
    def navigate_all_apphosts():
        """Navigate all apphosts to the same URL"""
        data = request.get_json()
        if not data or "url" not in data:
            return jsonify({"error": "Missing 'url' in request body"}), 400

        url = data["url"]
        timeout_ms = data.get("timeout_ms", 30000)
        wait_until_load = data.get("wait_until_load", False)

        results = controller.navigate_all(url, timeout_ms, wait_until_load)
        return jsonify(results), 200

    return app


def serve():
    """Start the gRPC controller server with health check and HTTP API"""
    port = os.environ.get("PORT", "5000")
    http_port = int(port) + 100  # HTTP API on 5100

    logger.info(f"Starting controller server on port {port}")

    # Initialize controller service
    controller = ControllerService()

    # Start gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Add health servicer
    health_servicer = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set("controller", health_pb2.HealthCheckResponse.SERVING)

    server.add_insecure_port(f"[::]:{port}")
    server.start()

    logger.info(f"Controller gRPC server started on port {port}")
    print(f"Controller gRPC health check server started on port {port}")
    print(f"Connected to apphosts: {list(controller.apphost_clients.keys())}")

    # Start HTTP API in separate thread
    app = create_http_api(controller)

    def run_http_server():
        logger.info(f"Starting HTTP API on port {http_port}")
        print(f"Controller HTTP API started on port {http_port}")
        app.run(host="0.0.0.0", port=http_port, debug=False, use_reloader=False)

    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down controller server...")
        server.stop(0)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    serve()
