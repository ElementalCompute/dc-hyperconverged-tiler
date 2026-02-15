FROM nvcr.io/nvidia/deepstream:8.0-triton-multiarch

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install GStreamer Python bindings and development packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3-gi \
    python3-gi-cairo \
    python3-gst-1.0 \
    gir1.2-gstreamer-1.0 \
    gir1.2-gst-plugins-base-1.0 \
    libgirepository1.0-dev \
    libcairo2-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY start_server.sh /app/start_server.sh
RUN chmod +x /app/start_server.sh

COPY . /app

WORKDIR /app
CMD ["/app/start_server.sh"]
