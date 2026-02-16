#!/bin/bash

echo "Starting GStreamer pipeline with RTP loopback sources..."

gst-launch-1.0 \
  nvstreammux name=mux width=1920 height=1080 batch-size=16 batched-push-timeout=40000 ! \
  nvmultistreamtiler rows=4 columns=4 width=3840 height=2160 ! \
  nvv4l2h264enc bitrate=8000000 idrinterval=10 iframeinterval=10 profile=4 tuning-info-id=3 ! \
  h264parse config-interval=-1 ! \
  mpegtsmux ! \
  tcpserversink host=0.0.0.0 port=6000 sync=false \
  udpsrc port=2001 ! application/x-rtp,encoding-name=H264 ! rtph264depay ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_0 \
  udpsrc port=2002 ! application/x-rtp,encoding-name=H264 ! rtph264depay ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_1 \
  udpsrc port=2003 ! application/x-rtp,encoding-name=H264 ! rtph264depay ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_2 \
  udpsrc port=2004 ! application/x-rtp,encoding-name=H264 ! rtph264depay ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_3 \
  udpsrc port=2005 ! application/x-rtp,encoding-name=H264 ! rtph264depay ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_4 \
  udpsrc port=2006 ! application/x-rtp,encoding-name=H264 ! rtph264depay ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_5 \
  udpsrc port=2007 ! application/x-rtp,encoding-name=H264 ! rtph264depay ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_6 \
  udpsrc port=2008 ! application/x-rtp,encoding-name=H264 ! rtph264depay ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_7 \
  udpsrc port=2009 ! application/x-rtp,encoding-name=H264 ! rtph264depay ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_8 \
  udpsrc port=2010 ! application/x-rtp,encoding-name=H264 ! rtph264depay ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_9 \
  udpsrc port=2011 ! application/x-rtp,encoding-name=H264 ! rtph264depay ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_10 \
  udpsrc port=2012 ! application/x-rtp,encoding-name=H264 ! rtph264depay ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_11 \
  udpsrc port=2013 ! application/x-rtp,encoding-name=H264 ! rtph264depay ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_12 \
  udpsrc port=2014 ! application/x-rtp,encoding-name=H264 ! rtph264depay ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_13 \
  udpsrc port=2015 ! application/x-rtp,encoding-name=H264 ! rtph264depay ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_14 \
  udpsrc port=2016 ! application/x-rtp,encoding-name=H264 ! rtph264depay ! nvvideoconvert ! "video/x-raw(memory:NVMM),format=NV12" ! mux.sink_15
