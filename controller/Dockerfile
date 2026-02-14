FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install protoc and build tools for gRPC
RUN apt-get update && \
    apt-get install -y --no-install-recommends protobuf-compiler && \
    rm -rf /var/lib/apt/lists/*



COPY start_server.sh /app/start_server.sh
RUN chmod +x /app/start_server.sh

COPY . /app

WORKDIR /app
CMD ["/app/start_server.sh"]
