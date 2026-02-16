#!/bin/bash

echo "Starting GStreamer pipeline..."

gst-launch-1.0 \
  nvstreammux name=mux width=1920 height=1080 batch-size=16 batched-push-timeout=40000 ! \
  nvmultistreamtiler rows=4 columns=4 width=3840 height=2160 ! \
  nvv4l2h264enc bitrate=8000000 ! \
  h264parse config-interval=-1! \
  mpegtsmux ! \
  tcpserversink host=0.0.0.0 port=6000 sync=false \
  videotestsrc pattern=0 is-live=true ! video/x-raw,width=1920,height=1080,framerate=30/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_0 \
  videotestsrc pattern=1 is-live=true ! video/x-raw,width=1920,height=1080,framerate=30/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_1 \
  videotestsrc pattern=2 is-live=true ! video/x-raw,width=1920,height=1080,framerate=30/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_2 \
  videotestsrc pattern=3 is-live=true ! video/x-raw,width=1920,height=1080,framerate=30/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_3 \
  videotestsrc pattern=4 is-live=true ! video/x-raw,width=1920,height=1080,framerate=30/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_4 \
  videotestsrc pattern=5 is-live=true ! video/x-raw,width=1920,height=1080,framerate=30/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_5 \
  videotestsrc pattern=6 is-live=true ! video/x-raw,width=1920,height=1080,framerate=30/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_6 \
  videotestsrc pattern=7 is-live=true ! video/x-raw,width=1920,height=1080,framerate=30/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_7 \
  videotestsrc pattern=8 is-live=true ! video/x-raw,width=1920,height=1080,framerate=30/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_8 \
  videotestsrc pattern=9 is-live=true ! video/x-raw,width=1920,height=1080,framerate=30/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_9 \
  videotestsrc pattern=10 is-live=true ! video/x-raw,width=1920,height=1080,framerate=30/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_10 \
  videotestsrc pattern=11 is-live=true ! video/x-raw,width=1920,height=1080,framerate=30/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_11 \
  videotestsrc pattern=12 is-live=true ! video/x-raw,width=1920,height=1080,framerate=30/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_12 \
  videotestsrc pattern=13 is-live=true ! video/x-raw,width=1920,height=1080,framerate=30/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_13 \
  videotestsrc pattern=14 is-live=true ! video/x-raw,width=1920,height=1080,framerate=30/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_14 \
  videotestsrc pattern=15 is-live=true ! video/x-raw,width=1920,height=1080,framerate=30/1,format=RGBA ! queue ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_15
