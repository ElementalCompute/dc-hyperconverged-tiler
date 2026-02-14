FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99

WORKDIR /app

# Install all dependencies in one layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    xvfb \
    x11vnc \
    fluxbox \
    xterm \
    protobuf-compiler \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

COPY start_server.sh /app/start_server.sh
RUN chmod +x /app/start_server.sh

COPY . /app

WORKDIR /app
CMD ["/app/start_server.sh"]
