import logging
import os
import signal
import sys

import gi

gi.require_version("Gst", "1.0")
from gi.repository import GLib, Gst

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Minimal static tiler - just build and run the pipeline"""

    # Get configuration
    num_inputs = int(os.environ.get("NUM_INPUTS", "16"))
    grid_cols = int(os.environ.get("GRID_COLS", "4"))
    grid_rows = int(os.environ.get("GRID_ROWS", "4"))

    logger.info(f"Starting tiler: {num_inputs} inputs, {grid_cols}x{grid_rows} grid")

    # Initialize GStreamer
    Gst.init(None)

    # Create pipeline
    pipeline = Gst.Pipeline.new("tiler-pipeline")

    # Create nvstreammux
    streammux = Gst.ElementFactory.make("nvstreammux", "mux")
    streammux.set_property("width", 1920)
    streammux.set_property("height", 1080)
    streammux.set_property("batch-size", num_inputs)
    streammux.set_property("batched-push-timeout", 40000)

    # Create tiler
    tiler = Gst.ElementFactory.make("nvmultistreamtiler", "tiler")
    tiler.set_property("rows", grid_rows)
    tiler.set_property("columns", grid_cols)
    tiler.set_property("width", 3840)
    tiler.set_property("height", 2160)

    # Create encoder
    encoder = Gst.ElementFactory.make("nvv4l2h264enc", "encoder")
    encoder.set_property("bitrate", 8000000)

    # Create h264parse
    h264parse = Gst.ElementFactory.make("h264parse", "parser")

    # Create TCP sink
    tcpsink = Gst.ElementFactory.make("tcpserversink", "sink")
    tcpsink.set_property("host", "0.0.0.0")
    tcpsink.set_property("port", 6000)
    tcpsink.set_property("sync", False)

    # Add to pipeline
    pipeline.add(streammux)
    pipeline.add(tiler)
    pipeline.add(encoder)
    pipeline.add(h264parse)
    pipeline.add(tcpsink)

    # Link main path
    streammux.link(tiler)
    tiler.link(encoder)
    encoder.link(h264parse)
    h264parse.link(tcpsink)

    # Create sources for each slot
    for i in range(num_inputs):
        # Use videotestsrc
        src = Gst.ElementFactory.make("videotestsrc", f"src{i}")
        src.set_property("pattern", i % 25)
        src.set_property("is-live", True)

        caps = Gst.ElementFactory.make("capsfilter", f"caps{i}")
        caps.set_property(
            "caps",
            Gst.Caps.from_string(
                "video/x-raw,width=1920,height=1080,framerate=30/1,format=RGBA"
            ),
        )

        queue = Gst.ElementFactory.make("queue", f"queue{i}")

        nvconv = Gst.ElementFactory.make("nvvideoconvert", f"nvconv{i}")

        nvcaps = Gst.ElementFactory.make("capsfilter", f"nvcaps{i}")
        nvcaps.set_property(
            "caps", Gst.Caps.from_string("video/x-raw(memory:NVMM),format=NV12")
        )

        # Add to pipeline
        pipeline.add(src)
        pipeline.add(caps)
        pipeline.add(queue)
        pipeline.add(nvconv)
        pipeline.add(nvcaps)

        # Link source chain
        src.link(caps)
        caps.link(queue)
        queue.link(nvconv)
        nvconv.link(nvcaps)

        # Link to mux
        nvcaps.link_pads("src", streammux, f"sink_{i}")

    logger.info("Pipeline built")

    # Set up bus
    bus = pipeline.get_bus()
    bus.add_signal_watch()

    def on_message(bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"Error: {err.message}")
            loop.quit()
        elif t == Gst.MessageType.EOS:
            logger.info("EOS")
            loop.quit()

    bus.connect("message", on_message)

    # Start pipeline
    logger.info("Starting pipeline...")
    pipeline.set_state(Gst.State.PLAYING)

    # Run loop
    loop = GLib.MainLoop()

    def signal_handler(sig, frame):
        logger.info("Stopping...")
        pipeline.set_state(Gst.State.NULL)
        loop.quit()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Running...")

    # Wait a bit and check state
    import time

    time.sleep(2)
    ret, state, pending = pipeline.get_state(Gst.CLOCK_TIME_NONE)
    logger.info(f"Pipeline state after 2s: {state.value_nick} (return: {ret})")

    try:
        loop.run()
    except Exception as e:
        logger.error(f"Loop exception: {e}")
        import traceback

        traceback.print_exc()

    pipeline.set_state(Gst.State.NULL)
    logger.info("Done")


if __name__ == "__main__":
    main()
