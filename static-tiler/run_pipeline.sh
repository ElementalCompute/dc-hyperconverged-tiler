#!/bin/bash

echo "Waiting for apphost FIFOs to be created..."

# Wait for all FIFOs to exist
for i in {1..16}; do
  FIFO_PATH="/dev/shm/apphost${i}/apphost${i}_video.fifo"
  while [ ! -p "$FIFO_PATH" ]; do
    echo "Waiting for $FIFO_PATH..."
    sleep 1
  done
  echo "Found $FIFO_PATH"
done

echo "All FIFOs ready. Starting GStreamer pipeline..."

gst-launch-1.0 \
  nvstreammux name=mux width=1920 height=1080 batch-size=16 batched-push-timeout=40000 ! \
  nvmultistreamtiler rows=4 columns=4 width=3840 height=2160 ! \
  nvv4l2h264enc bitrate=8000000 idrinterval=10 iframeinterval=10 profile=4 tuning-info-id=3 ! \
  h264parse config-interval=-1 ! \
  mpegtsmux ! \
  tcpserversink host=0.0.0.0 port=6000 sync=false \
  filesrc location=/dev/shm/apphost1/apphost1_video.fifo ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_0 \
  filesrc location=/dev/shm/apphost2/apphost2_video.fifo ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_1 \
  filesrc location=/dev/shm/apphost3/apphost3_video.fifo ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_2 \
  filesrc location=/dev/shm/apphost4/apphost4_video.fifo ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_3 \
  filesrc location=/dev/shm/apphost5/apphost5_video.fifo ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_4 \
  filesrc location=/dev/shm/apphost6/apphost6_video.fifo ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_5 \
  filesrc location=/dev/shm/apphost7/apphost7_video.fifo ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_6 \
  filesrc location=/dev/shm/apphost8/apphost8_video.fifo ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_7 \
  filesrc location=/dev/shm/apphost9/apphost9_video.fifo ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_8 \
  filesrc location=/dev/shm/apphost10/apphost10_video.fifo ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_9 \
  filesrc location=/dev/shm/apphost11/apphost11_video.fifo ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_10 \
  filesrc location=/dev/shm/apphost12/apphost12_video.fifo ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_11 \
  filesrc location=/dev/shm/apphost13/apphost13_video.fifo ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_12 \
  filesrc location=/dev/shm/apphost14/apphost14_video.fifo ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_13 \
  filesrc location=/dev/shm/apphost15/apphost15_video.fifo ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_14 \
  filesrc location=/dev/shm/apphost16/apphost16_video.fifo ! video/x-raw,width=1920,height=1080,framerate=60/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_15
