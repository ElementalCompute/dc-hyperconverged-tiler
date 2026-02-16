FROM nvcr.io/nvidia/deepstream:8.0-triton-multiarch

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Copy the launch script
COPY run_pipeline.sh /app/run_pipeline.sh

# Override the base image entrypoint
ENTRYPOINT []
CMD ["/bin/bash", "/app/run_pipeline.sh"]
