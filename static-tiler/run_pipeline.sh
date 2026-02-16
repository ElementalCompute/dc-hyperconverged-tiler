#!/bin/bash
echo "Starting GStreamer pipeline..."
gst-launch-1.0 \
  nvstreammux name=mux width=1920 height=1080 batch-size=16 batched-push-timeout=40000 ! \
  nvmultistreamtiler rows=4 columns=4 width=3840 height=2160 ! \
  nvv4l2h264enc bitrate=8000000 idrinterval=10 iframeinterval=10 profile=4 tuning-info-id=3 ! \
  h264parse config-interval=-1 ! \
  mpegtsmux ! \
  tcpserversink host=0.0.0.0 port=6000 sync=false \
  shmsrc socket-path=/dev/shm/apphost1_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_0 \
  shmsrc socket-path=/dev/shm/apphost2_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_1 \
  shmsrc socket-path=/dev/shm/apphost3_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_2 \
  shmsrc socket-path=/dev/shm/apphost4_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_3 \
  shmsrc socket-path=/dev/shm/apphost5_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_4 \
  shmsrc socket-path=/dev/shm/apphost6_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_5 \
  shmsrc socket-path=/dev/shm/apphost7_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_6 \
  shmsrc socket-path=/dev/shm/apphost8_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_7 \
  shmsrc socket-path=/dev/shm/apphost9_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_8 \
  shmsrc socket-path=/dev/shm/apphost10_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_9 \
  shmsrc socket-path=/dev/shm/apphost11_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_10 \
  shmsrc socket-path=/dev/shm/apphost12_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_11 \
  shmsrc socket-path=/dev/shm/apphost13_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_12 \
  shmsrc socket-path=/dev/shm/apphost14_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_13 \
  shmsrc socket-path=/dev/shm/apphost15_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_14 \
  shmsrc socket-path=/dev/shm/apphost16_socket is-live=true ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_15