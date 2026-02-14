import logging
import os
import time
from concurrent import futures

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

logger = logging.getLogger(__name__)


def serve():
    """Start the gRPC static tiler server with health check"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))

    # Add health servicer
    health_servicer = health.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)

    # Set service status to SERVING
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set("static-tiler", health_pb2.HealthCheckResponse.SERVING)

    port = os.environ.get("PORT", "6000")
    server.add_insecure_port(f"[::]:{port}")
    server.start()

    logger.info(f"Static tiler gRPC health check server started on port {port}")
    print(f"Static tiler gRPC health check server started on port {port}")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down static tiler server...")
        server.stop(0)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    serve()
