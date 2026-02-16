#!/bin/bash

echo "Waiting for apphost shared memory sockets to be created..."

# Wait for all shm sockets to exist
for i in {1..16}; do
  SHM_SOCKET="/dev/shm/apphost${i}/apphost${i}_socket"
  while [ ! -S "$SHM_SOCKET" ]; do
    echo "Waiting for $SHM_SOCKET..."
    sleep 1
  done
  echo "Found $SHM_SOCKET"
done

echo "All shm sockets ready. Starting GStreamer pipeline..."

gst-launch-1.0 \
  nvstreammux name=mux width=1920 height=1080 batch-size=16 batched-push-timeout=40000 ! \
  nvmultistreamtiler rows=4 columns=4 width=3840 height=2160 ! \
  nvv4l2h264enc bitrate=8000000 idrinterval=10 iframeinterval=10 profile=4 tuning-info-id=3 ! \
  h264parse config-interval=-1 ! \
  mpegtsmux ! \
  tcpserversink host=0.0.0.0 port=6000 sync=false \
  shmsrc socket-path=/dev/shm/apphost1/apphost1_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_0 \
  shmsrc socket-path=/dev/shm/apphost2/apphost2_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_1 \
  shmsrc socket-path=/dev/shm/apphost3/apphost3_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_2 \
  shmsrc socket-path=/dev/shm/apphost4/apphost4_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_3 \
  shmsrc socket-path=/dev/shm/apphost5/apphost5_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_4 \
  shmsrc socket-path=/dev/shm/apphost6/apphost6_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_5 \
  shmsrc socket-path=/dev/shm/apphost7/apphost7_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_6 \
  shmsrc socket-path=/dev/shm/apphost8/apphost8_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_7 \
  shmsrc socket-path=/dev/shm/apphost9/apphost9_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_8 \
  shmsrc socket-path=/dev/shm/apphost10/apphost10_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_9 \
  shmsrc socket-path=/dev/shm/apphost11/apphost11_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_10 \
  shmsrc socket-path=/dev/shm/apphost12/apphost12_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_11 \
  shmsrc socket-path=/dev/shm/apphost13/apphost13_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_12 \
  shmsrc socket-path=/dev/shm/apphost14/apphost14_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_13 \
  shmsrc socket-path=/dev/shm/apphost15/apphost15_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_14 \
  shmsrc socket-path=/dev/shm/apphost16/apphost16_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_15
