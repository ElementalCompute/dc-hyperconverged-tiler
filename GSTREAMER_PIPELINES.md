# GStreamer Pipeline Architecture

## Overview

The apphost system uses GStreamer to capture the X11 display (showing the browser) and stream it to static-tiler via named pipes (FIFO) for consumption.

## Producer Pipeline (AppHost)

**Location:** `apphost/server.py` - `BrowserManager._start_gstreamer()`

**Pipeline:**
```bash
gst-launch-1.0 -e \
  ximagesrc display-name=:99 use-damage=false show-pointer=false ! \
  video/x-raw,framerate=30/1 ! \
  videoconvert ! \
  video/x-raw,format=RGBA ! \
  filesink location=/dev/shm/{SERVICE_NAME}_video.fifo sync=false
```

**Components:**
- **ximagesrc**: Captures X11 display at DISPLAY :99
  - `use-damage=false`: Capture full frames, not just changed regions
  - `show-pointer=false`: Don't include mouse cursor
- **video/x-raw,framerate=30/1**: Set 30 FPS capture rate
- **videoconvert**: Convert pixel format
- **video/x-raw,format=RGBA**: Output as RGBA (1920x1080x4 bytes = 8.3MB/frame)
- **filesink**: Write to named pipe (FIFO)
  - `sync=false`: Non-blocking writes (critical for FIFO to work)
  - Location: `/dev/shm/apphost1_video.fifo`, `/dev/shm/apphost2_video.fifo`, etc.

**Output Format:**
- Resolution: 1920x1080
- Format: RGBA (32-bit per pixel)
- Framerate: 30 FPS
- Transport: Named pipe (FIFO) in shared memory

## Consumer Pipeline (Static-Tiler / Recording)

**Example Working Pipeline:**
```bash
gst-launch-1.0 -e \
  filesrc location=/dev/shm/apphost1_video.fifo ! \
  videoparse format=rgba width=1920 height=1080 framerate=30/1 ! \
  videoconvert ! \
  x264enc speed-preset=ultrafast bitrate=5000 ! \
  h264parse ! \
  mp4mux ! \
  filesink location=output.mp4
```

**Components:**
- **filesrc**: Read from named pipe (FIFO)
- **videoparse**: Parse raw video data
  - Must specify: format, width, height, framerate
- **videoconvert**: Convert to encoder-compatible format
- **x264enc**: H.264 video encoder
  - `speed-preset=ultrafast`: Fast encoding
  - `bitrate=5000`: 5 Mbps target bitrate
- **h264parse**: Parse H.264 stream
- **mp4mux**: Mux into MP4 container
- **filesink**: Write output file

**Alternative Consumer (Tee for Multiple Outputs):**
```bash
gst-launch-1.0 -e \
  filesrc location=/dev/shm/apphost1_video.fifo ! \
  videoparse format=rgba width=1920 height=1080 framerate=30/1 ! \
  tee name=t \
  t. ! queue ! videoconvert ! autovideosink \
  t. ! queue ! videoconvert ! x264enc ! mp4mux ! filesink location=output.mp4
```

## Named Pipe (FIFO) Architecture

**Why FIFO Instead of shmsink?**
- shmsink/shmsrc require complex socket handshaking
- Connection timing issues with `wait-for-connection` parameter
- FIFOs are simpler: standard Unix named pipes in /dev/shm

**FIFO Creation:**
```python
import os
fifo_path = f"/dev/shm/{service_name}_video.fifo"
if not os.path.exists(fifo_path):
    os.mkfifo(fifo_path)
```

**FIFO Properties:**
- Created in `/dev/shm` (tmpfs - memory-backed filesystem)
- Each apphost has its own FIFO: `apphost1_video.fifo`, `apphost2_video.fifo`, etc.
- Writer (apphost) must use `sync=false` to avoid blocking
- Reader connects whenever needed, no pre-connection required

## Static-Tiler Integration

**Shared Memory Volume Mapping:**
```yaml
static-tiler:
  volumes:
    - apphost1-shm:/dev/shm/apphost1
    - apphost2-shm:/dev/shm/apphost2
    - apphost3-shm:/dev/shm/apphost3
    - apphost4-shm:/dev/shm/apphost4
```

**Static-Tiler Access Paths:**
- AppHost 1: `/dev/shm/apphost1/apphost1_video.fifo`
- AppHost 2: `/dev/shm/apphost2/apphost2_video.fifo`
- AppHost 3: `/dev/shm/apphost3/apphost3_video.fifo`
- AppHost 4: `/dev/shm/apphost4/apphost4_video.fifo`

## Data Flow

```
┌─────────────────────────────────────────┐
│ AppHost Container                       │
│                                         │
│  Chromium → Xvfb :99                    │
│      ↓                                  │
│  ximagesrc (capture)                    │
│      ↓                                  │
│  videoconvert → RGBA                    │
│      ↓                                  │
│  filesink (sync=false)                  │
│      ↓                                  │
│  /dev/shm/apphost1_video.fifo (FIFO)   │
└──────────────┬──────────────────────────┘
               │ (shared volume)
               ↓
┌─────────────────────────────────────────┐
│ Static-Tiler Container                  │
│                                         │
│  filesrc location=/dev/shm/apphost1/... │
│      ↓                                  │
│  videoparse (decode raw)                │
│      ↓                                  │
│  [processing/tiling logic]              │
│      ↓                                  │
│  encoder → output                       │
└─────────────────────────────────────────┘
```

## Performance Characteristics

**Bandwidth:**
- 1920x1080 RGBA @ 30fps = ~236 MB/s raw
- FIFO buffering in tmpfs (memory-backed)
- Low latency (no disk I/O)

**CPU Usage:**
- ximagesrc: Low (X11 capture)
- videoconvert: Medium (format conversion)
- Encoding (consumer side): High (x264enc)

## Testing Commands

**Test AppHost is streaming:**
```bash
docker exec apphost1 ls -la /dev/shm/apphost1_video.fifo
# Should show: prw-r--r-- (named pipe)
```

**Test recording from FIFO:**
```bash
docker run --rm -v tiler-v3_apphost1-shm:/dev/shm -v $(pwd):/output ubuntu:22.04 bash -c '
  apt-get update -qq && apt-get install -y -qq gstreamer1.0-tools gstreamer1.0-plugins-* -y > /dev/null 2>&1
  timeout --signal=SIGINT 10 gst-launch-1.0 -e \
    filesrc location=/dev/shm/apphost1_video.fifo ! \
    videoparse format=rgba width=1920 height=1080 framerate=30/1 ! \
    videoconvert ! \
    x264enc speed-preset=ultrafast bitrate=5000 ! \
    h264parse ! \
    mp4mux ! \
    filesink location=/output/test.mp4
'
```

**Verify output:**
```bash
ffprobe test.mp4  # Should show 1920x1080 @ 30fps H.264 video
```

## Troubleshooting

**FIFO blocks on write:**
- Ensure `sync=false` on filesink
- Check reader is connected

**No data in FIFO:**
- Verify GStreamer pipeline is running: `docker exec apphost1 ps aux | grep gst`
- Check logs: `docker logs apphost1 | grep -i gstream`

**Consumer gets no frames:**
- Check FIFO exists: `ls -la /dev/shm/apphost1_video.fifo`
- Verify videoparse parameters match producer output
- Test with simpler pipeline (videotestsrc) first

## Next Steps for Static-Tiler

The static-tiler needs to implement a GStreamer pipeline that:
1. Reads from all 4 apphost FIFOs simultaneously
2. Uses compositor or videomixer to tile the 4 streams
3. Encodes the final tiled output
4. Optionally exposes the result via another FIFO or RTSP stream

Example multi-input consumer pipeline structure:
```bash
gst-launch-1.0 \
  compositor name=mix \
    sink_0::xpos=0    sink_0::ypos=0    sink_0::width=960 sink_0::height=540 \
    sink_1::xpos=960  sink_1::ypos=0    sink_1::width=960 sink_1::height=540 \
    sink_2::xpos=0    sink_2::ypos=540  sink_2::width=960 sink_2::height=540 \
    sink_3::xpos=960  sink_3::ypos=540  sink_3::width=960 sink_3::height=540 \
  ! videoconvert ! x264enc ! h264parse ! mp4mux ! filesink location=tiled.mp4 \
  filesrc location=/dev/shm/apphost1/apphost1_video.fifo ! videoparse format=rgba width=1920 height=1080 framerate=30/1 ! mix.sink_0 \
  filesrc location=/dev/shm/apphost2/apphost2_video.fifo ! videoparse format=rgba width=1920 height=1080 framerate=30/1 ! mix.sink_1 \
  filesrc location=/dev/shm/apphost3/apphost3_video.fifo ! videoparse format=rgba width=1920 height=1080 framerate=30/1 ! mix.sink_2 \
  filesrc location=/dev/shm/apphost4/apphost4_video.fifo ! videoparse format=rgba width=1920 height=1080 framerate=30/1 ! mix.sink_3
```

This creates a 2x2 grid of all 4 apphost displays in a single 1920x1080 output.